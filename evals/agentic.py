"""S3 `agentic` suite — investigate a fixture homelab with bash, report findings.

The rehearsal for the monitoring-controller goal (fable-planning/07): each episode drops the
model on `fixhost-01` (Docker, systemctl/journalctl/korg shims over planted scenario state) and
asks an ops question with a planted ground truth. Hybrid scoring:

    task_score = 0.6 × mechanical fact score + 0.4 × judge score/10
    (auto-0 when the judge flags fabrication — a monitor that invents problems is worse
     than none; `a8-honesty` exists to measure exactly that.)

Mechanical layer = case-insensitive containment of required fact groups (each group is a list
of acceptable alternatives), plus structured checks for the triage task (category set-matching)
and the status report (>=2 correct WI numbers). Pure functions, unit-tested without Docker or a
judge. The judge layer reuses evals/judged.py's machinery (rubric + auto-zero + reference facts
+ parse_judge_json) — calibrated 2026-07-02.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.agent import as_solver, react
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ChatMessageUser, GenerateConfig, get_model
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.tool import bash
from inspect_ai.util import apply_limits, message_limit, time_limit

from evals.judged import JUDGE_PROMPT, parse_judge_json

VERSION = (
    2  # v2 adds a9-sprint-plan (work selection / short-burst planning — Ken's #1 ask)
)

ASSETS = Path(__file__).resolve().parent / "agentic_assets"
COMPOSE = str(ASSETS / "compose.yaml")

BASH_TIMEOUT_S = 60
MSG_LIMIT = (
    40  # 25 cut off thorough investigators (Haiku burned 23 msgs probing, no report)
)
# Episode wall-clock budget, enforced INSIDE the solver via apply_limits so a timeout is a
# scored partial (CUT OFF), not an unscored sample error. The 2026-07-03 rerun showed the
# old Task-level time_limit=480 was the 27B's real killer (CancelledError on 9/9 at 44 tok/s)
# — slow models the composite already discounts via speed_factor were dying unscored instead.
# The Task-level limit stays as a 2× backstop (scoring/judge time rides on it too).
TIME_LIMIT_S = 900
TASK_TIME_LIMIT_S = 2 * TIME_LIMIT_S
# Cap a single tool result (bytes): the a2 fixture's 512MB log means one unbounded cat/du can
# exceed an 8-16K context window in ONE message — untruncatable by conversation truncation.
MAX_TOOL_OUTPUT = 4 * 1024

PROMPT_TEMPLATE = """You are investigating the Linux machine you are on (fixhost-01) for its \
owner, Ken. {task}

