"""What the eval runner is doing right now — written by the runner, read by the monitor.

Sprint 15 produced the failure this exists to prevent: a watcher ran
`pgrep -f "kvllm.evalrun <model>"` from a shell whose own command line contained that
string, matched itself, and reported a finished eval as still running for ~36 minutes.
Ken noticed only because the GPU had been idle on the dashboard.

The fix is not a smarter watcher. The runner already knows the model, the suite, the start
time and the exit status, so it writes them down; anything watching reads the file instead
of inferring from the outside. Two rules follow, and both are tested:

- **Liveness keys on the recorded PID**, never a command-line pattern match. A record can
  say "running" and still be dead — that is the SIGKILL case, and `is_alive` catches it.
- **Every setter is a no-op until `begin()`**, so the runner can instrument unconditionally
  and a library caller that never begins a run leaves no file behind.

Writes are atomic (temp file + rename): a monitor polling mid-write never sees half a
document. The file lives inside the gitignored `eval-logs/` as a dotfile so Inspect's log
scanner does not pick it up; `KVLLM_RUN_STATE` overrides the path.
"""

from __future__ import annotations

import atexit
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_PATH = REPO / "eval-logs" / ".run-state.json"

_path: Path | None = None  # None = not recording; every setter is a no-op
_state: dict = {}
_atexit_registered = False


def state_path() -> Path:
    """Where the run-state lives. `KVLLM_RUN_STATE` wins, so tests and one-off runs can
    point somewhere else without touching the real one."""
    override = os.environ.get("KVLLM_RUN_STATE")
    return Path(override) if override else DEFAULT_PATH


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _flush() -> None:
    """Render the state atomically — temp file in the same directory, then rename."""
    if _path is None:
        return
    _state["heartbeat"] = _now()
    _path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=_path.parent, prefix=".run-state.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(_state, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, _path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# --- writing (the runner's side) -----------------------------------------------------


def begin(
    *, models: list[str], argv: list[str], label: str | None = None
) -> Path | None:
    """Start recording. Returns the path written, or None if recording is disabled.

    Registers an atexit backstop that marks an unfinished run `interrupted` — a run that
    dies without reaching `end()` should not leave a record claiming to be running.
    """
    global _path, _state, _atexit_registered
    _path = state_path()
    _state = {
        "pid": os.getpid(),
        "label": label,
        "started": _now(),
        "status": "running",
        "models": list(models),
        "argv": list(argv),
        "current": None,
        "completed": [],
        "exit_code": None,
        "finished": None,
    }
    if not _atexit_registered:
        atexit.register(_on_exit)
        _atexit_registered = True
    _flush()
    return _path


def set_model(key: str, index: int, total: int) -> None:
    """Now evaluating `key` — the index-th of `total`. Clears the suite: a model that has
    just started has not entered a suite yet, and carrying the previous one forward would
    name the wrong suite for tens of minutes."""
    if _path is None:
        return
    _state["current"] = {
        "model": key,
        "index": index,
        "total": total,
        "started": _now(),
        "suite": None,
        "suite_started": None,
    }
    _flush()


def set_suite(cap: str) -> None:
    """Now running suite `cap` for the current model."""
    if _path is None or not _state.get("current"):
        return
    _state["current"]["suite"] = cap
    _state["current"]["suite_started"] = _now()
    _flush()


def finish_model(key: str, verdict: str | None, error: str | None = None) -> None:
    if _path is None:
        return
    _state["completed"].append(
        {
            "model": key,
            "verdict": verdict,
            "error": error,
            "finished": _now(),
        }
    )
    _state["current"] = None
    _flush()


def end(status: str, exit_code: int | None = None) -> None:
    """Mark the run terminal: `done`, `failed` or `interrupted`.

    Idempotent by design — `main()` ends the run explicitly and the atexit backstop fires
    afterwards; the first terminal status is the true one and must survive.
    """
    if _path is None or _state.get("status") != "running":
        return
    _state["status"] = status
    _state["exit_code"] = exit_code
    _state["finished"] = _now()
    _flush()


def _on_exit() -> None:
    end("interrupted")


def reset() -> None:
    """Forget the in-process recording (does not delete the file). Tests use this."""
    global _path, _state
    _path = None
    _state = {}


# --- reading (the monitor's side) ----------------------------------------------------


def read(path: Path | None = None) -> dict | None:
    """The last state the runner wrote, or None if there is none (or it is unreadable —
    a half-written or hand-mangled file is 'nothing to report', never an exception in the
    monitor's request path)."""
    p = path or state_path()
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def is_alive(state: dict | None) -> bool:
    """Is the run this record describes still going?

    `status == "running"` alone is not enough: a SIGKILLed runner never got to write a
    terminal status, so the recorded PID is the authority. Signal 0 asks the kernel whether
    the process exists without touching it.
    """
    if not state or state.get("status") != "running":
        return False
    pid = state.get("pid")
    if not isinstance(pid, int):
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else — alive is still the honest answer
    except OSError:
        return False
    return True


def _elapsed_s(since: str | None, until: str | None = None) -> float | None:
    if not since:
        return None
    try:
        start = datetime.fromisoformat(since)
        stop = datetime.fromisoformat(until) if until else datetime.now(UTC)
    except ValueError:
        return None
    return round((stop - start).total_seconds(), 1)


def describe(state: dict | None) -> dict | None:
    """The state plus what a viewer wants and shouldn't recompute: liveness, and elapsed
    seconds for the run and the suite in flight. Elapsed is measured to `finished` once the
    run is over, so a finished run stops ageing."""
    if not state:
        return None
    out = dict(state)
    alive = is_alive(state)
    out["alive"] = alive
    # A run that is over must stop ageing, and that applies to `current` too — it names the
    # model and suite the runner exited during, so measuring it against wall-clock reports
    # 95 minutes for an 8m36s run. `finished` is the exit moment; a runner that was killed
    # never wrote one, so its last heartbeat is the last instant it was known to be alive.
    stop = None if alive else (state.get("finished") or state.get("heartbeat"))
    out["elapsed_s"] = _elapsed_s(state.get("started"), stop)
    if out.get("current"):
        cur = dict(out["current"])
        cur["elapsed_s"] = _elapsed_s(cur.get("started"), stop)
        cur["suite_elapsed_s"] = _elapsed_s(cur.get("suite_started"), stop)
        out["current"] = cur
    return out
