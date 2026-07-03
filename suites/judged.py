"""S4 `judged` suite — instruction quality that mechanical checks can't grade alone.

Single-turn tasks (summarize / strict format / plan / explain / constrained list / rewrite),
scored by a frontier judge (eval-config.toml [judge].model, Anthropic API) against a per-task
rubric, with mechanical pre-checks capping the score where format rules are objective (bullet
counts, JSON validity — an unparseable "JSON" answer is auto-0 regardless of judge opinion).
The judge returns structured JSON {score 0-10, rationale, violations}; the rationale is stored
in the scorecard so every judged number is auditable (planning/03).

The suite is EXCLUDED from the composite until the calibration protocol passes
([judge].calibrated in eval-config.toml): `python -m suites.judged sheet <log.eval>` renders a
calibration sheet for Ken to hand-score; judge must be within ±1 on >=80%.

Mechanical checks + judge-JSON parsing are pure functions (unit-tested without a live judge).
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import generate

# v2 (2026-07-03): max_tokens 1024 → 4096. Reasoning models (Qwen3.5/3.6 family) burned the
# whole 1024 inside <think> and submitted empty answers — the judge was grading blanks. 4096
# gives thinking room while the rubrics still reward concision; non-reasoning models' answers
# are unaffected (they fit in 1024 already).
VERSION = 2

REPO = Path(__file__).resolve().parent.parent

INCIDENT_LOG = """\
2026-07-01 02:14:03 kubsdb systemd[1]: postgresql.service: Main process exited, code=killed, signal=KILL
2026-07-01 02:14:03 kubsdb kernel: Out of memory: Killed process 88123 (postgres) total-vm:14203944kB
2026-07-01 02:14:04 kubsdb systemd[1]: postgresql.service: Failed with result 'signal'.
2026-07-01 02:14:09 kubsdb systemd[1]: postgresql.service: Scheduled restart job, restart counter is at 1.
2026-07-01 02:14:12 kubsdb postgres[88342]: LOG: database system was interrupted; last known up at 02:13:55
2026-07-01 02:14:14 kubsdb postgres[88342]: LOG: database system is ready to accept connections
2026-07-01 02:20:31 kubsdb backup[88690]: pg_dump: error: connection to server failed: FATAL: too many connections
2026-07-01 02:20:31 kubsdb backup[88690]: nightly backup FAILED
2026-07-01 03:05:10 kubsdb admin: raised max_connections 100 -> 200 in postgresql.conf, restarted service
2026-07-01 03:11:44 kubsdb backup[91002]: nightly backup completed OK (retry)
"""

UNIT_FILE = """\
[Unit]
Description=kvllm — vLLM OpenAI-compatible server (kai RTX 5090)
After=network-online.target

[Service]
Type=exec
EnvironmentFile=%h/src/ai/kvllm/deploy/kvllm.env
ExecStart=/home/ken/.local/bin/uv run python -m kvllm.registry serve ${KVLLM_MODEL_KEY}
Restart=on-failure
TimeoutStartSec=900

