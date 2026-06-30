"""Eval suites + mechanical scorers, keyed by skillset (registry `capabilities`).

MVP ships the `tool_use` suite (mechanical, objective). Coding / vision / agentic suites and the
LLM-judge scorer are scaffolded as follow-ups (see SUITES + score_case). Suites are defined in code
for now — small, typed, no parsing; they can move to data files if non-dev editing is wanted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

# --- shared tools the tool_use suite binds -----------------------------------------

WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. 'Paris'"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["city"],
        },
    },
}
ADD_TOOL = {
    "type": "function",
    "function": {
        "name": "add",
        "description": "Add two integers.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    },
}


@dataclass
class Case:
    """One eval case. `kind` selects the mechanical scorer in score_case()."""

    name: str
    kind: str  # tool_call | no_tool | multi_turn | parallel
    prompt: str
    tools: list[dict] = field(default_factory=list)
    expect_tool: str | None = None
    expect_args: dict | None = None  # subset match against the parsed arguments
    expect_calls: list[dict] | None = None  # for parallel: [{tool, args}, ...]
    tool_choice: str | None = None  # e.g. "required"
    tool_result: str | None = None  # for multi_turn: fed back as the tool message
    expect_contains: list[str] | None = None  # substrings required in the final answer


TOOL_USE: list[Case] = [
    Case(
        name="single_call",
        kind="tool_call",
        prompt="What's the weather in Paris? Use the tool.",
        tools=[WEATHER_TOOL],
        expect_tool="get_weather",
        expect_args={"city": "Paris"},
    ),
    Case(
        name="enum_arg",
        kind="tool_call",
        prompt="What's the weather in Tokyo in fahrenheit? Use the tool.",
        tools=[WEATHER_TOOL],
        expect_tool="get_weather",
        expect_args={"city": "Tokyo", "unit": "fahrenheit"},
    ),
    Case(
        name="integer_args",
        kind="tool_call",
        prompt="What is 17 + 25? Use the add tool.",
        tools=[ADD_TOOL],
        expect_tool="add",
        expect_args={"a": 17, "b": 25},
    ),
    Case(
        name="no_unneeded_call",
        kind="no_tool",
        prompt="Reply with exactly the word: hello",
        tools=[WEATHER_TOOL, ADD_TOOL],
    ),
    Case(
        name="forced_choice",
        kind="tool_call",
        prompt="The weather in Berlin.",
        tools=[WEATHER_TOOL],
        tool_choice="required",
        expect_tool="get_weather",
        expect_args={"city": "Berlin"},
    ),
    Case(
        name="multi_turn_roundtrip",
        kind="multi_turn",
        prompt="What's the weather in Paris? Use the tool.",
        tools=[WEATHER_TOOL],
        expect_tool="get_weather",
        tool_result=json.dumps({"city": "Paris", "temp": 21, "unit": "celsius"}),
        expect_contains=["21"],
    ),
    Case(
        name="parallel_calls",
        kind="parallel",
        prompt="Get the weather in both Paris and Tokyo. Call the tool for each.",
        tools=[WEATHER_TOOL],
        expect_calls=[
            {"tool": "get_weather", "args": {"city": "Paris"}},
            {"tool": "get_weather", "args": {"city": "Tokyo"}},
        ],
    ),
]

# Maps a registry capability → the suite to run. Extend as suites land.
SUITES: dict[str, list[Case]] = {"tools": TOOL_USE}
# Follow-ups: "code" → coding suite (sandboxed exec), "vision" → image suite,
# "agentic" → scripted mock-tool scenario; LLM-judge scorer for fuzzy quality.


def _args_subset(expected: dict, actual: dict) -> bool:
    return all(
        str(actual.get(k)).lower() == str(v).lower() for k, v in expected.items()
    )


def score_case(case: Case, message, final_answer: str = "") -> tuple[bool, str]:
    """Mechanically score one case against the assistant message (and, for multi_turn, the
    second-turn `final_answer`). Returns (passed, detail)."""
    calls = list(getattr(message, "tool_calls", None) or [])

    if case.kind == "no_tool":
        return (not calls), (
            "no tool call" if not calls else f"unexpected {calls[0].function.name}"
        )

    if case.kind == "tool_call":
        if not calls:
            return False, "no tool call emitted"
        c = calls[0]
        if c.function.name != case.expect_tool:
            return False, f"called {c.function.name}, expected {case.expect_tool}"
        try:
            args = json.loads(c.function.arguments or "{}")
        except json.JSONDecodeError:
            return False, f"unparseable arguments: {c.function.arguments!r}"
        if case.expect_args and not _args_subset(case.expect_args, args):
            return False, f"args {args} missing {case.expect_args}"
        return True, f"{c.function.name}({args})"

    if case.kind == "parallel":
        want = case.expect_calls or []
        got = []
        for c in calls:
            try:
                got.append((c.function.name, json.loads(c.function.arguments or "{}")))
            except json.JSONDecodeError:
                pass
        matched = sum(
            any(n == w["tool"] and _args_subset(w["args"], a) for n, a in got)
            for w in want
        )
        ok = matched == len(want)
        return ok, f"matched {matched}/{len(want)} parallel calls (got {len(calls)})"

    if case.kind == "multi_turn":
        if not calls:
            return False, "no initial tool call"
        answer = final_answer or ""
        missing = [s for s in (case.expect_contains or []) if s not in answer]
        if missing:
            return False, f"final answer missing {missing}: {answer[:80]!r}"
        return True, f"round-trip ok: {answer[:60]!r}"

    return False, f"unknown case kind {case.kind}"
