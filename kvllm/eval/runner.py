"""Eval runner — orchestrate serve→measure→restore and run the capability suites.

    uv run --group eval python -m kvllm.eval <model-key> [--suite tools] [--port 8000] [--no-write]

Orchestration (Ken approved): stop kvllm.service if running, serve the target model standalone,
run the operational gate + the suites matching the model's registry `capabilities`, then restore
the service. Writes a scorecard + updates the leaderboard and models.toml (unless --no-write).
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request

from openai import OpenAI

from kvllm.eval import report
from kvllm.eval.suites import SUITES, score_case
from kvllm.registry import build_serve_argv, load_registry

SERVICE = "kvllm"
TOOL_PASS_THRESHOLD = 0.8
MIN_TOKENS_PER_SEC = 10.0  # below this, a model "works" but is too slow to be practical


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", *args], capture_output=True, text=True
    )


def _service_active() -> bool:
    return _systemctl("is-active", SERVICE).stdout.strip() == "active"


def _gpu_used_mib() -> int | None:
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


def _wait_healthy(
    proc: subprocess.Popen, port: int, timeout_s: int = 900
) -> float | None:
    """Block until /v1/models answers. Returns seconds-to-ready, or None if the serve process
    dies (fast fail) or we hit the timeout."""
    url = f"http://localhost:{port}/v1/models"
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if (
            proc.poll() is not None
        ):  # serve process exited (e.g. OOM) — stop waiting now
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


def _serve_error(log_path: str) -> str:
    """Pull a concise failure reason out of the serve log (best-effort)."""
    try:
        lines = open(log_path).read().splitlines()
    except OSError:
        return ""
    for pat in _ERROR_PATTERNS:
        hits = [ln for ln in lines if pat in ln]
        if hits:
            # strip the vLLM "(EngineCore pid=...) ERROR ... [core.py:NN] " prefix if present
            msg = hits[-1].split("] ", 1)[-1].strip()
            return msg[:280]
    return ""


def _measure_tps(client: OpenAI, model: str) -> float | None:
    try:
        t0 = time.time()
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Write a short paragraph about GPUs."}
            ],
            max_tokens=128,
            temperature=0.0,
        )
        dt = time.time() - t0
        toks = getattr(r.usage, "completion_tokens", 0) or 0
        return round(toks / dt, 1) if dt > 0 else None
    except Exception:
        return None


def _run_suite(client: OpenAI, model: str, cases) -> dict:
    results = []
    for case in cases:
        try:
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": case.prompt}],
                "tools": case.tools,
                "temperature": 0.0,
            }
            if case.tool_choice:
                kwargs["tool_choice"] = case.tool_choice
            resp = client.chat.completions.create(**kwargs)
            msg = resp.choices[0].message
            final_answer = ""
            if case.kind == "multi_turn":  # second turn: feed the tool result back
                calls = list(msg.tool_calls or [])
                if calls:
                    follow = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "user", "content": case.prompt},
                            msg.model_dump(),
                            {
                                "role": "tool",
                                "tool_call_id": calls[0].id,
                                "content": case.tool_result,
                            },
                        ],
                        tools=case.tools,
                        temperature=0.0,
                    )
                    final_answer = follow.choices[0].message.content or ""
            passed, detail = score_case(case, msg, final_answer)
        except Exception as e:  # a case that errors is a fail, not a crash
            passed, detail = False, f"error: {e}"
        results.append({"name": case.name, "passed": passed, "detail": detail})
        print(f"    {'PASS' if passed else 'FAIL'}  {case.name}: {detail}")
    n = len(results)
    passed = sum(r["passed"] for r in results)
    return {
        "passed": passed,
        "total": n,
        "pass_rate": round(passed / n, 2) if n else 0.0,
        "cases": results,
    }


def _verdict(served: bool, suites: dict, tps: float | None = None) -> str:
    if not served:
        return "skip"
    rates = [s["pass_rate"] for s in suites.values()]
    base = (
        "worth trying"
        if (not suites or all(r >= TOOL_PASS_THRESHOLD for r in rates))
        else "has issues"
    )
    # A model that serves + passes but crawls is "has issues" in practice, not "worth trying".
    if base == "worth trying" and tps is not None and tps < MIN_TOKENS_PER_SEC:
        return "has issues"
    return base


def evaluate(model_key: str, *, port: int, only_suite: str | None, today: str) -> dict:
    registry = load_registry()
    if model_key not in registry:
        sys.exit(f"error: unknown model '{model_key}' (try: just models-list)")
    entry = registry[model_key]
    caps = entry.get("capabilities", [])
    to_run = {
        cap: SUITES[cap]
        for cap in caps
        if cap in SUITES and (not only_suite or cap == only_suite)
    }

    prior_active = _service_active()
    if prior_active:
        print(f"[orchestrate] stopping {SERVICE}.service to free the GPU")
        _systemctl("stop", SERVICE)
        time.sleep(2)

    argv = build_serve_argv(model_key, entry, port=str(port))
    print(f"[serve] {' '.join(argv)}")
    log = open(f"/tmp/kvllm-eval-{model_key}.log", "w")
    proc = subprocess.Popen(
        argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )

    scorecard = {
        "model": model_key,
        "date": today,
        "hf_repo": entry.get("hf_repo"),
        "operational": {},
        "suites": {},
        "notes": "",
    }
    try:
        cold = _wait_healthy(proc, port)
        served = cold is not None
        scorecard["operational"] = {
            "served": served,
            "cold_start_s": round(cold, 1) if cold else None,
            "gpu_used_mib": _gpu_used_mib() if served else None,
        }
        if not served:
            reason = _serve_error(log.name)
            scorecard["operational"]["error"] = (
                reason or f"did not become healthy; see {log.name}"
            )
            scorecard["notes"] = reason
            print(f"[serve] FAILED to serve — {reason or 'see ' + log.name}")
        else:
            print(
                f"[serve] ready in {cold:.0f}s, GPU {scorecard['operational']['gpu_used_mib']} MiB"
            )
            client = OpenAI(base_url=f"http://localhost:{port}/v1", api_key="EMPTY")
            tps = _measure_tps(client, model_key)
            scorecard["operational"]["tokens_per_sec"] = tps
            if tps is not None and tps < MIN_TOKENS_PER_SEC:
                scorecard["notes"] = f"works but impractically slow on kai: {tps} tok/s"
            for cap, cases in to_run.items():
                print(f"[suite] {cap} ({len(cases)} cases)")
                scorecard["suites"][cap] = _run_suite(client, model_key, cases)
    finally:
        print("[serve] stopping model under test")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=30)
        except Exception:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
        log.close()
        if prior_active:
            print(f"[orchestrate] restoring {SERVICE}.service")
            _systemctl("start", SERVICE)

    scorecard["verdict"] = _verdict(
        scorecard["operational"].get("served", False),
        scorecard["suites"],
        scorecard["operational"].get("tokens_per_sec"),
    )
    return scorecard


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kvllm.eval", description=__doc__)
    p.add_argument("model_key")
    p.add_argument(
        "--suite", default=None, help="run only this capability suite (e.g. tools)"
    )
    p.add_argument("--port", type=int, default=8000)
    p.add_argument(
        "--today",
        default=os.environ.get("KVLLM_EVAL_DATE", ""),
        help="YYYY-MM-DD stamp for the scorecard (defaults to env or 'undated')",
    )
    p.add_argument(
        "--no-write",
        action="store_true",
        help="don't write scorecard/leaderboard/registry",
    )
    args = p.parse_args(argv)

    today = args.today or "undated"
    card = evaluate(args.model_key, port=args.port, only_suite=args.suite, today=today)
    print(f"\n=== {card['model']}: {card['verdict'].upper()} ===")
    for cap, s in card["suites"].items():
        print(f"  {cap}: {s['passed']}/{s['total']} ({s['pass_rate']:.0%})")

    if not args.no_write:
        paths = report.write_all(card)
        print("\nwrote:", ", ".join(str(p) for p in paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