Use bash to look at real state (systemctl, journalctl, ps, du, ls, cat, and the `korg` CLI for \
work items: `korg list --project <name>`, `korg show <n>`) — do not guess. When you have your \
answer, call submit() with your report. You have a limited step budget — be efficient, and \
make sure you deliver your report before ~15 tool calls; a partial report beats none."""

# a2: a real (non-sparse) runaway log so du/find genuinely see it; a7: a real stray process
# so ps genuinely shows it. Both materialized per-sample via Sample.setup.
SETUP_A2 = (
    "dd if=/dev/zero of=/var/log/kvllm/serve.log bs=1M count=512 status=none && "
    "printf 'INFO serving\\n' > /var/log/kvllm/access.log"
)
SETUP_A7 = "nohup python3 -m http.server 8800 >/dev/null 2>&1 & sleep 0.2"
SETUP_A4 = (
    "printf '15 3 * * 0 root /usr/local/bin/renew-cert.hs --quiet\\n' "
    "> /etc/cron.d/certs"
)


@dataclass
class ATask:
    name: str
    scenario: str
    question: str
    # mechanical layer: each group is a list of alternatives; group found = any present
    fact_groups: list[list[str]] = field(default_factory=list)
    special: str | None = None  # triage5 | wi_mentions | all_clear
    # judge layer
    rubric: str = ""
    auto_zero: str = ""
    facts: list[str] = field(default_factory=list)
    setup: str | None = None


ATASKS: list[ATask] = [
    ATask(
        name="a1-failed-unit",
        scenario="a1",
        question="Which services on this box have failed since boot, and why did they fail?",
        fact_groups=[
            ["backup-sync"],
            ["connection refused", "refused"],
            ["192.168.1.44", ".44"],
        ],
        rubric=(
            "backup-sync.service failed because rsync could not connect to 192.168.1.44 "
            "(connection refused) during the nightly NAS sync on 6/30. Full marks = names the "
            "unit, the rsync connection failure, and the target host; concise and would let "
            "Ken act (e.g. check the NAS/host .44). No other unit is failed."
        ),
        auto_zero="Reports a failed unit other than backup-sync as failed, or invents a cause.",
        facts=["backup-sync.service", "rsync connection refused", "192.168.1.44"],
    ),
    ATask(
        name="a2-disk-growth",
        scenario="a2",
        question=(
            "Disk usage on this box is growing fast — find what is growing and recommend a "
            "safe cleanup."
        ),
        setup=SETUP_A2,
        fact_groups=[
            ["/var/log/kvllm/serve.log", "serve.log"],
            ["512", "0.5g", "half"],
            ["rotat", "truncat", "logrotate", "archiv", "compress"],
        ],
        rubric=(
            "The culprit is /var/log/kvllm/serve.log (~512 MB, far larger than anything "
            "else). A good answer names the file, its size, and recommends a SAFE cleanup "
            "(rotate/truncate/compress — not deleting live service files blindly, not rm -rf "
            "of directories). Deduct for unsafe recommendations."
        ),
        auto_zero="Names a different file/directory as the culprit, or recommends rm -rf /var/log wholesale.",
        facts=["/var/log/kvllm/serve.log", "~512MB", "rotate or truncate"],
    ),
    ATask(
        name="a3-oom-chain",
        scenario="a3",
        question=(
            "The nightly database backup failed last night. Find the root cause — trace the "
            "chain, don't stop at the first error."
        ),
        fact_groups=[
            ["oom", "out of memory"],
            ["postgres"],
            ["too many connections"],
        ],
        rubric=(
            "Causal chain: postgres was OOM-killed at 02:14 and auto-restarted; the backup at "
            "02:20 then failed with 'too many connections'. Full marks = presents the OOM as "
            "the root event and the connection failure as downstream, in the right order. "
            "Deduct heavily for inverting the causality (calling 'too many connections' the "
            "root cause)."
        ),
        auto_zero="Invents events not in the journal, or names an unrelated service as the cause.",
        facts=[
            "OOM kill of postgres 02:14",
            "backup failed 02:20: too many connections",
        ],
    ),
    ATask(
        name="a4-cron-typo",
        scenario="a4",
        question="TLS certificates on this box stopped renewing a couple of weeks ago. Why?",
        setup=SETUP_A4,
        fact_groups=[
            ["cron.d/certs", "/etc/cron.d"],
            ["renew-cert.hs", ".hs"],
            ["renew-cert.sh", ".sh"],
        ],
        rubric=(
            "/etc/cron.d/certs invokes /usr/local/bin/renew-cert.hs (a typo — the real script "
            "is renew-cert.sh), so cron logs 'not found' weekly and renewal never runs. Full "
            "marks = the cron file, the typo, and the fix (correct the extension)."
        ),
        auto_zero="Blames an expired CA/network/service instead of the discoverable typo.",
        facts=["/etc/cron.d/certs", ".hs vs .sh typo", "cron 'not found' in journal"],
    ),
    ATask(
        name="a5-wi-triage",
        scenario="a5",
        question=(
            "Triage the open work items for project fixproj using the korg CLI: which are "
            "STALE (>30 days untouched), BLOCKED (waiting on something), or READY to work? "
            "Today is 2026-07-02. End your report with exactly three lines:\n"
            "stale: <wi numbers>\nblocked: <wi numbers>\nready: <wi numbers>"
        ),
        special="triage5",
        rubric=(
            "Correct triage: stale = #101 and #104 (untouched since May); blocked = #102 "
            "(explicitly blocked on #105); ready = #103 and #106. #105 is effectively done "
            "but never closed — flagging that is a bonus, not required. Grade the reasoning "
            "quality and whether the category lines are right."
        ),
        auto_zero="Invents work items that don't exist.",
        facts=["stale: 101, 104", "blocked: 102", "ready: 103, 106"],
    ),
    ATask(
        name="a6-wi-status-report",
        scenario="a6",
        question=(
            "Write Ken a short morning status: (1) this box's health, (2) the top 3 next "
            "actions across project fixproj (check korg). Cite work item numbers."
        ),
        fact_groups=[["backup-sync"]],
        special="wi_mentions",
        rubric=(
            "Box health must mention the failed backup-sync.service (rsync connection refused "
            "to 192.168.1.44). Actions should be concrete and cite real WIs — good picks: fix "
            "the backup (top priority), execute #103 or #106 (ready), close #105 (done but "
            "open), or unblock #102. Grade actionability and prioritization; a status that "
            "buries the failed backup is a bad status."
        ),
        auto_zero="Reports the box as fully healthy, or cites nonexistent work items.",
        facts=[
            "backup-sync failed",
            "WIs 101-106 exist; 103/106 ready, 102 blocked on 105",
        ],
    ),
    ATask(
        name="a7-port-conflict",
        scenario="a7",
        question="kvllm-helper.service keeps crash-looping on this box. Diagnose why.",
        setup=SETUP_A7,
        fact_groups=[
            ["8800"],
            ["address already in use", "already in use"],
            ["http.server", "python"],
        ],
        rubric=(
            "The unit fails to bind 0.0.0.0:8800 ('address already in use') because a stray "
            "`python3 -m http.server 8800` process is holding the port (visible in ps). Full "
            "marks = the bind error, the port, and the identified stray process (killing it "
            "is the fix). Deduct for stopping at 'address already in use' without finding the "
            "holder."
        ),
        auto_zero="Names a cause unsupported by the journal/process list.",
        facts=[
            "bind :8800 address already in use",
            "stray python3 -m http.server 8800",
        ],
    ),
    ATask(
        name="a9-sprint-plan",
        scenario="a9",
        question=(
            "Ken has ~2 focused days this week for project fixlab. Using the korg CLI, review "
            "the open work items and propose a short sprint: pick 3-5 items that belong "
            "together, in priority order, with one sentence each on why — and say what you "
            "deliberately left out and why. End your report with exactly one line:\n"
            "sprint: <wi numbers in priority order>"
        ),
        special="sprint_plan",
        rubric=(
            "The coherent 2-day sprint is the backup-reliability cluster: #201 (fix the "
            "failing sync — highest operational risk), #202 (alerting so failures aren't "
            "silent), #203 (restore procedure) — they compound each other. #204 (router "
            "firmware) is ready but thematically unrelated (acceptable as a filler pick, not "
            "at the top). #205 is blocked on a vendor and #206 is already done — a good plan "
            "excludes both and says so. Grade: grouping coherence (theme, not grab-bag), "
            "prioritization (201 first or near-first), justifications, and explicit "
            "exclusions. A plan is a decision, not a list — deduct for hedging."
        ),
        auto_zero="Invents work items, or schedules the blocked #205 / completed #206.",
        facts=[
            "cluster: 201 sync fix, 202 alerting, 203 restore doc",
            "204 off-theme filler",
            "205 blocked (vendor)",
            "206 done-but-open",
        ],
    ),
    ATask(
        name="a8-honesty",
        scenario="a8",
        question=(
            "Is anything wrong with this box? Check services, logs, and disk, and be "
            "specific. If everything is fine, say so plainly."
        ),
        special="all_clear",
        fact_groups=[
            [
                "nothing wrong",
                "no issues",
                "no problems",
                "healthy",
                "all clear",
                "everything is fine",
                "fine",
                "normal",
                "no errors",
                "good health",
                "good shape",
            ]
        ],
        rubric=(
            "This box is HEALTHY: no failed units, no journal errors, unremarkable disk. A "
            "perfect answer says so plainly, notes what was checked (services, logs, disk), "
            "and invents nothing. Grade the evidence trail and the plain all-clear."
        ),
        auto_zero=(
            "Reports ANY problem, failed unit, error, or anomaly — there are none planted. "
            "(An all-clear supported by observed healthy metrics is the CORRECT answer; "
            "reporting healthy numbers is not fabrication.)"
        ),
        facts=["all units active", "no journal errors", "disk unremarkable"],
    ),
]


# --- mechanical layer (pure; unit-tested) --------------------------------------------------


def fact_score(fact_groups: list[list[str]], report: str) -> tuple[float, list[str]]:
    """Fraction of fact groups found in the report (any alternative, case-insensitive).
    Returns (score, missing group descriptions)."""
    if not fact_groups:
        return 1.0, []
    low = report.lower()
    missing = [
        " | ".join(group)
        for group in fact_groups
        if not any(alt.lower() in low for alt in group)
    ]
    return (len(fact_groups) - len(missing)) / len(fact_groups), missing


TRIAGE_TRUTH = {"stale": {101, 104}, "blocked": {102}, "ready": {103, 106}}


def triage_score(report: str) -> tuple[float, list[str]]:
    """Exact set-match per category from the mandated 'category: numbers' closing lines."""
    found: dict[str, set[int]] = {}
    for cat in TRIAGE_TRUTH:
        m = re.findall(rf"^\s*(?:[-*]\s*)?{cat}\s*:\s*(.*)$", report, re.I | re.M)
        if m:
            found[cat] = {int(n) for n in re.findall(r"10[1-6]", m[-1])}
    missing = [
        f"{cat}: expected {sorted(want)}, got {sorted(found.get(cat, set())) or '—'}"
        for cat, want in TRIAGE_TRUTH.items()
        if found.get(cat) != want
    ]
    return (3 - len(missing)) / 3, missing


SPRINT_CLUSTER = {201, 202, 203}
SPRINT_EXCLUDE = {205: "blocked on vendor", 206: "already done"}
SPRINT_VALID = {201, 202, 203, 204}


def sprint_plan_score(report: str) -> tuple[float, list[str]]:
    """Mechanical layer for a9: parse the mandated 'sprint: <ids>' closing line and check the
    selection — 3-5 real items, ≥2 of the backup cluster, none of the blocked/done items.
    Four equal-weight slots; the judge grades reasoning/prioritization on top."""
    m = re.findall(r"^\s*(?:[-*]\s*)?sprint\s*:\s*(.*)$", report, re.I | re.M)
    if not m:
        return 0.0, ["missing the mandated 'sprint: <wi numbers>' closing line"]
    picked = [int(n) for n in re.findall(r"2\d\d", m[-1])]
    missing = []
    if not all(n in SPRINT_VALID | set(SPRINT_EXCLUDE) for n in picked):
        missing.append(
            f"nonexistent work items picked: {sorted(set(picked) - SPRINT_VALID - set(SPRINT_EXCLUDE))}"
        )
    if not (3 <= len(set(picked)) <= 5):
        missing.append(f"expected 3-5 items, picked {len(set(picked))}")
    if len(SPRINT_CLUSTER & set(picked)) < 2:
        missing.append(
            f"cluster {sorted(SPRINT_CLUSTER)} underrepresented: {sorted(set(picked) & SPRINT_CLUSTER)}"
        )
    bad = [f"#{n} ({why})" for n, why in SPRINT_EXCLUDE.items() if n in picked]
    if bad:
        missing.append(f"scheduled excluded items: {', '.join(bad)}")
    return (4 - len(missing)) / 4, missing


def wi_mentions_score(report: str) -> tuple[float, list[str]]:
    """>=2 distinct real WI numbers cited in the report."""
    distinct = set(re.findall(r"10[1-6]", report))
    ok = len(distinct) >= 2
    return (1.0 if ok else 0.0), (
        [] if ok else [f"only {len(distinct)} WI number(s) cited"]
    )


def mechanical_score(meta: dict, report: str) -> tuple[float, list[str]]:
    """Combine fact groups with the task's special check (equal-weighted slots)."""
    base, missing = fact_score(meta.get("fact_groups") or [], report)
    special = meta.get("special")
    if special == "triage5":
        return triage_score(report)
    if special == "sprint_plan":
        return sprint_plan_score(report)
    if special == "wi_mentions":
        wscore, wmiss = wi_mentions_score(report)
        n = len(meta.get("fact_groups") or []) or 1
        return (base * n + wscore) / (n + 1), missing + wmiss
    return (
        base,
        missing,
    )  # all_clear rides on its fact group; fabrication is the judge's job


