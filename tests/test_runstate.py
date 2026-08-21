"""kvllm.runstate unit tests — the run-state file the eval runner writes about itself.

Pure file/clock logic: no eval, no GPU, no network. The behaviour under test is the one
sprint 15 got wrong by inferring state from the outside — liveness must key on the recorded
PID, a finished run must read as finished, and a run killed without cleanup must not read
as alive.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from kvllm import runstate


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    """Every test gets its own state file and a clean module (no leakage between tests)."""
    monkeypatch.setenv("KVLLM_RUN_STATE", str(tmp_path / "run.json"))
    runstate.reset()
    yield
    runstate.reset()


def _dead_pid() -> int:
    """A pid that is certainly not running: past the highest one /proc knows about."""
    live = [int(p.name) for p in Path("/proc").iterdir() if p.name.isdigit()]
    return max(live) + 5000


def test_read_missing_returns_none():
    assert runstate.read() is None


def test_setters_are_noops_before_begin():
    """The runner instruments unconditionally; nothing is recorded until begin()."""
    runstate.set_model("gemma", 1, 2)
    runstate.set_suite("agentic")
    runstate.end("done", 0)
    assert runstate.read() is None


def test_begin_records_pid_models_and_running_status():
    runstate.begin(
        models=["claude-sonnet-5"], argv=["claude-sonnet-5", "--suite=agentic"]
    )
    st = runstate.read()
    assert st["pid"] == os.getpid()
    assert st["status"] == "running"
    assert st["models"] == ["claude-sonnet-5"]
    assert st["argv"] == ["claude-sonnet-5", "--suite=agentic"]
    assert st["started"].endswith("Z")
    assert st["current"] is None
    assert st["completed"] == []


def test_begin_writes_to_env_path(tmp_path):
    runstate.begin(models=["m"], argv=[])
    assert json.loads((tmp_path / "run.json").read_text())["pid"] == os.getpid()


def test_set_model_and_suite_track_the_current_position():
    runstate.begin(models=["a", "b"], argv=[])
    runstate.set_model("b", 2, 2)
    runstate.set_suite("agentic")
    cur = runstate.read()["current"]
    assert cur["model"] == "b"
    assert cur["index"] == 2
    assert cur["total"] == 2
    assert cur["suite"] == "agentic"
    assert cur["suite_started"].endswith("Z")


def test_set_model_clears_the_previous_suite():
    """A new model has not started a suite yet — carrying the old one forward would name
    the wrong suite for tens of minutes."""
    runstate.begin(models=["a", "b"], argv=[])
    runstate.set_model("a", 1, 2)
    runstate.set_suite("agentic")
    runstate.set_model("b", 2, 2)
    assert runstate.read()["current"]["suite"] is None


def test_finish_model_appends_and_clears_current():
    runstate.begin(models=["a"], argv=[])
    runstate.set_model("a", 1, 1)
    runstate.set_suite("agentic")
    runstate.finish_model("a", "baseline")
    st = runstate.read()
    assert st["current"] is None
    assert len(st["completed"]) == 1
    assert st["completed"][0]["model"] == "a"
    assert st["completed"][0]["verdict"] == "baseline"
    assert st["completed"][0]["error"] is None
    assert st["completed"][0]["finished"].endswith("Z")


def test_finish_model_records_an_error():
    runstate.begin(models=["a"], argv=[])
    runstate.finish_model("a", None, error="serve failed")
    assert runstate.read()["completed"][0]["error"] == "serve failed"


def test_end_records_terminal_status_and_exit_code():
    runstate.begin(models=["a"], argv=[])
    runstate.end("done", 0)
    st = runstate.read()
    assert st["status"] == "done"
    assert st["exit_code"] == 0
    assert st["finished"].endswith("Z")


def test_end_is_idempotent_so_atexit_cannot_overwrite_the_real_status():
    """main() ends the run explicitly; the atexit backstop must not then relabel a clean
    'failed' as 'interrupted'."""
    runstate.begin(models=["a"], argv=[])
    runstate.end("failed", 1)
    runstate.end("interrupted", None)
    st = runstate.read()
    assert st["status"] == "failed"
    assert st["exit_code"] == 1


def test_heartbeat_advances_on_every_update():
    runstate.begin(models=["a"], argv=[])
    first = runstate.read()["heartbeat"]
    runstate.set_model("a", 1, 1)
    assert runstate.read()["heartbeat"] >= first


def test_is_alive_true_for_a_running_record_with_a_live_pid():
    runstate.begin(models=["a"], argv=[])
    assert runstate.is_alive(runstate.read()) is True


def test_is_alive_false_once_ended():
    runstate.begin(models=["a"], argv=[])
    runstate.end("done", 0)
    assert runstate.is_alive(runstate.read()) is False


def test_is_alive_false_when_the_pid_is_gone():
    """The SIGKILL case: status still says 'running' because nothing got to write 'done'.
    The PID is the authority, and this is exactly what a command-line match got wrong."""
    runstate.begin(models=["a"], argv=[])
    st = runstate.read()
    st["pid"] = _dead_pid()
    assert runstate.is_alive(st) is False


def test_is_alive_false_for_none_and_missing_pid():
    assert runstate.is_alive(None) is False
    assert runstate.is_alive({"status": "running"}) is False


def test_describe_adds_liveness_and_elapsed():
    runstate.begin(models=["a"], argv=[], label="noise-floor r1/3")
    runstate.set_model("a", 1, 1)
    runstate.set_suite("agentic")
    d = runstate.describe(runstate.read())
    assert d["alive"] is True
    assert d["label"] == "noise-floor r1/3"
    assert d["elapsed_s"] >= 0
    assert d["current"]["suite_elapsed_s"] >= 0


def test_describe_of_none_is_none():
    assert runstate.describe(None) is None


def test_write_is_atomic_leaving_no_partial_file(tmp_path):
    """Rendered via a temp file + rename, so a monitor polling mid-write never reads
    half a document."""
    runstate.begin(models=["a"], argv=[])
    runstate.set_model("a", 1, 1)
    runstate.set_suite("agentic")
    strays = [p.name for p in tmp_path.iterdir() if p.name != "run.json"]
    assert strays == []
    assert (
        json.loads((tmp_path / "run.json").read_text())["current"]["suite"] == "agentic"
    )