[Install]
WantedBy=default.target
"""

ANGRY_EMAIL = """\
Your update BROKE EVERYTHING again!!! Third time this quarter. The dashboard has been down
since 6am, your status page still says "all systems operational" which is a JOKE, and nobody
has answered the ticket I opened four hours ago (#48213). We pay for the premium SLA. Fix it
TODAY or we are done.
"""


@dataclass
class JTask:
    name: str
    prompt: str
    rubric: str  # what the judge grades 0-10
    auto_zero: str  # conditions the judge must score 0 for
    mech: str | None = None  # mechanical pre-check key (see mechanical_check)
    facts: list[str] = field(default_factory=list)  # reference facts for the judge


JTASKS: list[JTask] = [
    JTask(
        name="summarize-incident",
        prompt=(
            "Here is a homelab incident log:\n\n```\n"
            + INCIDENT_LOG
            + "```\n\nSummarize the incident in exactly 3 bullet points: (1) what broke, "
            "(2) the root cause, (3) how it was resolved. Each bullet one sentence."
        ),
        rubric=(
            "Accuracy against the log: postgres was OOM-killed and auto-restarted; the "
            "nightly backup then failed due to 'too many connections'; the admin raised "
            "max_connections 100->200 and the backup retry succeeded. Full marks = all three "
            "elements correct and concise; deduct for missing elements or muddled causality."
        ),
        auto_zero="Any fabricated fact not present in the log (hosts, times, causes).",
        mech="bullets3",
        facts=[
            "OOM-killed postgres",
            "backup failed: too many connections",
            "max_connections 100->200",
        ],
    ),
    JTask(
        name="strict-json",
        prompt=(
            "Machine report: host kubsdb is degraded. The failed units are postgresql and "
            "nightly-backup. There are 42 gigabytes free on disk.\n\n"
            "Output ONLY a JSON object (no prose, no code fences) with exactly these keys: "
            '"host" (string), "status" (string), "failed_units" (array of strings), '
            '"disk_free_gb" (number).'
        ),
        rubric=(
            "Values must match the report: host kubsdb, status degraded, failed_units "
            "[postgresql, nightly-backup] (order irrelevant), disk_free_gb 42. Full marks = "
            "exact keys and correct values; deduct for wrong values or extra keys."
        ),
        auto_zero="Output is not parseable JSON, or keys differ from the four required.",
        mech="json4keys",
        facts=["kubsdb", "degraded", "postgresql", "nightly-backup", "42"],
    ),
    JTask(
        name="plan-migration",
        prompt=(
            "Plan the migration of a PostgreSQL database service from machine A to machine B "
            "in a homelab. Constraints: total downtime must stay under 5 minutes, and the plan "
            "must include an explicit rollback step. Present at most 6 numbered steps."
        ),
        rubric=(
            "Grade plan quality: sensible ordering (replicate/sync before cutover, verify "
            "before decommission), the downtime constraint respected by the approach (e.g. "
            "replication + brief cutover, not dump/restore during downtime), an explicit "
            "rollback step, and <=6 steps. Full marks = coherent, ordered, constraint-aware."
        ),
        auto_zero="No rollback step, or the plan clearly violates the 5-minute downtime bound.",
    ),
    JTask(
        name="explain-config",
        prompt=(
            "Explain this systemd user unit to a colleague in 2-4 plain sentences — what runs, "
            "when it restarts, and one operational caveat:\n\n```ini\n"
            + UNIT_FILE
            + "```"
        ),
        rubric=(
            "Correctness: it serves a vLLM model chosen by KVLLM_MODEL_KEY from an env file; "
            "Restart=on-failure means it restarts only on failure (not clean stops); a caveat "
            "such as the 900s start timeout for cold model loads, or the env file gating the "
            "model choice. Deduct for wrong semantics (e.g. claiming it always restarts)."
        ),
        auto_zero="Misstates Restart=on-failure as always-restart, or describes a different unit.",
    ),
    JTask(
        name="constrained-list",
        prompt=(
            "List exactly 5 checks for diagnosing high disk usage on a Linux server. "
            "One check per line, each 8 words or fewer, no numbering beyond '1.'-'5.'."
        ),
        rubric=(
            "Usefulness and coverage of the 5 checks (e.g. du/df, log growth, docker/images, "
            "package caches, deleted-but-open files). Format compliance is mechanically "
            "checked; grade content quality."
        ),
        auto_zero="Fewer or more than 5 checks.",
        mech="list5x8",
    ),
    JTask(
        name="professional-rewrite",
        prompt=(
            "Rewrite this message to a vendor so it is firm but professional, preserving all "
            "three factual complaints (dashboard down since 6am; status page wrong; ticket "
            "#48213 unanswered for four hours) and the SLA expectation:\n\n"
            + ANGRY_EMAIL
        ),
        rubric=(
            "Professional, non-hostile tone; all three factual complaints preserved (downtime "
            "since 6am, incorrect status page, unanswered ticket #48213); the premium-SLA "
            "expectation retained; concise. Deduct for dropped facts or residual hostility."
        ),
        auto_zero="Any of the three factual complaints missing, or ticket number changed.",
        facts=["6am", "status page", "#48213", "SLA"],
    ),
]


# --- mechanical pre-checks (pure; cap the judge's score) --------------------------------


def _bullet_lines(answer: str) -> list[str]:
    return [
        ln for ln in answer.splitlines() if re.match(r"^\s*([-*•]|\d+[.)])\s+\S", ln)
    ]


def mechanical_check(mech: str | None, answer: str) -> tuple[int, list[str]]:
    """(score cap 0-10, violations). 10 = no mechanical objection."""
    if not mech:
        return 10, []
    answer = answer.strip()
    if mech == "bullets3":
        n = len(_bullet_lines(answer))
        return (10, []) if n == 3 else (4, [f"expected 3 bullets, found {n}"])
    if mech == "json4keys":
        try:
            # tolerate a fenced block even though the prompt forbids it (grade via judge)
            text = re.sub(r"^```(json)?|```$", "", answer, flags=re.MULTILINE).strip()
            obj = json.loads(text)
        except json.JSONDecodeError:
            return 0, ["not parseable JSON"]
        want = {"host", "status", "failed_units", "disk_free_gb"}
        if not isinstance(obj, dict) or set(obj) != want:
            got = sorted(obj) if isinstance(obj, dict) else type(obj).__name__
            return 2, [f"keys {got} != required {sorted(want)}"]
        return 10, []
    if mech == "list5x8":
        lines = [ln for ln in answer.splitlines() if ln.strip()]
        items = _bullet_lines(answer) or lines
        violations = []
        if len(items) != 5:
            violations.append(f"expected 5 items, found {len(items)}")
        long = [
            ln
            for ln in items
            if len(re.sub(r"^\s*([-*•]|\d+[.)])\s*", "", ln).split()) > 8
        ]
        if long:
            violations.append(f"{len(long)} item(s) over 8 words")
        return (10, []) if not violations else (4, violations)
    return 10, []


def parse_judge_json(text: str) -> dict | None:
    """Extract {'score', 'rationale', 'violations'} from the judge's reply (tolerates fences
    or stray prose). None if unusable."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or "score" not in obj:
        return None
    try:
        s = float(obj["score"])
    except (TypeError, ValueError):
        return None
    return {
        "score": max(0.0, min(10.0, s)),
        "rationale": str(obj.get("rationale", "")),
        "violations": [str(v) for v in obj.get("violations", []) or []],
    }


