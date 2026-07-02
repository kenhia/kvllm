"""Unit tests for the mechanical scorers in kvllm.eval.suites.

No network / no vLLM — these are pure functions over fake OpenAI tool-call messages.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from kvllm.eval.suites import Case, _args_subset, score_case


def _call(name: str, args: dict, call_id: str = "call_1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def _message(calls: list | None = None):
    return SimpleNamespace(tool_calls=calls or [])


# --- _args_subset --------------------------------------------------------------------


def test_args_subset_exact_match():
    assert _args_subset({"city": "Paris"}, {"city": "Paris"})


def test_args_subset_actual_has_extra_keys():
    assert _args_subset({"city": "Paris"}, {"city": "Paris", "unit": "celsius"})


def test_args_subset_case_insensitive():
    assert _args_subset({"city": "Paris"}, {"city": "paris"})


def test_args_subset_missing_key_fails():
    assert not _args_subset({"city": "Paris", "unit": "celsius"}, {"city": "Paris"})


def test_args_subset_wrong_value_fails():
    assert not _args_subset({"city": "Paris"}, {"city": "Tokyo"})


# --- score_case: tool_call -------------------------------------------------------------


def test_tool_call_pass():
    case = Case(
        name="c",
        kind="tool_call",
        prompt="",
        expect_tool="get_weather",
        expect_args={"city": "Paris"},
    )
    passed, detail = score_case(
        case, _message([_call("get_weather", {"city": "Paris"})])
    )
    assert passed
    assert "get_weather" in detail


def test_tool_call_no_call_fails():
    case = Case(name="c", kind="tool_call", prompt="", expect_tool="get_weather")
    passed, detail = score_case(case, _message([]))
    assert not passed
    assert "no tool call" in detail


def test_tool_call_wrong_tool_fails():
    case = Case(name="c", kind="tool_call", prompt="", expect_tool="get_weather")
    passed, detail = score_case(case, _message([_call("add", {"a": 1, "b": 2})]))
    assert not passed
    assert "expected get_weather" in detail


def test_tool_call_bad_json_fails():
    case = Case(name="c", kind="tool_call", prompt="", expect_tool="get_weather")
    bad = SimpleNamespace(
        function=SimpleNamespace(name="get_weather", arguments="{not json")
    )
    passed, detail = score_case(case, _message([bad]))
    assert not passed
    assert "unparseable" in detail


def test_tool_call_missing_expected_args_fails():
    case = Case(
        name="c",
        kind="tool_call",
        prompt="",
        expect_tool="get_weather",
        expect_args={"city": "Paris", "unit": "fahrenheit"},
    )
    passed, _ = score_case(case, _message([_call("get_weather", {"city": "Paris"})]))
    assert not passed


# --- score_case: no_tool -----------------------------------------------------------


def test_no_tool_pass():
    case = Case(name="c", kind="no_tool", prompt="")
    passed, _ = score_case(case, _message([]))
    assert passed


def test_no_tool_fails_when_called():
    case = Case(name="c", kind="no_tool", prompt="")
    passed, detail = score_case(
        case, _message([_call("get_weather", {"city": "Paris"})])
    )
    assert not passed
    assert "get_weather" in detail


# --- score_case: parallel -----------------------------------------------------------


def test_parallel_all_matched():
    case = Case(
        name="c",
        kind="parallel",
        prompt="",
        expect_calls=[
            {"tool": "get_weather", "args": {"city": "Paris"}},
            {"tool": "get_weather", "args": {"city": "Tokyo"}},
        ],
    )
    calls = [
        _call("get_weather", {"city": "Paris"}),
        _call("get_weather", {"city": "Tokyo"}),
    ]
    passed, detail = score_case(case, _message(calls))
    assert passed
    assert "2/2" in detail


def test_parallel_partial_match_fails():
    case = Case(
        name="c",
        kind="parallel",
        prompt="",
        expect_calls=[
            {"tool": "get_weather", "args": {"city": "Paris"}},
            {"tool": "get_weather", "args": {"city": "Tokyo"}},
        ],
    )
    calls = [_call("get_weather", {"city": "Paris"})]
    passed, detail = score_case(case, _message(calls))
    assert not passed
    assert "1/2" in detail


# --- score_case: multi_turn -----------------------------------------------------------


def test_multi_turn_pass():
    case = Case(
        name="c",
        kind="multi_turn",
        prompt="",
        expect_tool="get_weather",
        expect_contains=["21"],
    )
    passed, _ = score_case(
        case,
        _message([_call("get_weather", {"city": "Paris"})]),
        final_answer="It's 21C",
    )
    assert passed


def test_multi_turn_no_initial_call_fails():
    case = Case(name="c", kind="multi_turn", prompt="", expect_tool="get_weather")
    passed, detail = score_case(case, _message([]), final_answer="It's 21C")
    assert not passed
    assert "no initial tool call" in detail


def test_multi_turn_missing_expected_content_fails():
    case = Case(
        name="c",
        kind="multi_turn",
        prompt="",
        expect_tool="get_weather",
        expect_contains=["21"],
    )
    passed, detail = score_case(
        case,
        _message([_call("get_weather", {"city": "Paris"})]),
        final_answer="It's cold",
    )
    assert not passed
    assert "missing" in detail


# --- score_case: unknown kind -------------------------------------------------------


def test_unknown_kind_fails():
    case = Case(name="c", kind="bogus", prompt="")
    passed, detail = score_case(case, _message([]))
    assert not passed
    assert "unknown case kind" in detail
