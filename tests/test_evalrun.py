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


# --- provenance (sprint 15) ---------------------------------------------------------------


class _FakeResp:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_vllm_version_asks_the_serving_endpoint(monkeypatch):
    seen = {}

    def fake_urlopen(url, timeout=None):
        seen["url"] = url
        return _FakeResp(b'{"version": "0.27.1"}')

    monkeypatch.setattr(evalrun.urllib.request, "urlopen", fake_urlopen)
    # /version lives at the root, not under /v1 — the base_url suffix must be stripped.
    assert evalrun._vllm_version("http://localhost:8000/v1") == "0.27.1"
    assert seen["url"] == "http://localhost:8000/version"


def test_vllm_version_strips_trailing_slash(monkeypatch):
    seen = {}

    def fake_urlopen(url, timeout=None):
        seen["url"] = url
        return _FakeResp(b'{"version": "0.27.1"}')

    monkeypatch.setattr(evalrun.urllib.request, "urlopen", fake_urlopen)
    evalrun._vllm_version("http://remote:8000/v1/")
    assert seen["url"] == "http://remote:8000/version"


def test_vllm_version_falls_back_to_installed_package(monkeypatch):
    def boom(url, timeout=None):
        raise OSError("no /version on this build")

    monkeypatch.setattr(evalrun.urllib.request, "urlopen", boom)
    # Falls back rather than raising — provenance must never break an eval run.
    assert evalrun._vllm_version("http://localhost:8000/v1") is not None


def test_vllm_version_no_endpoint_uses_local_package():
    assert evalrun._vllm_version(None) is not None


def test_resolve_model_ignores_non_anthropic_providers():
    assert evalrun._resolve_model("openai/gpt-4o") is None


def test_resolve_model_returns_id_and_created_date(monkeypatch):
    import datetime

    import anthropic

    class _M:
        id = "claude-sonnet-5"
        created_at = datetime.datetime(2026, 6, 29, tzinfo=datetime.timezone.utc)

    monkeypatch.setattr(
        anthropic.resources.models.Models, "retrieve", lambda self, *a, **k: _M()
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")
    assert evalrun._resolve_model("anthropic/claude-sonnet-5") == {
        "id": "claude-sonnet-5",
        "created_at": "2026-06-29",
    }


def test_resolve_model_returns_none_when_api_unreachable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")

    import anthropic

    def boom(*a, **k):
        raise anthropic.APIConnectionError(request=None)

    monkeypatch.setattr(anthropic.resources.models.Models, "retrieve", boom)
    # Best-effort: an unresolvable model yields no provenance, not a failed eval.
    assert evalrun._resolve_model("anthropic/claude-sonnet-5") is None


# --- cost accounting (sprint 15 bugfix) ---------------------------------------------------


def test_total_usage_counts_suites_carried_forward_from_other_dates(
    tmp_path, monkeypatch
):
    """The bug: totals were globbed from ONE date dir, so suites carried forward by
    merge_prior_suites (which live under an earlier date) were never counted — the board
    reported a partial-run cost as the full-suite cost."""
    monkeypatch.setattr(evalrun, "REPO", tmp_path)
    seen = []

    def fake_usage_from_log(path, model_str):
        seen.append(str(path))
        return {"input": 10, "output": 1}, {"input": 2, "output": 0}

    monkeypatch.setattr(evalrun.score, "usage_from_log", fake_usage_from_log)

    # Two suites from an older date (carried forward) + one from today, as a real card looks.
    suites = {}
    for cap, date in [
        ("agentic", "2026-07-02"),
        ("code", "2026-07-02"),
        ("judged", "2026-07-04"),
    ]:
        rel = f"eval-logs/m/{date}/{cap}/run.eval"
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x")
        suites[cap] = {"log": rel}

    usage, judge = evalrun._total_usage(suites, "anthropic/claude-sonnet-5")
    assert len(seen) == 3, f"every suite on the card must be counted, got {seen}"
    assert usage == {"input": 30, "output": 3}
    assert judge == {"input": 6, "output": 0}


def test_total_usage_skips_missing_logs_without_failing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(evalrun, "REPO", tmp_path)
    monkeypatch.setattr(
        evalrun.score, "usage_from_log", lambda p, m: ({"input": 5}, {"input": 1})
    )
    present = "eval-logs/m/2026-08-20/tools/run.eval"
    (tmp_path / present).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / present).write_text("x")
    suites = {
        "tools": {"log": present},
        "code": {"log": "eval-logs/m/2026-08-20/code/gone.eval"},  # deleted transcript
        "vision": {},  # no log recorded at all
    }
    usage, _ = evalrun._total_usage(suites, "m")
    # Cost accounting is best-effort: a pruned transcript must not crash a run, but it must
    # say so rather than silently under-reporting.
    assert usage == {"input": 5}
    assert "not counted" in capsys.readouterr().err
