"""S2 `coding` suite — sandboxed write-run-fix coding tasks (fable-planning/06-coding-suite-spec).

The model works in a Docker /workspace with a `bash` tool (react agent), writes code, runs it,
and iterates. After the episode a custom scorer injects HIDDEN pytest tests the model never saw,
runs them in the sandbox, and scores partial credit from the junit XML — never from the model's
own claims. C4 tasks additionally measure `recovered` (ran tests, saw a failure, still reached
>=80%) — the iteration signal that matters most for our agentic use (fable-planning/03).

Tiers: C1 single function (6), C2 script/IO contract (4), C3 fix/extend a seeded repo (3),
C4 iterate-to-green (2). Assets live in coding_assets/<task-id>/{prompt.md,hidden/,solution/,seed/}.

Scoring, transcript-signal, and junit parsing are pure functions (parse_junit /
extract_coding_signals) unit-tested in tests/test_evals_coding.py without Docker or a live model.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.agent import as_solver, react
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.tool import bash
from inspect_ai.util import apply_limits, message_limit, sandbox

VERSION = 1

ASSETS = Path(__file__).resolve().parent / "coding_assets"
COMPOSE = str(ASSETS / "compose.yaml")

BASH_TIMEOUT_S = 120
TIME_LIMIT_S = 600
TIER_MSG_LIMIT = {"C1": 30, "C2": 30, "C3": 40, "C4": 40}
HIDDEN_DIR = "/workspace/.hidden_tests"

# Wraps the per-task prompt.md (the {task_prompt}) — the full instruction the model receives.
PROMPT_TEMPLATE = """You are working in /workspace inside a Linux container. {task_prompt}

Write your code, run it to check it works, and iterate until you're confident. When done, call \
submit() with a one-line summary. There is no network access."""


@dataclass(frozen=True)
class CodingTask:
    id: str
    tier: str  # C1 | C2 | C3 | C4


TASKS: list[CodingTask] = [
    CodingTask("c1-slugify", "C1"),
    CodingTask("c1-parse-size", "C1"),
    CodingTask("c1-merge-intervals", "C1"),
    CodingTask("c1-dedupe", "C1"),
    CodingTask("c1-parse-duration", "C1"),
    CodingTask("c1-tail-lines", "C1"),
    CodingTask("c2-logsum", "C2"),
    CodingTask("c2-csvfilter", "C2"),
    CodingTask("c2-jsonmerge", "C2"),
    CodingTask("c2-dumon", "C2"),
    CodingTask("c3-inventory", "C3"),
    CodingTask("c3-todo-due", "C3"),
    CodingTask("c3-stats-pure", "C3"),
    CodingTask("c4-rolling", "C4"),
    CodingTask("c4-lru-bugs", "C4"),
]


def _seed_files(task_id: str) -> dict[str, str]:
    """Files to drop into /workspace at episode start (C2 fixtures, C3/C4 skeletons).
    Keyed by path relative to /workspace. Hidden tests are NOT seeded — the scorer injects them."""
    seed = ASSETS / task_id / "seed"
    if not seed.is_dir():
        return {}
    return {
        str(p.relative_to(seed)): p.read_text()
        for p in sorted(seed.rglob("*"))
        if p.is_file()
    }


def _samples() -> list[Sample]:
    samples = []
    for t in TASKS:
        prompt = (ASSETS / t.id / "prompt.md").read_text().strip()
        samples.append(
            Sample(
                id=t.id,
                input=PROMPT_TEMPLATE.format(task_prompt=prompt),
                metadata={"task_id": t.id, "tier": t.tier},
                files=_seed_files(t.id) or None,
            )
        )
    return samples


# --- pure functions (unit-tested without Docker) --------------------------------------

# a bash command that runs the tests (pytest, or `python ... test`)
_TEST_RE = re.compile(r"pytest|python[0-9.]*\s+\S*test", re.IGNORECASE)
# markers that a test run reported a failure/error (pytest passing output has none of these)
_FAIL_RE = re.compile(
    r"FAILED|AssertionError|Traceback|\bfailed\b|\berror\b|no tests ran", re.IGNORECASE
)


