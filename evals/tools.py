"""S1 `tools` suite — the mechanical tool-calling battery, as an Inspect task.

v2 of the Sprint 7 suite: the original 7 cases (single/enum/integer args, negative no-call,
forced choice, multi-turn round-trip, parallel calls) plus 4 hard cases from the fable-planning
design — array args, a distractor tool, tool-error recovery, and exact-argument adherence.

Stub tools return canned values so multi-turn cases round-trip deterministically; scoring is
mechanical (score_extract is a pure function — unit-tested in tests/test_evals_tools.py).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Literal

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Target,
    accuracy,
    scorer,
    stderr,
)
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.tool import tool

VERSION = 2  # v1 = the Sprint 7 flat-runner suite (7 cases)

# --- stub tools -----------------------------------------------------------------------
# Deterministic canned returns; the suite tests the *model's* calling behavior, not the tools.


@tool
def get_weather():
    async def execute(city: str, unit: Literal["celsius", "fahrenheit"] = "celsius"):
        """Get the current weather for a city.

        Args:
            city: City name, e.g. 'Paris'.
            unit: Temperature unit.
        """
        temp = 21 if unit == "celsius" else 70
        return json.dumps({"city": city, "temp": temp, "unit": unit})

    return execute


@tool
def add():
    async def execute(a: int, b: int):
        """Add two integers.

        Args:
            a: First addend.
            b: Second addend.
        """
        return str(a + b)

    return execute


@tool
def restart_service():
    async def execute(name: str):
        """Restart a systemd service (stop then start; it comes back up).

        Args:
            name: The service unit name, e.g. 'nginx'.
        """
        return f"restarted {name}"

    return execute


@tool
def stop_service():
    async def execute(name: str):
        """Stop a systemd service (it stays stopped until started again).

        Args:
            name: The service unit name, e.g. 'nginx'.
        """
        return f"stopped {name}"

    return execute


@tool
def run_command():
    async def execute(host: str, argv: list[str]):
        """Run a command on a remote host and return its output.

        Args:
            host: Hostname to run the command on.
            argv: The command as an argv list, e.g. ["ls", "-la"].
        """
        return "(command ran ok)"

    return execute


@tool
def read_file():
    async def execute(path: str):
        """Read a file and return its contents.

        Args:
            path: Absolute path of the file to read.
        """
        # Always errors — the error_recovery case checks the model reports the failure
        # instead of hallucinating file contents.
        return f"ERROR: file not found: {path}"

    return execute


@tool
def set_fan_speed():
    async def execute(device_id: str, percent: int):
        """Set a device's fan speed.

        Args:
            device_id: Device identifier, e.g. 'gpu0'.
            percent: Fan speed percent, 0-100.
        """
        return f"fan on {device_id} set to {percent}%"

    return execute


TOOLS = {
    "get_weather": get_weather,
    "add": add,
    "restart_service": restart_service,
    "stop_service": stop_service,
    "run_command": run_command,
    "read_file": read_file,
    "set_fan_speed": set_fan_speed,
}

# --- cases ------------------------------------------------------------------------------


@dataclass
class Case:
    """One eval case. `kind` selects the mechanical check in score_extract()."""

    name: str
    kind: str  # tool_call | no_tool | parallel | multi_turn | error_recovery
    prompt: str
    tools: list[str] = field(default_factory=list)
    expect_tool: str | None = None
    expect_args: dict | None = None  # subset match against the parsed arguments
    exact_args: bool = False  # require the argument key set to match exactly
    expect_calls: list[dict] | None = None  # for parallel: [{tool, args}, ...]
    tool_choice_required: bool = False  # serve the request with tool_choice="any"
    expect_contains: list[str] | None = (
        None  # multi_turn: ALL must appear in final answer
    )
    expect_contains_any: list[str] | None = None  # error_recovery: ANY must appear


CASES: list[Case] = [
    Case(
        name="single_call",
        kind="tool_call",
        prompt="What's the weather in Paris? Use the tool.",
        tools=["get_weather"],
        expect_tool="get_weather",
        expect_args={"city": "Paris"},
    ),
    Case(
        name="enum_arg",
        kind="tool_call",
        prompt="What's the weather in Tokyo in fahrenheit? Use the tool.",
        tools=["get_weather"],
        expect_tool="get_weather",
        expect_args={"city": "Tokyo", "unit": "fahrenheit"},
    ),
    Case(
        name="integer_args",
        kind="tool_call",
        prompt="What is 17 + 25? Use the add tool.",
        tools=["add"],
        expect_tool="add",
        expect_args={"a": 17, "b": 25},
    ),
    Case(
        name="no_unneeded_call",
        kind="no_tool",
        prompt="Reply with exactly the word: hello",
        tools=["get_weather", "add"],
    ),
    Case(
        name="forced_choice",
        kind="tool_call",
        prompt="The weather in Berlin.",
        tools=["get_weather"],
        tool_choice_required=True,
        expect_tool="get_weather",
        expect_args={"city": "Berlin"},
    ),
    Case(
        name="multi_turn_roundtrip",
        kind="multi_turn",
        prompt="What's the weather in Paris? Use the tool.",
        tools=["get_weather"],
        expect_tool="get_weather",
        expect_contains=["21"],
    ),
    Case(
        name="parallel_calls",
        kind="parallel",
        prompt="Get the weather in both Paris and Tokyo. Call the tool for each.",
        tools=["get_weather"],
        expect_calls=[
            {"tool": "get_weather", "args": {"city": "Paris"}},
            {"tool": "get_weather", "args": {"city": "Tokyo"}},
        ],
    ),
    # --- v2 hard cases ------------------------------------------------------------
    Case(
        name="array_args",
        kind="tool_call",
        prompt="Run `df -h` on the host kubsdb. Use the tool.",
        tools=["run_command"],
        expect_tool="run_command",
        expect_args={"host": "kubsdb", "argv": ["df", "-h"]},
    ),
    Case(
        name="distractor_tool",
        kind="tool_call",
        prompt="The nginx service needs to be restarted. Use a tool.",
        tools=["restart_service", "stop_service"],
        expect_tool="restart_service",
        expect_args={"name": "nginx"},
    ),
    Case(
        name="error_recovery",
        kind="error_recovery",
        prompt=(
            "Read /etc/kvllm/kvllm.conf with the tool and tell me what port it configures. "
            "If you can't read it, say what went wrong."
        ),
        tools=["read_file"],
        expect_tool="read_file",
        expect_contains_any=[
            "not found",
            "does not exist",
            "doesn't exist",
            "couldn't",
            "could not",
            "unable",
            "error",
            "no such file",
        ],
    ),
    Case(
        name="exact_args",
        kind="tool_call",
        prompt="Set the fan on device gpu0 to seventy percent. Use the tool.",
        tools=["set_fan_speed"],
        expect_tool="set_fan_speed",
        expect_args={"device_id": "gpu0", "percent": 70},
        exact_args=True,
    ),
]

# --- extraction + scoring (pure — unit-tested without inspect running) ----------------


@dataclass
class Extract:
    """The transcript facts scoring needs: first assistant message's tool calls, every
    tool name called anywhere, and the final answer text."""

    first_calls: list[dict]  # [{"name", "args": dict, "parse_error": str|None}, ...]
    all_call_names: list[str]
    final_text: str


def extract_transcript(messages, completion: str) -> Extract:
    """Reduce a message history to the Extract scoring operates on. `messages` need only
    have .role, and (on assistant messages) .tool_calls with .function/.arguments/.parse_error."""
    first_calls: list[dict] = []
    all_names: list[str] = []
    first_seen = False
    for m in messages:
        if getattr(m, "role", None) != "assistant":
            continue
        calls = [
            {
                "name": tc.function,
                "args": tc.arguments if isinstance(tc.arguments, dict) else {},
                "parse_error": getattr(tc, "parse_error", None),
            }
            for tc in (getattr(m, "tool_calls", None) or [])
        ]
        all_names += [c["name"] for c in calls]
        if not first_seen:
            first_calls = calls
            first_seen = True
    return Extract(
        first_calls=first_calls, all_call_names=all_names, final_text=completion or ""
    )


def _args_subset(expected: dict, actual: dict) -> bool:
    return all(
        str(actual.get(k)).lower() == str(v).lower() for k, v in expected.items()
    )


def _check_call(meta: dict, call: dict) -> tuple[bool, str]:
    if call["parse_error"]:
        return False, f"unparseable arguments: {call['parse_error']}"
    if call["name"] != meta["expect_tool"]:
        return False, f"called {call['name']}, expected {meta['expect_tool']}"
    args = call["args"]
    expected = meta.get("expect_args") or {}
    if meta.get("exact_args") and set(args) != set(expected):
        return False, f"args keys {sorted(args)} != expected {sorted(expected)}"
    if expected and not _args_subset(expected, args):
        return False, f"args {args} missing {expected}"
    return True, f"{call['name']}({args})"


def score_extract(meta: dict, ex: Extract) -> tuple[bool, str]:
    """Mechanically score one case's transcript. `meta` is an asdict(Case)."""
    kind = meta["kind"]

    if kind == "no_tool":
        if ex.all_call_names:
            return False, f"unexpected call to {ex.all_call_names[0]}"
        return True, "no tool call"

    if kind == "tool_call":
        if not ex.first_calls:
            return False, "no tool call emitted"
        return _check_call(meta, ex.first_calls[0])

    if kind == "parallel":
        want = meta.get("expect_calls") or []
        matched = sum(
            any(
                c["name"] == w["tool"]
                and not c["parse_error"]
                and _args_subset(w["args"], c["args"])
                for c in ex.first_calls
            )
            for w in want
        )
        ok = matched == len(want)
        return ok, (
            f"matched {matched}/{len(want)} parallel calls (got {len(ex.first_calls)})"
        )

    if kind == "multi_turn":
        if not ex.first_calls:
            return False, "no initial tool call"
        ok, detail = _check_call(meta, ex.first_calls[0])
        if not ok:
            return False, detail
        missing = [
            s for s in (meta.get("expect_contains") or []) if s not in ex.final_text
        ]
        if missing:
            return False, f"final answer missing {missing}: {ex.final_text[:80]!r}"
        return True, f"round-trip ok: {ex.final_text[:60]!r}"

    if kind == "error_recovery":
        if meta["expect_tool"] not in ex.all_call_names:
            return False, f"never called {meta['expect_tool']}"
        low = ex.final_text.lower()
        if not any(s in low for s in (meta.get("expect_contains_any") or [])):
            return False, f"did not report the failure: {ex.final_text[:80]!r}"
        return True, f"reported failure: {ex.final_text[:60]!r}"

    return False, f"unknown case kind {kind}"