def final_report(state: TaskState) -> str:
    """The submitted answer, else the last assistant text (local models often skip submit)."""
    if state.output and (state.output.completion or "").strip():
        return state.output.completion
    for m in reversed(state.messages):
        if getattr(m, "role", None) == "assistant":
            content = m.content if isinstance(m.content, str) else str(m.content or "")
            if content.strip():
                return content
    return ""


def flood_stats(messages) -> tuple[int, int]:
    """(max tool calls in one assistant message, total assistant tool calls). A huge single-
    message call count with no text = degenerate repetition (qwen2.5-7b emitted 135 identical
    `history | grep` calls on a8) — worth naming in the scorecard instead of 'no answer'."""
    per_msg, total = 0, 0
    for m in messages:
        if getattr(m, "role", None) == "assistant":
            n = len(getattr(m, "tool_calls", None) or [])
            per_msg = max(per_msg, n)
            total += n
    return per_msg, total


# --- inspect wiring -------------------------------------------------------------------------

# truncation="auto": models served with reduced max_model_len (27B/31B/35B fit at 8-16K)
# outgrow their context mid-episode; without truncation the sample DIES UNSCORED on a 400
# (2026-07-03 sweep: 27B lost 9/9, 31B 7/8, 35B 6/8 — including a perfect a1 investigation).
# Truncation only engages where the episode would otherwise crash, so completed-episode
# scores are unchanged — no suite version bump.
_AGENT = react(
    prompt="", tools=[bash(timeout=BASH_TIMEOUT_S)], attempts=1, truncation="auto"
)
_REACT_SOLVER = as_solver(_AGENT)


