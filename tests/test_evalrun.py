"""kvllm.evalrun unit tests — sandbox host selection (pure env/config logic, no Docker)."""

from __future__ import annotations

import os

from kvllm import evalrun, score


def test_sandbox_host_from_config(monkeypatch):
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(
        score, "load_config", lambda: {"sandbox": {"docker_host": "ssh://ken@ksandbox"}}
    )
    evalrun._apply_sandbox_host()
    assert os.environ["DOCKER_HOST"] == "ssh://ken@ksandbox"


def test_sandbox_host_env_wins(monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    monkeypatch.setattr(
        score, "load_config", lambda: {"sandbox": {"docker_host": "ssh://ken@ksandbox"}}
    )
    evalrun._apply_sandbox_host()
    assert os.environ["DOCKER_HOST"] == "unix:///var/run/docker.sock"


def test_sandbox_host_absent_leaves_env_alone(monkeypatch):
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(score, "load_config", lambda: {})
    evalrun._apply_sandbox_host()
    assert "DOCKER_HOST" not in os.environ


def test_run_suites_clears_stale_manifest_and_retries(tmp_path, monkeypatch):
    """eval_set rejecting same-day logs from an older task manifest → the suite dir is
    cleared and eval_set retried once; other errors propagate untouched."""
    import inspect_ai

    sdir = tmp_path / "tools"
    sdir.mkdir()
    (sdir / "old.eval").write_text("stale")
    calls = []

    def fake_eval_set(**kw):
        calls.append(kw)
        if len(calls) == 1:
            raise RuntimeError(
                "Existing log file 'old.eval' in log_dir is not associated with a task "
                "passed to eval_set (you must run eval_set in a fresh log directory)."
            )
        return True, []

    monkeypatch.setattr(inspect_ai, "eval_set", fake_eval_set)
    monkeypatch.setattr(score, "load_config", lambda: {})
    results, usage, judge = evalrun._run_suites(
        "mockllm/model", {"tools": (lambda: None, 2)}, tmp_path, local=False
    )
    assert len(calls) == 2
    assert not sdir.exists() or not list(sdir.glob("*.eval"))
    assert results["tools"]["error"] == "no inspect log produced"


def test_run_suites_other_errors_propagate(tmp_path, monkeypatch):
    import inspect_ai
    import pytest

    def fake_eval_set(**kw):
        raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(inspect_ai, "eval_set", fake_eval_set)
    monkeypatch.setattr(score, "load_config", lambda: {})
    with pytest.raises(RuntimeError, match="CUDA"):
        evalrun._run_suites(
            "mockllm/model", {"tools": (lambda: None, 2)}, tmp_path, local=False
        )


def test_suites_for_excludes_optional_by_default():
    suites = {
        "agentic": (None, 2, "tools", False),
        "assisted": (None, 1, "tools", True),
    }
    entry = {"capabilities": ["tools"]}
    assert set(evalrun._suites_for(entry, None, suites)) == {"agentic"}
    assert set(evalrun._suites_for(entry, "assisted", suites)) == {"assisted"}
    assert set(evalrun._suites_for(entry, "agentic", suites)) == {"agentic"}
    assert evalrun._suites_for({"capabilities": ["chat"]}, "assisted", suites) == {}


def test_stale_suites_drops_current_keeps_missing_and_stale():
    to_run = {
        "tools": (None, 2),
        "agentic": (None, 2),
        "vision": (None, 1),
    }
    prior = {
        "suites": {
            "tools": {"version": 2, "pass_rate": 1.0},  # current → drop
            "agentic": {"version": 1, "pass_rate": 0.2},  # stale → keep
            # vision absent → keep
        }
    }
    out = evalrun._stale_suites(to_run, prior)
    assert set(out) == {"agentic", "vision"}


def test_stale_suites_reruns_errored_and_handles_no_prior():
    to_run = {"code": (None, 1)}
    prior = {"suites": {"code": {"version": 1, "error": "no inspect log produced"}}}
    assert set(evalrun._stale_suites(to_run, prior)) == {"code"}
    assert evalrun._stale_suites(to_run, None) == to_run
