"""Unit tests for kvllm.eval.runner._verdict — no network / no vLLM."""

from __future__ import annotations

from kvllm.eval.runner import MIN_TOKENS_PER_SEC, _verdict


def test_not_served_is_skip():
    assert _verdict(served=False, suites={}) == "skip"


def test_served_no_suites_is_worth_trying():
    assert _verdict(served=True, suites={}) == "worth trying"


def test_served_all_suites_pass_threshold():
    suites = {"tools": {"pass_rate": 1.0}}
    assert _verdict(served=True, suites=suites) == "worth trying"


def test_served_suite_below_threshold_has_issues():
    suites = {"tools": {"pass_rate": 0.5}}
    assert _verdict(served=True, suites=suites) == "has issues"


def test_served_passing_but_too_slow_has_issues():
    suites = {"tools": {"pass_rate": 1.0}}
    tps = MIN_TOKENS_PER_SEC - 0.1
    assert _verdict(served=True, suites=suites, tps=tps) == "has issues"


def test_served_passing_and_fast_enough_worth_trying():
    suites = {"tools": {"pass_rate": 1.0}}
    tps = MIN_TOKENS_PER_SEC + 5
    assert _verdict(served=True, suites=suites, tps=tps) == "worth trying"


def test_tps_none_does_not_downgrade():
    suites = {"tools": {"pass_rate": 1.0}}
    assert _verdict(served=True, suites=suites, tps=None) == "worth trying"
