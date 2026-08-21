"""kvllm.helper unit tests — the eval-monitor route.

Route functions are called directly (no TestClient, no httpx): they are plain functions
returning plain dicts, and the point under test is the contract the dashboard consumes.
"""

from __future__ import annotations

import json

from kvllm import helper, runstate


def test_api_eval_is_null_when_no_eval_has_ever_run(tmp_path, monkeypatch):
    monkeypatch.setenv("KVLLM_RUN_STATE", str(tmp_path / "run.json"))
    assert helper.api_eval() == {"run": None}


def test_api_eval_reports_a_live_run(tmp_path, monkeypatch):
    monkeypatch.setenv("KVLLM_RUN_STATE", str(tmp_path / "run.json"))
    runstate.reset()
    try:
        runstate.begin(models=["claude-sonnet-5"], argv=[], label="noise-floor r1/3")
        runstate.set_model("claude-sonnet-5", 1, 1)
        runstate.set_suite("agentic")
        run = helper.api_eval()["run"]
    finally:
        runstate.reset()
    assert run["alive"] is True
    assert run["label"] == "noise-floor r1/3"
    assert run["current"]["model"] == "claude-sonnet-5"
    assert run["current"]["suite"] == "agentic"


def test_api_eval_reports_a_dead_run_as_not_alive(tmp_path, monkeypatch):
    """The failure this whole route exists for: a runner that died without writing a
    terminal status must not read as still running."""
    state = tmp_path / "run.json"
    monkeypatch.setenv("KVLLM_RUN_STATE", str(state))
    state.write_text(
        json.dumps(
            {
                "pid": 2**30,  # far past any live pid
                "status": "running",
                "started": "2026-08-20T22:00:00Z",
                "models": ["gemma-4-31b-it-awq"],
                "current": None,
                "completed": [],
            }
        )
    )
    assert helper.api_eval()["run"]["alive"] is False


def test_api_eval_survives_a_corrupt_state_file(tmp_path, monkeypatch):
    """A monitor must not 500 because something scribbled on the file."""
    state = tmp_path / "run.json"
    monkeypatch.setenv("KVLLM_RUN_STATE", str(state))
    state.write_text("{not json")
    assert helper.api_eval() == {"run": None}
