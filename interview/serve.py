"""Serve a registry model with overrides, for the envelope study.

    uv run python -m interview.serve start <key> [--tag T] [--max-model-len N]
        [--kv-cache-dtype fp8|auto] [--spec '{"method":"mtp","num_speculative_tokens":3}' | --no-spec]
        [--chat-kwargs '{"enable_thinking":true}'] [--gpu-util 0.90] [--port 8000] [--no-wait]
    uv run python -m interview.serve stop
    uv run python -m interview.serve status

`start` applies the overrides to the registry entry, builds the exact `vllm serve` argv the
registry would, launches it in its own session, waits for /v1/models, and prints (and
records to model-research/ra-interview/envelope/serves.jsonl) what the engine reported:
KV pool, KV tokens, concurrency at max_model_len, weights, cold start, VRAM. A serve that
fails to start is recorded too, with vLLM's own reason — a ceiling is a measurement.

Does NOT touch kvllm.service. Stop it first (the sprint does), restore it after.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

from kvllm import evalctl
from kvllm.registry import build_serve_argv, get_model

REPO = Path(__file__).resolve().parent.parent
LOG_DIR = REPO / "eval-logs" / "serve"
STATE = REPO / ".scratch" / "interview-serve.json"
RECORD = REPO / "model-research" / "ra-interview" / "envelope" / "serves.jsonl"


def apply_overrides(
    entry: dict,
    *,
    max_model_len: int | None = None,
    kv_cache_dtype: str | None = None,
    speculative: dict | None = None,
    no_spec: bool = False,
    chat_kwargs: dict | None = None,
    extra: list[str] | None = None,
) -> dict:
    """Registry entry + overrides → the entry to serve. Pure; the tests cover it.

    `kv_cache_dtype="auto"` clears the field (vLLM's default); `no_spec` drops any
    draft head; `chat_kwargs` merges over the entry's own defaults."""
    e = dict(entry)
    if max_model_len:
        e["max_model_len"] = int(max_model_len)
    if kv_cache_dtype:
        if kv_cache_dtype == "auto":
            e.pop("kv_cache_dtype", None)
        else:
            e["kv_cache_dtype"] = kv_cache_dtype
    if speculative is not None:
        e["speculative_config"] = speculative
    if no_spec:
        e.pop("speculative_config", None)
    if chat_kwargs is not None:
        e["chat_template_kwargs"] = {**e.get("chat_template_kwargs", {}), **chat_kwargs}
    if extra:
        e["extra_args"] = list(e.get("extra_args", [])) + list(extra)
    return e


_KV_PATTERNS = {
    "kv_tokens": r"GPU KV cache size:\s*([\d,]+)\s*tokens",
    "concurrency_x": r"Maximum concurrency for\s*[\d,]+\s*tokens per request:\s*([\d.]+)x",
    "kv_pool_gib": r"Available KV cache memory:\s*([\d.]+)\s*GiB",
    "weights_gib": r"model weights take\s*([\d.]+)\s*GiB",
    "activation_peak_gib": r"PyTorch activation peak memory takes\s*([\d.]+)\s*GiB",
    "non_torch_gib": r"non_torch_memory takes\s*([\d.]+)\s*GiB",
}


def parse_kv_stats(text: str) -> dict:
    """Pull the engine's own memory/KV report out of a serve log (last match wins)."""
    out: dict = {}
    for k, pat in _KV_PATTERNS.items():
        hits = re.findall(pat, text)
        if hits:
            v = hits[-1].replace(",", "")
            out[k] = int(v) if k == "kv_tokens" else float(v)
    if "kv_tokens" in out and "kv_pool_gib" in out and out["kv_tokens"]:
        out["kib_per_token"] = round(
            out["kv_pool_gib"] * 1024 * 1024 / out["kv_tokens"], 1
        )
    return out


def _record(row: dict) -> None:
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    with RECORD.open("a") as f:
        f.write(json.dumps(row) + "\n")


def _load_state() -> dict | None:
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return None


def cmd_start(args: argparse.Namespace) -> int:
    if _load_state() and evalctl.wait_port_healthy(args.port, timeout_s=1):
        sys.exit("error: something already answers on that port — `stop` it first")
    entry = apply_overrides(
        get_model(args.key),
        max_model_len=args.max_model_len,
        kv_cache_dtype=args.kv_cache_dtype,
        speculative=json.loads(args.spec) if args.spec else None,
        no_spec=args.no_spec,
        chat_kwargs=json.loads(args.chat_kwargs) if args.chat_kwargs else None,
        extra=args.extra,
    )
    argv = build_serve_argv(
        args.key, entry, port=str(args.port), gpu_util=str(args.gpu_util)
    )
    tag = args.tag or time.strftime("%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"interview-{args.key}-{tag}.log"
    evalctl.wait_gpu_drained()
    print(f"[serve] {' '.join(argv)}")
    print(f"[serve] log: {log_path}")
    log = open(log_path, "w")
    t0 = time.time()
    proc = subprocess.Popen(
        argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(
        json.dumps(
            {
                "pid": proc.pid,
                "key": args.key,
                "tag": tag,
                "port": args.port,
                "log": str(log_path),
                "argv": argv,
                "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
    )
    row = {
        "date": time.strftime("%Y-%m-%d"),
        "key": args.key,
        "tag": tag,
        "vllm": None,
        "max_model_len": entry.get("max_model_len"),
        "kv_cache_dtype": entry.get("kv_cache_dtype"),
        "speculative_config": entry.get("speculative_config"),
        "chat_template_kwargs": entry.get("chat_template_kwargs"),
        "gpu_util": args.gpu_util,
    }
    if args.no_wait:
        print(json.dumps(row | {"pid": proc.pid, "waited": False}))
        return 0
    cold = evalctl.wait_healthy(proc, args.port)
    text = log_path.read_text()
    row |= parse_kv_stats(text)
    m = re.search(r"V1 LLM engine \(v([\d.a-z]+)\)", text)
    row["vllm"] = m.group(1) if m else None
    if cold is None:
        row |= {"served": False, "error": evalctl.serve_error(log_path)}
        print(json.dumps(row, indent=1))
        _record(row)
        cmd_stop(args)
        return 1
    row |= {
        "served": True,
        "cold_s": round(cold, 1),
        "gpu_used_mib": evalctl.gpu_used_mib(),
        "wall_s": round(time.time() - t0, 1),
    }
    print(json.dumps(row, indent=1))
    _record(row)
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    st = _load_state()
    if not st:
        print("[serve] nothing recorded as running")
        return 0
    pid = st["pid"]
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except ProcessLookupError:
        print(f"[serve] pid {pid} already gone")
    else:
        for _ in range(60):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(1)
        else:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
    STATE.unlink(missing_ok=True)
    evalctl.wait_gpu_drained()
    print(
        f"[serve] stopped {st['key']} ({st['tag']}); GPU {evalctl.gpu_used_mib()} MiB"
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    st = _load_state()
    if not st:
        print("no interview serve recorded")
    else:
        alive = True
        try:
            os.kill(st["pid"], 0)
        except ProcessLookupError:
            alive = False
        healthy = evalctl.wait_port_healthy(st["port"], timeout_s=1)
        print(json.dumps(st | {"alive": alive, "healthy": healthy}, indent=1))
    print(
        f"GPU {evalctl.gpu_used_mib()} MiB; kvllm.service active={evalctl.service_active()}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="interview.serve", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("key")
    s.add_argument("--tag", default=None)
    s.add_argument("--max-model-len", type=int, default=None)
    s.add_argument("--kv-cache-dtype", default=None, help="fp8, or auto to clear")
    s.add_argument("--spec", default=None, help="JSON --speculative-config")
    s.add_argument("--no-spec", action="store_true", help="drop any draft head")
    s.add_argument("--chat-kwargs", default=None, help="JSON merged over the entry's")
    s.add_argument("--extra", nargs="*", default=None, help="extra vllm serve args")
    s.add_argument("--gpu-util", default=os.environ.get("KVLLM_GPU_UTIL", "0.90"))
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--no-wait", action="store_true")
    s.set_defaults(func=cmd_start)
    t = sub.add_parser("stop")
    t.add_argument("--port", type=int, default=8000)
    t.set_defaults(func=cmd_stop)
    u = sub.add_parser("status")
    u.set_defaults(func=cmd_status)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
