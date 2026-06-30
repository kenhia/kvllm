"""Model registry — load `models.toml`, resolve a key, and serve it with vLLM.

CLI:
    uv run python -m kvllm.registry list
    uv run python -m kvllm.registry show <key>
    uv run python -m kvllm.registry serve <key>   # execs `vllm serve ...`

`serve` builds the vLLM argv from the registry entry and `os.execvp`s into it, so signals
(Ctrl-C, systemd SIGTERM) pass straight through to vLLM. Serve-time knobs that aren't model
properties — port and GPU memory fraction — come from the environment (KVLLM_PORT,
KVLLM_GPU_UTIL), matching the justfile defaults.
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys
import tomllib
from pathlib import Path

DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "models.toml"

# Knobs that are deployment choices, not model properties.
DEFAULT_PORT = os.environ.get("KVLLM_PORT", "8000")
DEFAULT_GPU_UTIL = os.environ.get("KVLLM_GPU_UTIL", "0.90")


def load_registry(path: Path | None = None) -> dict[str, dict]:
    """Load and parse the TOML model registry → {key: entry}."""
    path = path or DEFAULT_REGISTRY
    if not path.is_file():
        sys.exit(f"error: registry not found: {path}")
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"error: invalid TOML in {path}: {e}")
    models = data.get("models")
    if not models:
        sys.exit(f"error: no [models.<key>] entries in {path}")
    for key, entry in models.items():
        if "hf_repo" not in entry:
            sys.exit(f"error: model '{key}' is missing required field 'hf_repo'")
    return models


def get_model(key: str, registry: dict[str, dict] | None = None) -> dict:
    """Look up one model by key, with a did-you-mean on miss."""
    registry = registry if registry is not None else load_registry()
    if key not in registry:
        near = difflib.get_close_matches(key, registry, n=3)
        hint = f" Did you mean: {', '.join(near)}?" if near else ""
        sys.exit(f"error: unknown model '{key}'.{hint} (try: list)")
    return registry[key]


def build_serve_argv(
    key: str,
    entry: dict,
    *,
    port: str = DEFAULT_PORT,
    gpu_util: str = DEFAULT_GPU_UTIL,
) -> list[str]:
    """Resolve a registry entry into a `vllm serve ...` argv."""
    argv = [
        "vllm",
        "serve",
        entry["hf_repo"],
        # The registry key is the model id the client passes as model=.
        "--served-model-name",
        key,
        "--port",
        str(port),
        "--gpu-memory-utilization",
        str(gpu_util),
    ]
    if "max_model_len" in entry:
        argv += ["--max-model-len", str(entry["max_model_len"])]
    if entry.get("tool_parser"):
        argv += [
            "--enable-auto-tool-choice",
            "--tool-call-parser",
            entry["tool_parser"],
        ]
    if entry.get("reasoning_parser"):
        argv += ["--reasoning-parser", entry["reasoning_parser"]]
    if entry.get("quantization"):
        argv += ["--quantization", entry["quantization"]]
    if entry.get("trust_remote_code"):
        argv += ["--trust-remote-code"]
    return argv


def _cmd_list(args: argparse.Namespace) -> int:
    registry = load_registry()
    show_all = getattr(args, "all", False)
    width = max(len(k) for k in registry)
    hidden = 0
    for key, entry in registry.items():
        verdict = entry.get("eval_verdict")
        # Models the eval proved don't run/fit here are hidden unless --all.
        if verdict == "skip" and not show_all:
            hidden += 1
            continue
        caps = ",".join(entry.get("capabilities", []))
        vram = entry.get("est_vram_gb")
        vram_s = f"~{vram}GB" if vram is not None else "?"
        flags = []
        if verdict:
            flags.append(
                {
                    "worth trying": "✓worth-trying",
                    "has issues": "⚠has-issues",
                    "skip": "✗skip",
                }.get(verdict, verdict)
            )
        elif entry.get("tested"):
            flags.append("tested")
        if entry.get("gated"):
            flags.append("gated")
        if entry.get("quantization"):
            flags.append(entry["quantization"])
        flag_s = f" [{', '.join(flags)}]" if flags else ""
        print(f"{key:<{width}}  {vram_s:>7}  {caps}{flag_s}")
    if hidden:
        print(
            f"\n({hidden} hidden — eval verdict 'skip' (won't fit/run on kai). `list --all` to show.)"
        )
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    entry = get_model(args.key)
    print(f"# {args.key}")
    for field in (
        "hf_repo",
        "tool_parser",
        "reasoning_parser",
        "quantization",
        "trust_remote_code",
        "max_model_len",
        "gated",
        "est_vram_gb",
        "capabilities",
        "tested",
        "eval_verdict",
        "eval_date",
        "eval_notes",
        "notes",
    ):
        if field in entry:
            print(f"{field:<16} {entry[field]}")
    print("\n# serve command:")
    print("  " + " ".join(build_serve_argv(args.key, entry)))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    entry = get_model(args.key)
    argv = build_serve_argv(args.key, entry)
    print("+ " + " ".join(argv), file=sys.stderr)
    os.execvp(argv[0], argv)  # replaces this process; only returns on failure
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kvllm.registry", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_list = sub.add_parser("list", help="list registered models (hides eval-skipped)")
    p_list.add_argument(
        "-a", "--all", action="store_true", help="include models the eval skipped"
    )
    p_list.set_defaults(func=_cmd_list)
    p_show = sub.add_parser("show", help="show one model's config + serve command")
    p_show.add_argument("key")
    p_show.set_defaults(func=_cmd_show)
    p_serve = sub.add_parser("serve", help="serve a model with vLLM (execs vllm serve)")
    p_serve.add_argument("key")
    p_serve.set_defaults(func=_cmd_serve)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