# --- inspect wiring ---------------------------------------------------------------------


@solver
def tool_case():
    """Bind the case's tools (+ tool_choice), then generate. Single-shot cases leave tool
    calls unexecuted; multi-turn cases run the tool loop so stub results feed back."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        meta = state.metadata
        state.tools = [TOOLS[name]() for name in meta["tools"]]
        if meta.get("tool_choice_required"):
            state.tool_choice = "any"
        mode = "loop" if meta["kind"] in ("multi_turn", "error_recovery") else "none"
        return await generate(state, tool_calls=mode)

    return solve


@scorer(metrics=[accuracy(), stderr()])
def tool_case_scorer():
    async def score(state: TaskState, target: Target) -> Score:
        completion = state.output.completion if state.output else ""
        ex = extract_transcript(state.messages, completion)
        passed, detail = score_extract(state.metadata, ex)
        return Score(value=CORRECT if passed else INCORRECT, explanation=detail)

    return score


@task
def tools() -> Task:
    return Task(
        dataset=MemoryDataset(
            [Sample(id=c.name, input=c.prompt, metadata=asdict(c)) for c in CASES],
            name="tools",
        ),
        solver=tool_case(),
        scorer=tool_case_scorer(),
        config=GenerateConfig(max_tokens=2048),
        message_limit=16,  # caps pathological retry loops in the tool-loop cases
        version=VERSION,
    )