def parse_junit(xml_text: str) -> tuple[int, int, list[str]]:
    """(passed, total, failed_names) from a pytest junit XML. total counts testcases;
    a testcase with a <failure>/<error> child counts as failed. Empty/unparseable → (0, 0, [])
    (e.g. a collection error that produced no report), which scores as 0.0."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return 0, 0, []
    cases = list(root.iter("testcase"))
    failed = [
        c.get("name", "")
        for c in cases
        if any(child.tag in ("failure", "error") for child in c)
    ]
    total = len(cases)
    return total - len(failed), total, failed


def _is_test_run(cmd: str) -> bool:
    return bool(_TEST_RE.search(cmd or ""))


def _output_indicates_failure(text: str, error=None) -> bool:
    return bool(error) or bool(_FAIL_RE.search(text or ""))


def extract_coding_signals(messages) -> dict:
    """Reduce a transcript to iteration signals. `messages` need .role, assistant .tool_calls
    (.function/.arguments/.id), and tool messages .tool_call_id/.content/.error."""
    test_call_ids: dict[str, str] = {}
    runs = 0
    saw_failing_run = False
    submitted = False
    for m in messages:
        role = getattr(m, "role", None)
        if role == "assistant":
            for tc in getattr(m, "tool_calls", None) or []:
                if tc.function == "submit":
                    submitted = True
                elif tc.function == "bash":
                    cmd = (tc.arguments or {}).get("command", "")
                    if _is_test_run(cmd):
                        runs += 1
                        test_call_ids[tc.id] = cmd
        elif role == "tool":
            tcid = getattr(m, "tool_call_id", None)
            if tcid in test_call_ids and _output_indicates_failure(
                str(getattr(m, "content", "") or ""), getattr(m, "error", None)
            ):
                saw_failing_run = True
    return {
        "test_runs": runs,
        "saw_failing_run": saw_failing_run,
        "submitted": submitted,
    }


# --- inspect wiring ---------------------------------------------------------------------

_AGENT = react(
    prompt="",  # task-specific guidance rides in the sample input; default ReAct system msg
    tools=[bash(timeout=BASH_TIMEOUT_S)],
    attempts=1,  # single greedy attempt: C4 measures self-iteration, not scorer retries
)
_REACT_SOLVER = as_solver(_AGENT)


@solver
def coding_agent():
    """Run the react agent under the tier's message limit (caught so the sample is still
    scored when the limit is hit — that partial work earns partial, ×0.9, credit)."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        limit = TIER_MSG_LIMIT.get(state.metadata.get("tier"), 40)
        # catch_errors=True: when the limit fires, apply_limits SUPPRESSES the
        # LimitExceededError, so control resumes after the `with` — we must still return a
        # TaskState (react mutates it in place, so it holds the partial transcript). Returning
        # inside the `with` would return None on a caught limit and crash scoring.
        with apply_limits([message_limit(limit)], catch_errors=True):
            state = await _REACT_SOLVER(state, generate)
        return state

    return solve


@scorer(metrics=[mean(), stderr()])
def coding_scorer():
    async def score(state: TaskState, target: Target) -> Score:
        task_id = state.metadata["task_id"]
        tier = state.metadata["tier"]
        sb = sandbox()

        # Inject hidden tests post-episode so the model could never read or game them.
        await sb.exec(["mkdir", "-p", HIDDEN_DIR])
        for f in sorted((ASSETS / task_id / "hidden").glob("*.py")):
            await sb.write_file(f"{HIDDEN_DIR}/{f.name}", f.read_text())

        report = f"{HIDDEN_DIR}/report.xml"
        await sb.exec(
            [
                "python",
                "-m",
                "pytest",
                ".hidden_tests/",
                "-q",
                "--tb=no",
                "-p",
                "no:cacheprovider",
                f"--junitxml={report}",
            ],
            cwd="/workspace",
            env={"PYTHONPATH": "/workspace"},
            timeout=BASH_TIMEOUT_S,
        )
        try:
            xml = await sb.read_file(report)
            xml = xml if isinstance(xml, str) else xml.decode()
        except Exception:
            xml = ""

        passed, total, failed = parse_junit(xml)
        frac = passed / total if total else 0.0

        sig = extract_coding_signals(state.messages)
        hit_limit = not sig["submitted"]
        points = round(frac * (0.9 if hit_limit else 1.0), 3)
        recovered = sig["saw_failing_run"] and frac >= 0.8

        detail = f"{passed}/{total} hidden tests"
        if failed:
            detail += f"; failed: {', '.join(failed[:5])}"
        if hit_limit:
            detail += "; hit message/time limit (×0.9)"
        return Score(
            value=points,
            answer=f"{passed}/{total}",
            explanation=detail,
            metadata={
                "tier": tier,
                "hit_limit": hit_limit,
                "test_runs": sig["test_runs"],
                "saw_failing_run": sig["saw_failing_run"],
                "recovered": recovered,
                "raw_frac": round(frac, 3),
            },
        )

    return score


@task
def coding() -> Task:
    return Task(
        dataset=MemoryDataset(_samples(), name="coding"),
        solver=coding_agent(),
        scorer=coding_scorer(),
        sandbox=("docker", COMPOSE),
        config=GenerateConfig(temperature=0.0),
        time_limit=TIME_LIMIT_S,
        version=VERSION,
    )
