"""Batch eval runner — serve→gate→suites→score for one, several, or all registry models.

    uv run --group eval python -m kvllm.evalrun <key> [<key> ...]   # specific models
    uv run --group eval python -m kvllm.evalrun --all               # sweep the registry
      [--suite tools] [--force] [--retry-skips] [--no-write] [--port 8000]
      [--endpoint URL [--model-name NAME]]                          # eval a served /v1 directly

Models run serially (vLLM = one model per GPU); everything inside a model runs through
Inspect's eval_set, which retries and resumes via the per-model log dir (eval-logs/<key>/<date>).
The model loop resumes too: models whose latest scorecard already covers every requested suite
at its current version are skipped (--force reruns; gate-failed 'skip' models need --retry-skips).

--endpoint skips serve orchestration entirely (no service stop, no cold-start/VRAM numbers) —
for evaluating whatever is already serving, on this box or another.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import date
from pathlib import Path

from kvllm import evalctl, score
from kvllm.registry import load_registry

REPO = Path(__file__).resolve().parent.parent
LOG_ROOT = REPO / "eval-logs"


def _suites():
    """Capability tag → (task factory, version). Imported lazily to keep inspect off the
    CLI-arg-error path. Extend as suites land (fable-planning/03)."""
    from evals.coding import VERSION as CODING_VERSION
    from evals.coding import coding
    from evals.tools import VERSION as TOOLS_VERSION
    from evals.tools import tools

    return {
        "tools": (tools, TOOLS_VERSION),
        "code": (coding, CODING_VERSION),
    }


def _suites_for(entry: dict, only: str | None, suites: dict) -> dict:
    caps = entry.get("capabilities", [])
    return {
        cap: suites[cap] for cap in caps if cap in suites and (not only or cap == only)
    }


def _run_suites(model_name: str, base_url: str, to_run: dict, log_dir: Path) -> dict:
    """Run the Inspect tasks against the served model; return scorecard suite dicts."""
    from inspect_ai import eval_set

    os.environ["KVLLM_BASE_URL"] = base_url
    os.environ.setdefault("KVLLM_API_KEY", "EMPTY")
    model = f"openai-api/kvllm/{model_name}"

    results: dict[str, dict] = {}
    tasks = [factory() for factory, _ in to_run.values()]
    print(f"[suites] {', '.join(to_run)} via inspect eval_set → {log_dir}")
    success, logs = eval_set(tasks=tasks, model=model, log_dir=str(log_dir))
    by_task = {log.eval.task: log for log in logs}
    for cap, (_, version) in to_run.items():
        log = by_task.get(cap)
        if log is None:
            results[cap] = {
                "version": version,
                "passed": 0,
                "total": 0,
                "pass_rate": 0.0,
                "cases": [],
                "error": "no inspect log produced",
            }
            continue
        results[cap] = score.suite_from_log(log.location, version)
        s = results[cap]
        print(f"[suite] {cap}: {s['passed']}/{s['total']} ({s['pass_rate']:.0%})")
        for c in s["cases"]:
            print(
                f"    {'PASS' if c['passed'] else 'FAIL'}  {c['name']}: {c['detail']}"
            )
    return results


def evaluate(
    key: str,
    entry: dict,
    *,
    port: int,
    only_suite: str | None,
    today: str,
    endpoint: str | None,
    model_name: str | None,
    force: bool = False,
) -> dict:
    suites = _suites()
    to_run = _suites_for(entry, only_suite, suites)
    served_name = model_name or key
    log_dir = LOG_ROOT / key.replace("/", "_") / today
    if force and log_dir.exists():
        # eval_set resumes from completed logs in log_dir — a --force rerun must actually
        # re-execute the suites, not replay this morning's cached results.
        shutil.rmtree(log_dir)

    card: dict = {
        "schema": 2,
        "model": key,
        "date": today,
        "hf_repo": entry.get("hf_repo"),
        "operational": {},
        "suites": {},
        "notes": "",
    }

    if endpoint:
        card["operational"]["served"] = True
        card["operational"] |= evalctl.measure_speed(endpoint, served_name)
        card["suites"] = _run_suites(served_name, endpoint, to_run, log_dir)
    else:
        with evalctl.serving(key, entry, port=port) as (proc, serve_log):
            cold = evalctl.wait_healthy(proc, port)
            served = cold is not None
            card["operational"] = {
                "served": served,
                "cold_start_s": round(cold, 1) if cold else None,
                "gpu_used_mib": evalctl.gpu_used_mib() if served else None,
            }
            if not served:
                reason = evalctl.serve_error(serve_log)
                card["operational"]["error"] = (
                    reason or f"did not become healthy; see {serve_log}"
                )
                card["notes"] = reason
                print(f"[serve] FAILED to serve — {reason or 'see ' + str(serve_log)}")
            else:
                print(
                    f"[serve] ready in {cold:.0f}s, "
                    f"GPU {card['operational']['gpu_used_mib']} MiB"
                )
                base_url = f"http://localhost:{port}/v1"
                card["operational"] |= evalctl.measure_speed(base_url, key)
                decode = card["operational"].get("decode_tok_s")
                if decode is not None and decode < score.MIN_DECODE_TOK_S:
                    card["notes"] = (
                        f"works but impractically slow on kai: {decode} tok/s decode"
                    )
                card["suites"] = _run_suites(key, base_url, to_run, log_dir)

    # Fold in suites this run didn't cover (e.g. `--suite code` keeps prior tools results),
    # so the model's card — and its one leaderboard row — stays complete.
    card["suites"] = score.merge_prior_suites(key, card["suites"])
    card["verdict"] = score.verdict(
        card["operational"].get("served", False),
        card["suites"],
        card["operational"].get("decode_tok_s"),
    )
    return card


def _select_models(args, registry: dict, suites: dict) -> list[str]:
    if args.keys:
        for k in args.keys:
            if k not in registry:
                sys.exit(f"error: unknown model '{k}' (try: just models-list)")
        return args.keys
    if not args.all:
        sys.exit("error: name model keys or pass --all")
    selected = []
    for key, entry in registry.items():
        needed = {
            cap: ver for cap, (_, ver) in _suites_for(entry, args.suite, suites).items()
        }
        prior = score.latest_scorecard(key)
        if prior and prior.get("verdict") == "skip" and not args.retry_skips:
            print(f"[skip] {key}: prior gate verdict 'skip' (--retry-skips to retest)")
            continue
        if not args.force and score.scorecard_current(key, needed):
            print(
                f"[skip] {key}: already scored on current suite versions (--force to rerun)"
            )
            continue
        selected.append(key)
    return selected


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kvllm.evalrun", description=__doc__)
    p.add_argument("keys", nargs="*", help="registry model key(s) to evaluate")
    p.add_argument(
        "--all", action="store_true", help="sweep the whole registry (resumable)"
    )
    p.add_argument(
        "--suite", default=None, help="run only this capability suite (e.g. tools)"
    )
    p.add_argument("--port", type=int, default=8000)
    p.add_argument(
        "--endpoint", default=None, help="eval this /v1 URL (no serve orchestration)"
    )
    p.add_argument(
        "--model-name",
        default=None,
        help="served model id at --endpoint if not the key",
    )
    p.add_argument("--force", action="store_true", help="rerun even if already current")
    p.add_argument(
        "--retry-skips", action="store_true", help="retest models the gate skipped"
    )
    p.add_argument(
        "--date", default=os.environ.get("KVLLM_EVAL_DATE") or date.today().isoformat()
    )
    p.add_argument(
        "--no-write",
        action="store_true",
        help="don't write scorecard/leaderboard/registry",
    )
    args = p.parse_args(argv)

    if args.endpoint and (args.all or len(args.keys) != 1):
        sys.exit("error: --endpoint evaluates exactly one model key")

    registry = load_registry()
    suites = _suites()
    selected = _select_models(args, registry, suites)
    if not selected:
        print("nothing to do — all selected models are current")
        return 0
    current_versions = {cap: ver for cap, (_, ver) in suites.items()}

    # Service is managed once per sweep, not per model: rapid stop/serve/kill/restart
    # cycling is what wedged the GPU (GSP hang, Xid 119) on 2026-07-02.
    manage_service = not args.endpoint and evalctl.service_active()
    if manage_service:
        evalctl.stop_service()

    failures = 0
    try:
        for i, key in enumerate(selected, 1):
            print(f"\n=== [{i}/{len(selected)}] {key} ===")
            try:
                card = evaluate(
                    key,
                    registry[key],
                    port=args.port,
                    only_suite=args.suite,
                    today=args.date,
                    endpoint=args.endpoint,
                    model_name=args.model_name,
                    force=args.force,
                )
            except KeyboardInterrupt:
                raise
            except Exception as e:  # one broken model must not kill an overnight sweep
                print(f"[error] {key}: {e}")
                failures += 1
                continue
            print(f"=== {key}: {card['verdict'].upper()} ===")
            if not args.no_write:
                paths = score.write_all(card, current_versions)
                print("wrote:", ", ".join(str(p) for p in paths))
    finally:
        if manage_service:
            evalctl.start_service()
            if evalctl.wait_port_healthy(args.port):
                print("[orchestrate] service restored and healthy")
            else:
                print(
                    "[orchestrate] WARNING: restored service is NOT healthy — "
                    f"check `journalctl --user -u kvllm` and nvidia-smi (port {args.port})"
                )
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