JUDGE_PROMPT = """You are grading a local LLM's answer for a homelab model leaderboard. Be a \
strict, consistent grader; the same quality must always get the same score.

TASK GIVEN TO THE MODEL:
{prompt}

RUBRIC (grade 0-10 against this):
{rubric}

SCORE 0 IF: {auto_zero}
REFERENCE FACTS (the answer must not contradict these): {facts}

MODEL'S ANSWER:
<answer>
{answer}
</answer>

Reply with ONLY a JSON object: {{"score": <0-10 integer>, "rationale": "<one or two sentences>", \
"violations": ["<rule broken>", ...]}}"""


# --- inspect wiring -----------------------------------------------------------------------


@scorer(metrics=[mean(), stderr()])
def judged_scorer():
    async def score(state, target: Target) -> Score:
        from kvllm.score import load_config  # single source for the judge model id

        meta = state.metadata
        answer = state.output.completion or ""
        cap, mech_violations = mechanical_check(meta.get("mech"), answer)

        judge_model = load_config()["judge"]["model"]
        grader = get_model(judge_model)
        prompt = JUDGE_PROMPT.format(
            prompt=meta["prompt"],
            rubric=meta["rubric"],
            auto_zero=meta["auto_zero"],
            facts=", ".join(meta.get("facts") or []) or "(none)",
            answer=answer[:6000],
        )
        result = await grader.generate(
            prompt, config=GenerateConfig(temperature=0.0, max_tokens=400)
        )
        parsed = parse_judge_json(result.completion or "")
        if parsed is None:
            return Score(
                value=0.0,
                explanation="judge reply unparseable — scored 0; investigate",
                metadata={"judge_model": judge_model, "judge_raw": result.completion},
            )

        final10 = min(parsed["score"], cap)
        violations = mech_violations + parsed["violations"]
        detail = parsed["rationale"]
        if mech_violations:
            detail += f" [mechanical: {'; '.join(mech_violations)} → cap {cap}/10]"
        return Score(
            value=round(final10 / 10, 3),
            answer=answer[:200],
            explanation=detail,
            metadata={
                "judge_model": judge_model,
                "judge_score": parsed["score"],
                "mech_cap": cap,
                "violations": violations,
            },
        )

    return score