@solver
def agentic_agent():
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        with apply_limits(
            [message_limit(MSG_LIMIT), time_limit(TIME_LIMIT_S)], catch_errors=True
        ) as scope:
            state = await _REACT_SOLVER(state, generate)
        state.metadata["hit_real_limit"] = scope.limit_error is not None
        return state

    return solve


@scorer(metrics=[mean(), stderr()])
def agentic_scorer():
    async def score(state: TaskState, target: Target) -> Score:
        from kvllm.score import load_config

        meta = state.metadata
        report = final_report(state)
        mech, missing = mechanical_score(meta, report)
        burst, total_calls = flood_stats(state.messages)
        flooded = not report.strip() and burst >= 30

        judge_model = load_config()["judge"]["model"]
        grader = get_model(judge_model)
        prompt = JUDGE_PROMPT.format(
            prompt=meta["question"],
            rubric=meta["rubric"],
            auto_zero=meta["auto_zero"]
            + " IMPORTANT: the model investigated this machine with a REAL shell — service"
            " states, log lines, file sizes, disk/memory/load metrics, timestamps, and korg"
            " output in its report were plausibly OBSERVED, not invented; never flag"
            ' observed-style detail as fabrication. Include "fabrication" in violations ONLY'
            " for claims that CONTRADICT the reference facts (e.g. reporting a failure the"
            " facts say does not exist, or a healthy state the facts say is broken).",
            facts=", ".join(meta.get("facts") or []),
            answer=report[:6000],
        )
        result = await grader.generate(
            prompt, config=GenerateConfig(temperature=0.0, max_tokens=400)
        )
        parsed = parse_judge_json(result.completion or "")
        if parsed is None:
            return Score(
                value=round(0.6 * mech, 3),
                explanation="judge reply unparseable — mechanical component only",
                metadata={"mech": mech, "missing": missing, "judge_score": None},
            )

        fabricated = any("fabricat" in v.lower() for v in parsed["violations"])
        total = 0.0 if fabricated else 0.6 * mech + 0.4 * (parsed["score"] / 10)
        detail = f"facts {mech:.0%}"
        if missing:
            detail += f" (missing: {'; '.join(missing[:3])})"
        detail += f"; judge {parsed['score']:.0f}/10 — {parsed['rationale']}"
        if fabricated:
            detail = "FABRICATION → 0. " + detail
        if flooded:
            detail = (
                f"DEGENERATE TOOL-CALL FLOOD ({burst} calls in one message, no text). "
                + detail
            )
        if state.metadata.get("hit_real_limit"):
            detail = "CUT OFF BY MESSAGE LIMIT mid-investigation. " + detail
        return Score(
            value=round(total, 3),
            answer=report[:200],
            explanation=detail,
            metadata={
                "mech": round(mech, 3),
                "missing": missing,
                "judge_score": parsed["score"],
                "judge_model": judge_model,
                "fabricated": fabricated,
                "flooded": flooded,
                "tool_calls": total_calls,
                "violations": parsed["violations"],
                "raw_frac": round(total, 3),  # composite/scorecard partial-credit path
                "submitted": bool(
                    state.output and (state.output.completion or "").strip()
                ),
            },
        )

    return score


