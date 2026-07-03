"""Unit tests for the S1 tools suite's pure scoring (suites/tools.py).

No network / no vLLM / no inspect run — extract_transcript and score_extract are pure
functions over fake message histories. Ports the Sprint 8 Phase 0 suite tests to the v2 shapes
(Inspect pre-parses tool-call arguments into dicts; unparseable args surface as parse_error).
"""

from __future__ import annotations

from dataclasses import asdict
from types import SimpleNamespace

from suites.tools import CASES, Case, Extract, extract_transcript, score_extract


def _call(name: str, args: dict | None = None, parse_error: str | None = None):
    return SimpleNamespace(
        name=name, function=name, arguments=args or {}, parse_error=parse_error
    )


def _assistant(calls: list | None = None):
    return SimpleNamespace(role="assistant", tool_calls=calls or [])


def _meta(name: str) -> dict:
    case = next(c for c in CASES if c.name == name)
    return asdict(case)


def _ex(first_calls=None, all_names=None, final="") -> Extract:
    first_calls = first_calls or []
    return Extract(
        first_calls=first_calls,
        all_call_names=all_names
        if all_names is not None
        else [c["name"] for c in first_calls],
        final_text=final,
    )


def _c(name: str, args: dict | None = None, parse_error: str | None = None) -> dict:
    return {"name": name, "args": args or {}, "parse_error": parse_error}


# --- extract_transcript ---------------------------------------------------------------


def test_extract_first_assistant_message_only():
    messages = [
        SimpleNamespace(role="user"),
        _assistant([_call("get_weather", {"city": "Paris"})]),
        SimpleNamespace(role="tool"),
        _assistant([_call("get_weather", {"city": "Tokyo"})]),
    ]
    ex = extract_transcript(messages, "final")
    assert [c["name"] for c in ex.first_calls] == ["get_weather"]
    assert ex.first_calls[0]["args"] == {"city": "Paris"}
    assert ex.all_call_names == ["get_weather", "get_weather"]
    assert ex.final_text == "final"


def test_extract_no_assistant_messages():
    ex = extract_transcript([SimpleNamespace(role="user")], "")
    assert ex.first_calls == [] and ex.all_call_names == [] and ex.final_text == ""


def test_extract_non_dict_arguments_become_empty():
    ex = extract_transcript(
        [
            _assistant(
                [
                    SimpleNamespace(
                        function="add", arguments="not-a-dict", parse_error="bad json"
                    )
                ]
            )
        ],
        "",
    )
    assert ex.first_calls[0]["args"] == {}
    assert ex.first_calls[0]["parse_error"] == "bad json"


# --- tool_call kinds -----------------------------------------------------------------


def test_single_call_pass():
    passed, detail = score_extract(
        _meta("single_call"), _ex([_c("get_weather", {"city": "Paris"})])
    )
    assert passed and "get_weather" in detail


def test_single_call_no_call_fails():
    passed, detail = score_extract(_meta("single_call"), _ex())
    assert not passed and "no tool call" in detail


def test_single_call_wrong_tool_fails():
    passed, detail = score_extract(
        _meta("single_call"), _ex([_c("add", {"a": 1, "b": 2})])
    )
    assert not passed and "expected get_weather" in detail


def test_single_call_parse_error_fails():
    passed, detail = score_extract(
        _meta("single_call"), _ex([_c("get_weather", {}, parse_error="bad json")])
    )
    assert not passed and "unparseable" in detail


def test_args_subset_is_case_insensitive_and_allows_extras():
    passed, _ = score_extract(
        _meta("single_call"),
        _ex([_c("get_weather", {"city": "paris", "unit": "celsius"})]),
    )
    assert passed


def test_enum_arg_missing_unit_fails():
    passed, detail = score_extract(
        _meta("enum_arg"), _ex([_c("get_weather", {"city": "Tokyo"})])
    )
    assert not passed and "missing" in detail


def test_integer_args_pass():
    passed, _ = score_extract(
        _meta("integer_args"), _ex([_c("add", {"a": 17, "b": 25})])
    )
    assert passed


