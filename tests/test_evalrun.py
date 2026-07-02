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