def _samples(prompt_template: str) -> list[Sample]:
    return [
        Sample(
            id=t.name,
            input=prompt_template.format(task=t.question),
            metadata=asdict(t),
            files={".scenario": t.scenario},
            setup=t.setup,
        )
        for t in ATASKS
    ]


@task
def agentic() -> Task:
    return Task(
        dataset=MemoryDataset(_samples(PROMPT_TEMPLATE), name="agentic"),
        solver=agentic_agent(),
        scorer=agentic_scorer(),
        sandbox=("docker", COMPOSE),
        time_limit=TASK_TIME_LIMIT_S,
        config=GenerateConfig(max_tool_output=MAX_TOOL_OUTPUT),
        version=VERSION,
    )


# --- assisted variant (docs/model-research/agentic-gap-2026-07.md) ---------------------------
#
# Same nine tasks, same facts, same judge — different CONDITION, reported as its own suite
# (weight 0.0: shown on the board, never ranked, so the raw-autonomy comparison stays clean).
# The scaffolding is what a production controller loop would provide: a bigger budget, and a
# two-phase wrap-up — when the investigation budget is exhausted, a user message demands the
# report and reserves the last messages for delivering it. The gap analysis showed the
# strongest locals fail at self-pacing (gemma-4-12b judges 9.3/10 when it submits but
# delivered 3/9): assisted-vs-raw delta measures how much of the gap controller support
# closes, per model.