@task
def judged() -> Task:
    samples = [
        Sample(id=t.name, input=t.prompt, metadata=asdict(t) | {"prompt": t.prompt})
        for t in JTASKS
    ]
    return Task(
        dataset=MemoryDataset(samples, name="judged"),
        solver=generate(),
        scorer=judged_scorer(),
        config=GenerateConfig(max_tokens=4096),
        version=VERSION,
    )


# --- calibration sheet ---------------------------------------------------------------------


def write_calibration_sheet(log_paths: list[str], out_path: Path) -> Path:
    """Render judged results into a hand-scoring sheet: answer + judge score/rationale + a
    blank column for Ken. Judge passes calibration at within ±1 on >=80% of rows
    (then flip [judge].calibrated in eval-config.toml)."""
    from inspect_ai.log import read_eval_log

    lines = [
        "# Judge calibration sheet",
        "",
        "_Self-contained: each row carries the full task the model saw, its answer, the rubric,",
        "and the judge's grade — score 0-10 yourself (last line) WITHOUT reading the judge's",
        "score first. Pass: judge within ±1 of your score on >=80% of rows → set",
        "`[judge] calibrated = true` in eval-config.toml. The judge score is the CONTENT grade;",
        "where a mechanical cap applied, the suite's final (capped) score is shown too — caps",
        "are code, not judgment, and are excluded from calibration._",
        "",
    ]
    n = 0
    for lp in log_paths:
        log = read_eval_log(str(lp))
        model = log.eval.model
        for s in log.samples or []:
            sc = next(iter((s.scores or {}).values()), None)
            if not sc:
                continue
            n += 1
            meta = sc.metadata or {}
            smeta = s.metadata or {}
            judge10 = meta.get("judge_score")
            final10 = round(float(sc.value) * 10, 1) if sc.value is not None else None
            capped = (
                f" (suite final after mechanical cap: {final10}/10)"
                if judge10 is not None and final10 is not None and final10 < judge10
                else ""
            )
            lines += [
                f"## {n}. `{s.id}` — {model}",
                "",
                "**Task given to the model:**",
                "",
                "```",
                (smeta.get("prompt") or s.input or "")[:2500],
                "```",
                "",
                "**Model's answer:**",
                "",
                "```",
                (s.output.completion or "")[:1500],
                "```",
                "",
                f"**Rubric:** {smeta.get('rubric', '(see suites/judged.py)')}",
                "",
                f"- judge: **{judge10}/10**{capped} — {sc.explanation}",
                f"- violations: {meta.get('violations') or 'none'}",
                "- **Ken:** ___ /10",
                "",
            ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    return out_path


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "sheet":
        out = REPO / "model-research" / "evals" / "calibration" / "judged-sheet.md"
        path = write_calibration_sheet(sys.argv[2:], out)
        print(f"wrote {path}")
        return 0
    print("usage: python -m suites.judged sheet <log.eval> [...]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
