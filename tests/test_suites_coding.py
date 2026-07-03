"""Unit tests for the coding suite's pure functions (suites/coding.py).

No Docker / no model / no inspect run — parse_junit and extract_coding_signals are pure. The
end-to-end scorer path (sandbox exec, hidden-test injection) is covered by `just test-coding-suite`.
"""

from __future__ import annotations

from types import SimpleNamespace

from suites.coding import (
    ASSETS,
    TASKS,
    _is_test_run,
    _output_indicates_failure,
    _seed_files,
    extract_coding_signals,
    parse_junit,
)


def _bash(cmd, cid):
    return SimpleNamespace(function="bash", arguments={"command": cmd}, id=cid)


def _submit(cid="s"):
    return SimpleNamespace(function="submit", arguments={"answer": "done"}, id=cid)


def _asst(calls):
    return SimpleNamespace(role="assistant", tool_calls=calls)


def _tool(cid, content, error=None):
    return SimpleNamespace(role="tool", tool_call_id=cid, content=content, error=error)


# --- parse_junit -----------------------------------------------------------------------


def test_parse_junit_all_pass():
    xml = '<testsuite tests="2"><testcase name="a"/><testcase name="b"/></testsuite>'
    assert parse_junit(xml) == (2, 2, [])


def test_parse_junit_some_fail():
    xml = (
        '<testsuite tests="3"><testcase name="a"/>'
        '<testcase name="b"><failure message="x"/></testcase>'
        '<testcase name="c"/></testsuite>'
    )
    assert parse_junit(xml) == (2, 3, ["b"])


def test_parse_junit_error_counts_as_failed():
    xml = '<testsuite><testcase name="a"><error/></testcase></testsuite>'
    assert parse_junit(xml) == (0, 1, ["a"])


def test_parse_junit_testsuites_root():
    xml = (
        '<testsuites><testsuite><testcase name="a"/>'
        '<testcase name="b"><failure/></testcase></testsuite></testsuites>'
    )
    assert parse_junit(xml) == (1, 2, ["b"])


def test_parse_junit_empty_or_bad():
    assert parse_junit("") == (0, 0, [])
    assert parse_junit("not xml <<<") == (0, 0, [])
    assert parse_junit('<testsuite tests="0"></testsuite>') == (0, 0, [])


# --- _is_test_run / _output_indicates_failure -----------------------------------------


def test_is_test_run():
    assert _is_test_run("python -m pytest tests/")
    assert _is_test_run("pytest .hidden_tests/")
    assert _is_test_run("python test_rolling.py")
    assert _is_test_run("python3 tests/test_x.py")
    assert not _is_test_run("python solve.py")
    assert not _is_test_run("ls -la")
    assert not _is_test_run("")


def test_output_indicates_failure():
    assert _output_indicates_failure("1 failed, 2 passed")
    assert _output_indicates_failure("FAILED tests/test_x.py::test_y")
    assert _output_indicates_failure("Traceback (most recent call last):")
    assert _output_indicates_failure("E   AssertionError")
    assert _output_indicates_failure("", error="nonzero exit")
    assert not _output_indicates_failure("3 passed in 0.02s")
    assert not _output_indicates_failure("")


# --- extract_coding_signals -----------------------------------------------------------


def test_signals_recovered_path():
    msgs = [
        _asst([_bash("python -m pytest tests/", "1")]),
        _tool("1", "1 failed, 2 passed\nFAILED test_x"),
        _asst([_bash("python -m pytest tests/", "2")]),
        _tool("2", "3 passed in 0.1s"),
        _asst([_submit()]),
    ]
    sig = extract_coding_signals(msgs)
    assert sig == {"test_runs": 2, "saw_failing_run": True, "submitted": True}


def test_signals_no_tests_run():
    msgs = [
        _asst([_bash("cat solve.py", "1")]),
        _tool("1", "..."),
        _asst([_submit()]),
    ]
    sig = extract_coding_signals(msgs)
    assert sig["test_runs"] == 0
    assert sig["saw_failing_run"] is False
    assert sig["submitted"] is True


def test_signals_hit_limit_no_submit():
    msgs = [_asst([_bash("python -m pytest tests/", "1")]), _tool("1", "3 passed")]
    sig = extract_coding_signals(msgs)
    assert sig["submitted"] is False  # -> scorer treats as hit_limit
    assert sig["saw_failing_run"] is False


def test_signals_failure_only_counted_for_test_runs():
    # a failing NON-test command must not set saw_failing_run
    msgs = [
        _asst([_bash("cat missing.py", "1")]),
        _tool("1", "cat: missing.py: No such file", error="exit 1"),
        _asst([_submit()]),
    ]
    assert extract_coding_signals(msgs)["saw_failing_run"] is False


# --- manifest sanity ------------------------------------------------------------------


def test_manifest_has_15_tasks_with_assets():
    assert len(TASKS) == 15
    tiers = {}
    for t in TASKS:
        tiers[t.tier] = tiers.get(t.tier, 0) + 1
        base = ASSETS / t.id
        assert (base / "prompt.md").is_file(), t.id
        assert list((base / "hidden").glob("*.py")), t.id
        assert list((base / "solution").rglob("*.py")), t.id
    assert tiers == {"C1": 6, "C2": 4, "C3": 3, "C4": 2}


def test_c3_c4_have_seed_files():
    for tid in (
        "c3-inventory",
        "c3-todo-due",
        "c3-stats-pure",
        "c4-rolling",
        "c4-lru-bugs",
    ):
        assert _seed_files(tid), tid