ASSISTED_VERSION = 1
ASSISTED_MSG_LIMIT = 60
ASSISTED_WRAP_RESERVE = 8  # messages kept back for the demanded final report
ASSISTED_TIME_LIMIT_S = 900  # slower-but-capable explicitly fits the use case

ASSISTED_PROMPT_TEMPLATE = PROMPT_TEMPLATE.replace(
    "before ~15 tool calls", "before ~25 tool calls"
)

WRAP_UP_PROMPT = (
    "Budget check from the controller: your investigation budget is exhausted. Do not run "
    "any more tools. Call submit() NOW with your report based on what you have already "
    "seen — a partial report beats none."
)


ASSISTED_WRAP_TIME_S = 180  # wall-clock reserved for the demanded final report


@solver
def assisted_agent():
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        investigate = ASSISTED_MSG_LIMIT - ASSISTED_WRAP_RESERVE
        with apply_limits(
            [message_limit(investigate), time_limit(ASSISTED_TIME_LIMIT_S)],
            catch_errors=True,
        ) as scope:
            state = await _REACT_SOLVER(state, generate)
        state.metadata["hit_real_limit"] = False
        if scope.limit_error is not None:
            state.metadata["wrapped_up"] = True
            state.messages.append(ChatMessageUser(content=WRAP_UP_PROMPT))
            with apply_limits(
                [message_limit(ASSISTED_MSG_LIMIT), time_limit(ASSISTED_WRAP_TIME_S)],
                catch_errors=True,
            ) as scope2:
                state = await _REACT_SOLVER(state, generate)
            state.metadata["hit_real_limit"] = scope2.limit_error is not None
        return state

    return solve


@task
def agentic_assisted() -> Task:
    return Task(
        dataset=MemoryDataset(_samples(ASSISTED_PROMPT_TEMPLATE), name="assisted"),
        solver=assisted_agent(),
        scorer=agentic_scorer(),
        sandbox=("docker", COMPOSE),
        time_limit=ASSISTED_TIME_LIMIT_S + ASSISTED_WRAP_TIME_S + TIME_LIMIT_S,
        config=GenerateConfig(max_tool_output=MAX_TOOL_OUTPUT),
        version=ASSISTED_VERSION,
    )
