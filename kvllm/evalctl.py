"""Eval controller — make a registry model servable and measure the operational gate.

The controller half of the Sprint 7 runner, split out per fable-planning/02: it owns
"stop kvllm.service → serve model K standalone → health-wait → restore" and the operational
measurements (cold start, VRAM, TTFT, decode tok/s). It knows nothing about suites or scoring —
kvllm.evalrun composes this with the Inspect tasks in evals/.

Speed is measured properly now (v1 gate was one 128-token sample including prefill): streamed
completions, TTFT recorded separately, decode tok/s = (tokens-1)/(t_last - t_first), median of 3.
"""

from __future__ import annotations

import os
import signal
import statistics
import subprocess
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from kvllm.registry import build_serve_argv

SERVICE = "kvllm"
HEALTH_TIMEOUT_S = 900

REPO = Path(__file__).resolve().parent.parent
SERVE_LOG_DIR = REPO / "eval-logs" / "serve"


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", *args], capture_output=True, text=True
    )


def service_active() -> bool:
    return _systemctl("is-active", SERVICE).stdout.strip() == "active"


def gpu_used_mib() -> int | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        return int(out.strip().split("\n")[0])
    except Exception:
        return None


def wait_healthy(
    proc: subprocess.Popen, port: int, timeout_s: int = HEALTH_TIMEOUT_S
) -> float | None:
    """Block until /v1/models answers. Returns seconds-to-ready, or None if the serve
    process dies (fast fail) or the timeout passes."""
    url = f"http://localhost:{port}/v1/models"
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if proc.poll() is not None:  # serve process exited (e.g. OOM)
            return None
        try:
            with urllib.request.urlopen(url, timeout=2):
                return time.time() - t0
        except Exception:
            time.sleep(2)
    return None


# Patterns whose last match in the serve log best explains a failed start.
_ERROR_PATTERNS = (
    "OutOfMemoryError",
    "out of memory",
    "No available memory for the cache",
    "ValueError",
    "RuntimeError",
    "Error",
)


# Wrapper/summary lines that re-raise someone else's error — never the root cause.
_ERROR_WRAPPERS = ("See root cause above", "initialization failed")


def _root_cause(lines: list[str], pat: str) -> str | None:
    """Best 'Pattern: message' line: skip re-raise wrappers and bare `raise X(` traceback
    source lines, prefer exception-style lines over mere mentions. (qwen3-8b-fp8's DeepGEMM
    assert was masked first by the APIServer summary, then by its `raise RuntimeError(`.)"""
    hits = [
        ln
        for ln in lines
        if pat in ln
        and not any(w in ln for w in _ERROR_WRAPPERS)
        and not ln.split("] ", 1)[-1].strip().startswith("raise ")
    ]
    exception_style = [ln for ln in hits if f"{pat}:" in ln or f"{pat} " in ln]
    best = exception_style or hits
    return best[-1] if best else None


def serve_error(log_path: Path) -> str:
    """Pull a concise failure reason out of the serve log (best-effort)."""
    try:
        lines = log_path.read_text().splitlines()
    except OSError:
        return ""
    for pat in _ERROR_PATTERNS:
        line = _root_cause(lines, pat)
        if line:
            # strip the vLLM "(EngineCore pid=...) ERROR ... [core.py:NN] " prefix
            return line.split("] ", 1)[-1].strip()[:280]
    return ""


def stop_service() -> None:
    print(f"[orchestrate] stopping {SERVICE}.service to free the GPU")
    _systemctl("stop", SERVICE)
    time.sleep(2)


def start_service() -> None:
    print(f"[orchestrate] restoring {SERVICE}.service")
    _systemctl("start", SERVICE)


def wait_gpu_drained(threshold_mib: int = 2000, timeout_s: int = 90) -> bool:
    """Block until GPU memory drops below threshold. Starting a new vLLM while the killed
    one's memory is still being released can wedge the GPU — the 2026-07-02 incident on kai
    ended in a hung GSP (Xid 119) and a reboot. Never skip this between serves."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        used = gpu_used_mib()
        if used is None or used < threshold_mib:
            return True
        time.sleep(2)
    print(
        f"[orchestrate] WARNING: GPU still holds {gpu_used_mib()} MiB after {timeout_s}s"
    )
    return False


def wait_port_healthy(port: int, timeout_s: int = 300) -> bool:
    """Block until /v1/models on `port` answers (no process handle — e.g. the systemd
    service). Fire-and-forget restores are how tonight's hang went unnoticed for an hour."""
    url = f"http://localhost:{port}/v1/models"
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(3)
    return False


