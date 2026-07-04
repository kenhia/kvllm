"""S5 vision suite — read the surfaces the homelab controller will actually look at.

Single-generate episodes (no sandbox, no tools): an image + one question with a short
factual answer. v1 (v1-v8): extraction over deterministic PIL renderings (regenerate:
`python -m suites.vision_assets.generate`). v2 adds classification/captioning over real
photos (p1-p4, downscaled + EXIF-stripped) and a render-defect QA pair (v9/v10 — detect
the broken flowchart, do NOT invent defects on the clean control). Scoring is mechanical
fact-groups, agentic-style: every group must be matched by at least one of its
alternatives; digits-only alternatives match on word boundaries (so "20" never passes via
"205"). Partial credit = matched/total; pass = all groups.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ChatMessageUser, ContentImage, ContentText, GenerateConfig
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import TaskState, generate

# v2 (2026-07-04): +6 tasks. v1's clean-render extraction hit a ceiling (5 locals 94-100%,
# baselines 100%): added classification/captioning on real photos (Ken's, downscaled +
# EXIF-stripped), an absence/honesty count, and a render-defect pair (detect the broken
# flowchart — and do NOT invent defects on the clean control).
VERSION = 2
ASSETS = Path(__file__).resolve().parent / "vision_assets"

PREAMBLE = (
    "You are reading a monitoring screenshot for the owner of this homelab. "
    "Answer briefly and factually from the image alone."
)


@dataclass
class VTask:
    name: str
    image: str  # filename under vision_assets/
    question: str
    # fact groups: every group must match; a group matches if ANY alternative appears.
    groups: list[list[str]] = field(default_factory=list)


VTASKS = [
    VTask(
        name="v1-dashboard-down",
        image="v1-dashboard-down.png",
        question="Which service is down? Answer with the service name.",
        groups=[["backup-sync"]],
    ),
    VTask(
        name="v2-gauge-disk",
        image="v2-gauge-disk.png",
        question="Which mount is nearly full, and at what percent?",
        groups=[["/var"], ["87"]],
    ),
    VTask(
        name="v3-chart-peak",
        image="v3-chart-peak.png",
        question=(
            "On which day did GPU temperature peak, and at approximately what value in °C?"
        ),
        groups=[["thu"], ["80", "81", "82", "83", "84", "85"]],
    ),
    VTask(
        name="v4-terminal-df",
        image="v4-terminal-df.png",
        question="Which filesystem is fullest, and at what use percentage?",
        # First-run rubric bug (2026-07-03): 5/7 models answered the device
        # ("/dev/nvme1n1p1"), which IS the Filesystem column — only the mount was
        # accepted. Fairness fix on the then-unranked v1; affected models re-run.
        groups=[["/data", "nvme1n1"], ["91"]],
    ),
    VTask(
        name="v5-journal-error",
        image="v5-journal-error.png",
        question="What happened at 02:14 on this machine, and to which service?",
        groups=[["oom", "out of memory", "killed process"], ["postgres"]],
    ),
    VTask(
        name="v6-table-registry",
        image="v6-table-registry.png",
        question="Per this table, what is the est VRAM (GB) of qwen3.6-27b-awq?",
        groups=[["20"]],
    ),
    VTask(
        name="v7-count-warnings",
        image="v7-count-warnings.png",
        question="How many checks show WARN?",
        groups=[["3", "three"]],
    ),
    VTask(
        name="v8-diagram-backup",
        image="v8-diagram-backup.png",
        question="Per this topology diagram, which host receives kai's nightly backups?",
        groups=[["nas"]],
    ),
    # --- v2: rendering QA pair (detect real defects; don't invent them) ---
    VTask(
        name="v9-render-broken",
        image="v9-render-broken.png",
        question=(
            "Quality-check this generated diagram: does it render correctly? "
            "If not, describe the defect and where it is."
        ),
        groups=[
            [
                "overflow",
                "outside",
                "spill",
                "beyond",
                "clipped",
                "cut off",
                "extends past",
                "overrun",
                "truncat",
                "overlap",
                "on top of",
            ],
            ["integration", "third box"],
        ],
    ),
    VTask(
        name="v10-render-clean",
        image="v10-render-clean.png",
        question=(
            "Quality-check this generated diagram: does it render correctly? "
            "If not, describe the defect and where it is."
        ),
        groups=[
            [
                "correct",
                "no defect",
                "no issue",
                "fine",
                "properly",
                "looks good",
                "renders well",
            ]
        ],
    ),
    # --- v2: classification / captioning on real photos ---
    VTask(
        name="p1-animal",
        image="p1-animal.jpg",
        question="What animal is this (be specific), and what is it wearing?",
        # "harness" is deliberately NOT accepted (Ken confirmed it's a bandana): the
        # plausible misread earns partial credit via the group mechanism (1/2 = 50%),
        # and the precise read is a real differentiator — Sonnet said "Shiba Inu ...
        # harness or bandana-style", Haiku invented "hair bows". Both first-run 2026-07-04.
        groups=[["corgi"], ["bandana", "scarf", "kerchief", "neckerchief"]],
    ),
    VTask(
        name="p2-hardware",
        image="p2-hardware.jpg",
        question="What device is shown here, and is it connected to a network?",
        groups=[
            ["raspberry pi", "rpi", " pi "],
            ["ethernet", "network cable", "rj45", "yes"],
        ],
    ),
    VTask(
        name="p3-tools",
        image="p3-tools.jpg",
        question="What measuring tools are shown in this scan?",
        groups=[["caliper"], ["ruler", "rule "]],
    ),
    VTask(
        name="p5-activity",
        image="p5-activity.jpg",
        question="What activity is happening in this photo, and how many riders are visible?",
        groups=[["cycl", "bik", "triathlon", "road race"], ["2", "two"]],
    ),
    # absence check: same hardware photo, nobody in frame
    VTask(
        name="p4-count-people",
        image="p2-hardware.jpg",
        question="How many people are visible in this image? Answer with a number.",
        groups=[["0", "zero", "none", "no people", "no person"]],
    ),
]


def _alt_matches(alt: str, answer: str) -> bool:
    """Digits-only alternatives match on word boundaries ('20' must not pass via '205'
    or '120'); anything else is a case-insensitive substring."""
    if alt.isdigit():
        return re.search(rf"(?<![\d.]){re.escape(alt)}(?![\d.])", answer) is not None
    return alt in answer


def fact_score(groups: list[list[str]], answer: str) -> tuple[float, list[str]]:
    """(fraction of groups matched, unmatched groups rendered for the scorecard)."""
    if not groups:
        return 1.0, []
    low = answer.lower()
    missing = [
        " | ".join(g)
        for g in groups
        if not any(_alt_matches(a.lower(), low) for a in g)
    ]
    return (len(groups) - len(missing)) / len(groups), missing


@scorer(metrics=[mean(), stderr()])
def vision_scorer():
    async def score(state: TaskState, target: Target) -> Score:
        answer = (state.output.completion or "") if state.output else ""
        groups = state.metadata.get("groups", [])
        frac, missing = fact_score(groups, answer)
        detail = f"facts {frac:.0%}"
        if missing:
            detail += f" (missing: {'; '.join(missing)})"
        if not answer.strip():
            detail = "EMPTY ANSWER — " + detail
        return Score(
            value=round(frac, 3),
            answer=answer[:300],
            explanation=detail,
            # NOTE: no "raw_frac" key — suite_from_log treats its presence as the
            # coding-suite ×0.9-penalty path; vision is plain partial credit via value.
            metadata={"missing": missing},
        )

    return score


@task
def vision() -> Task:
    samples = [
        Sample(
            id=t.name,
            input=[
                ChatMessageUser(
                    content=[
                        ContentText(text=f"{PREAMBLE}\n\n{t.question}"),
                        ContentImage(image=str(ASSETS / t.image)),
                    ]
                )
            ],
            metadata=asdict(t),
        )
        for t in VTASKS
    ]
    return Task(
        dataset=MemoryDataset(samples, name="vision"),
        solver=generate(),
        scorer=vision_scorer(),
        # 4096: reasoning headroom (the judged-suite lesson; 2048 still cut off the 27B
        # mid-think on a photo task) while answers stay short.
        config=GenerateConfig(max_tokens=4096),
        version=VERSION,
    )