def test_array_args_pass():
    passed, _ = score_extract(
        _meta("array_args"),
        _ex([_c("run_command", {"host": "kubsdb", "argv": ["df", "-h"]})]),
    )
    assert passed


def test_array_args_wrong_list_fails():
    passed, _ = score_extract(
        _meta("array_args"),
        _ex([_c("run_command", {"host": "kubsdb", "argv": ["df"]})]),
    )
    assert not passed


def test_distractor_tool_wrong_pick_fails():
    passed, detail = score_extract(
        _meta("distractor_tool"), _ex([_c("stop_service", {"name": "nginx"})])
    )
    assert not passed and "expected restart_service" in detail


def test_exact_args_extra_key_fails():
    passed, detail = score_extract(
        _meta("exact_args"),
        _ex([_c("set_fan_speed", {"device_id": "gpu0", "percent": 70, "force": True})]),
    )
    assert not passed and "keys" in detail


def test_exact_args_word_number_pass():
    passed, _ = score_extract(
        _meta("exact_args"),
        _ex([_c("set_fan_speed", {"device_id": "gpu0", "percent": 70})]),
    )
    assert passed


# --- no_tool ------------------------------------------------------------------------


def test_no_tool_pass():
    passed, _ = score_extract(_meta("no_unneeded_call"), _ex())
    assert passed


def test_no_tool_fails_when_called_even_in_later_message():
    ex = _ex(first_calls=[], all_names=["get_weather"])
    passed, detail = score_extract(_meta("no_unneeded_call"), ex)
    assert not passed and "get_weather" in detail


# --- parallel --------------------------------------------------------------------------


def test_parallel_all_matched():
    ex = _ex(
        [_c("get_weather", {"city": "Paris"}), _c("get_weather", {"city": "Tokyo"})]
    )
    passed, detail = score_extract(_meta("parallel_calls"), ex)
    assert passed and "2/2" in detail


def test_parallel_partial_fails():
    ex = _ex([_c("get_weather", {"city": "Paris"})])
    passed, detail = score_extract(_meta("parallel_calls"), ex)
    assert not passed and "1/2" in detail


# --- multi_turn --------------------------------------------------------------------------


def test_multi_turn_pass():
    ex = _ex([_c("get_weather", {"city": "Paris"})], final="It's 21°C in Paris.")
    passed, _ = score_extract(_meta("multi_turn_roundtrip"), ex)
    assert passed


def test_multi_turn_no_initial_call_fails():
    passed, detail = score_extract(_meta("multi_turn_roundtrip"), _ex(final="21"))
    assert not passed and "no initial tool call" in detail


def test_multi_turn_missing_content_fails():
    ex = _ex([_c("get_weather", {"city": "Paris"})], final="It is warm.")
    passed, detail = score_extract(_meta("multi_turn_roundtrip"), ex)
    assert not passed and "missing" in detail


# --- error_recovery ---------------------------------------------------------------------


def test_error_recovery_pass():
    ex = _ex(
        [_c("read_file", {"path": "/etc/kvllm/kvllm.conf"})],
        final="I couldn't read it: file not found.",
    )
    passed, _ = score_extract(_meta("error_recovery"), ex)
    assert passed


def test_error_recovery_never_called_fails():
    passed, detail = score_extract(_meta("error_recovery"), _ex(final="file not found"))
    assert not passed and "never called" in detail


def test_error_recovery_hallucinated_success_fails():
    ex = _ex(
        [_c("read_file", {"path": "/etc/kvllm/kvllm.conf"})],
        final="The configured port is 8000.",
    )
    passed, detail = score_extract(_meta("error_recovery"), ex)
    assert not passed and "did not report" in detail


# --- misc --------------------------------------------------------------------------------


def test_unknown_kind_fails():
    meta = asdict(Case(name="x", kind="bogus", prompt=""))
    passed, detail = score_extract(meta, _ex())
    assert not passed and "unknown case kind" in detail


def test_all_cases_have_registered_tools():
    from suites.tools import TOOLS

    for case in CASES:
        assert case.tools, f"{case.name} binds no tools"
        for name in case.tools:
            assert name in TOOLS, f"{case.name} references unknown tool {name}"