@contextmanager
def serving(key: str, entry: dict, *, port: int):
    """Serve `key` standalone for the duration of the block. Yields (proc, serve_log_path);
    the caller decides health. Does NOT touch kvllm.service — the batch runner manages the
    service once per sweep (stop before the first model, restore + health-check after the
    last), so models swap with the minimum number of GPU teardown/startup cycles."""
    wait_gpu_drained()  # never start a serve while the previous one's VRAM is draining
    SERVE_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = SERVE_LOG_DIR / f"{key.replace('/', '_')}.log"
    argv = build_serve_argv(key, entry, port=str(port))
    print(f"[serve] {' '.join(argv)}")
    log = open(log_path, "w")
    proc = subprocess.Popen(
        argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
    try:
        yield proc, log_path
    finally:
        print("[serve] stopping model under test")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=60)
        except Exception:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
        log.close()
        wait_gpu_drained()


def context_probe(base_url: str, model: str, max_model_len: int) -> bool | None:
    """Deferred gate check from fable-planning/03 §S0: a prompt at ~75% of the served context
    window must complete without error (catches KV-cache/rope/serving bugs that only bite under
    context pressure). Returns True/False, or None if the probe couldn't run."""
    from openai import OpenAI

    # ~75% of the window in tokens; "lorem N." words ≈ 3-4 tokens each is too fuzzy — use a
    # repeated short word (≈1 token + space) and leave generous headroom for chat template.
    target_tokens = int(max_model_len * 0.75)
    filler = "data " * max(target_tokens - 200, 100)
    client = OpenAI(base_url=base_url, api_key="EMPTY", timeout=300)
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f"{filler}\nReply with exactly the word: ok",
                }
            ],
            max_tokens=8,
            temperature=0.0,
        )
        return bool(r.choices and r.choices[0].message is not None)
    except Exception as e:
        msg = str(e).lower()
        # a context-length rejection is a real failure; transport errors are "couldn't run"
        if "context" in msg or "length" in msg or "token" in msg:
            print(f"[gate] context probe FAILED: {str(e)[:160]}")
            return False
        print(f"[gate] context probe couldn't run: {str(e)[:120]}")
        return None


def measure_speed(base_url: str, model: str, runs: int = 3) -> dict:
    """Streamed speed probe: median TTFT and decode tok/s over `runs` completions.
    Returns {} if measurement fails (a gate detail, not a crash)."""
    from openai import (
        OpenAI,  # via vLLM's dependency chain; avoid import at module load
    )

    client = OpenAI(base_url=base_url, api_key="EMPTY")
    ttfts, decodes = [], []
    why = ""
    for _ in range(runs):
        try:
            t0 = time.time()
            c_first = c_last = a_first = a_last = None  # content-bearing vs any chunk
            usage = None
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": "Write a short paragraph about GPUs."}
                ],
                max_tokens=128,
                temperature=0.0,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
                if not chunk.choices:
                    continue
                now = time.time()
                a_last, a_first = now, (a_first or now)
                delta = chunk.choices[0].delta
                # reasoning models stream thinking under a separate delta field whose
                # name has moved between vLLM versions — check the known spellings
                if delta and (
                    delta.content
                    or getattr(delta, "reasoning_content", None)
                    or getattr(delta, "reasoning", None)
                ):
                    c_last, c_first = now, (c_first or now)
            # prefer content-bearing timing; fall back to chunk arrival (first chunk
            # lands at end of prefill, so it is still an honest TTFT)
            first = c_first or a_first
            last = c_last if c_first else a_last
            toks = getattr(usage, "completion_tokens", 0) or 0
            if first and last and last > first and toks > 1:
                ttfts.append(first - t0)
                decodes.append((toks - 1) / (last - first))
            else:
                why = f"chunks={a_first is not None} content={c_first is not None} tokens={toks}"
        except Exception as e:
            why = f"{type(e).__name__}: {e}"
            continue
    if not decodes:
        print(f"[gate] WARNING: speed unmeasured ({why or 'no runs completed'})")
        return {}
    return {
        "ttft_s": round(statistics.median(ttfts), 2),
        "decode_tok_s": round(statistics.median(decodes), 1),
    }
