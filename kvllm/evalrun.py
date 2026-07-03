"""Batch eval runner — serve→gate→suites→score for one, several, or all registry models.

    uv run --group eval python -m kvllm.evalrun <key> [<key> ...]   # specific models
    uv run --group eval python -m kvllm.evalrun --all               # sweep the registry
      [--suite tools] [--force] [--retry-skips] [--no-write] [--port 8000]
      [--endpoint URL [--model-name NAME]]                          # eval a served /v1 directly

Models run serially (vLLM = one model per GPU); everything inside a model runs through
Inspect's eval_set, which retries and resumes via a per-suite log dir (eval-logs/<key>/<date>/<cap>).
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
    """Suite name → (task factory, version, required registry capability, optional). Imported
    lazily to keep inspect off the CLI-arg-error path. A suite runs on a model iff the model's
    registry `capabilities` contain the required cap (`judged` rides on plain `chat` — every
    model). Optional suites (`assisted`) run ONLY when named via --suite — they're labeled
    alternate conditions, never part of the default sweep or its resume check."""
    from evals.agentic import ASSISTED_VERSION, agentic, agentic_assisted
    from evals.agentic import VERSION as AGENTIC_VERSION
    from evals.coding import VERSION as CODING_VERSION
    from evals.coding import coding
    from evals.judged import VERSION as JUDGED_VERSION
    from evals.judged import judged
    from evals.tools import VERSION as TOOLS_VERSION
    from evals.tools import tools

    return {
        "tools": (tools, TOOLS_VERSION, "tools", False),
        "code": (coding, CODING_VERSION, "code", False),
        "agentic": (agentic, AGENTIC_VERSION, "tools", False),
        "judged": (judged, JUDGED_VERSION, "chat", False),
        "assisted": (agentic_assisted, ASSISTED_VERSION, "tools", True),
    }


def _suites_for(entry: dict, only: str | None, suites: dict) -> dict:
    caps = entry.get("capabilities", [])
    return {
        name: (factory, version)
        for name, (factory, version, req_cap, optional) in suites.items()
        if req_cap in caps and (only == name if optional or only else True)
    }


def _apply_sandbox_host() -> None:
    """Point suite sandboxes at [sandbox].docker_host (planning/04 — the ksandbox
    cutover). An explicit DOCKER_HOST in the environment wins over config."""
    if os.environ.get("DOCKER_HOST"):
        print(f"[sandbox] DOCKER_HOST={os.environ['DOCKER_HOST']} (env)")
        return
    host = score.load_config().get("sandbox", {}).get("docker_host", "")
    if host:
        os.environ["DOCKER_HOST"] = host
        print(f"[sandbox] DOCKER_HOST={host} (eval-config.toml)")


def _run_suites(
    model: str,
    to_run: dict,
    log_root: Path,
    *,
    local: bool,
    base_url: str | None = None,
) -> tuple[dict, dict, dict]:
    """Run each suite against `model` (a full Inspect model string) in its OWN log subdir
    (log_root/<cap>) so suites never share an eval_set manifest. Returns (suite results,
    subject-model usage, judge/other usage). temperature=0.0 is applied only to LOCAL models —
    frontier baselines run at provider defaults (Sonnet 5 rejects non-default sampling)."""
    from inspect_ai import eval_set

    _apply_sandbox_host()
    if local:
        os.environ["KVLLM_BASE_URL"] = base_url or "http://localhost:8000/v1"
        os.environ.setdefault("KVLLM_API_KEY", "EMPTY")

    results: dict[str, dict] = {}
    usage: dict = {}
    judge_usage: dict = {}
    for cap, (factory, version) in to_run.items():
        sdir = log_root / cap
        print(f"[suite] {cap} via inspect eval_set → {sdir}")
        kwargs = {"temperature": 0.0} if local else {}
        if local and cap in ("agentic", "assisted"):
            # Episodes are long generation loops against ONE local vLLM: 9-way concurrency
            # makes each sample's wall-clock budget mostly queue-wait behind its siblings,
            # and slow models (42-44 tok/s hybrids) die on the task backstop UNSCORED.
            # 3-way keeps the pipeline busy while time limits measure the model, not the
            # queue. API baselines keep full concurrency (provider-side parallelism).
            kwargs["max_samples"] = 3
        try:
            _success, logs = eval_set(
                tasks=[factory()], model=model, log_dir=str(sdir), **kwargs
            )
        except Exception as e:
            # Same-day logs from an older task manifest (suite version bump or task-config
            # change since the last run) — eval_set refuses the log dir, and those logs'
            # results are unusable anyway. Clear just this suite dir and retry once.
            msg = str(e)
            if (
                "not associated with a task" not in msg
                and "fresh log directory" not in msg
            ):
                raise
            print(f"[suite] {cap}: stale logs from an older task manifest — clearing")
            shutil.rmtree(sdir, ignore_errors=True)
            _success, logs = eval_set(
                tasks=[factory()], model=model, log_dir=str(sdir), **kwargs
            )
        log = next(
            (lg for lg in logs if lg.eval.task == cap), logs[0] if logs else None
        )
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
        subject, other = score.usage_from_log(log.location, model)
        score.add_usage(usage, subject)
        score.add_usage(judge_usage, other)
        s = results[cap]
        print(f"[suite] {cap}: {s['passed']}/{s['total']} ({s['pass_rate']:.0%})")
        for c in s["cases"]:
            print(
                f"    {'PASS' if c['passed'] else 'FAIL'}  {c['name']}: {c['detail']}"
            )
    return results, usage, judge_usage


def _total_usage(log_root: Path, model_str: str) -> tuple[dict, dict]:
    """Sum (subject, judge) usage over the latest .eval log in every suite subdir under
    log_root — the whole model/date, regardless of which suites this invocation executed."""
    usage: dict = {}
    judge_usage: dict = {}
    for sdir in sorted(log_root.glob("*/")):
        logs = sorted(sdir.glob("*.eval"))
        if not logs:
            continue
        subject, other = score.usage_from_log(logs[-1], model_str)
        score.add_usage(usage, subject)
        score.add_usage(judge_usage, other)
    return usage, judge_usage


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
    log_root = LOG_ROOT / key.replace("/", "_") / today
    if force:
        # eval_set resumes from completed logs — a --force rerun must re-execute. Only clear
        # the suites we're about to run, so `--force --suite code` keeps the tools transcript.
        for cap in to_run:
            sdir = log_root / cap
            if sdir.exists():
                shutil.rmtree(sdir)

    card: dict = {
        "schema": 2,
        "model": key,
        "date": today,
        "hf_repo": entry.get("hf_repo"),
        "operational": {},
        "suites": {},
        "notes": "",
    }

    if entry.get("provider"):
        # Frontier baseline: no serving, no gate — straight to the suites via the API.
        card["baseline"] = True
        card["provider"] = entry["provider"]
        card["operational"]["served"] = True
        card["suites"], _, _ = _run_suites(
            entry["provider"], to_run, log_root, local=False
        )
        card["suites"] = score.merge_prior_suites(key, card["suites"])
        # Usage/cost totals span ALL current suite logs for this model/date (a partial
        # --suite rerun must not shrink the reported full-suite cost).
        usage, judge_usage = _total_usage(log_root, entry["provider"])
        card["usage"], card["judge_usage"] = usage, judge_usage
        card["est_cost_usd"] = score.estimate_cost(usage, entry["provider"])
        card["judge_cost_usd"] = score.estimate_cost(
            judge_usage, score.load_config()["judge"]["model"]
        )
        card["verdict"] = "baseline"
        return card

    if endpoint:
        card["operational"]["served"] = True
        card["operational"] |= evalctl.measure_speed(endpoint, served_name)
        card["suites"], usage, judge_usage = _run_suites(
            f"openai-api/kvllm/{served_name}",
            to_run,
            log_root,
            local=True,
            base_url=endpoint,
        )
        card["usage"], card["judge_usage"] = usage, judge_usage
        card["judge_cost_usd"] = score.estimate_cost(
            judge_usage, score.load_config()["judge"]["model"]
        )
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
                ctx_ok = evalctl.context_probe(
                    base_url, key, int(entry.get("max_model_len", 8192))
                )
                if ctx_ok is not None:
                    card["operational"]["ctx_probe_ok"] = ctx_ok
                decode = card["operational"].get("decode_tok_s")
                if decode is not None and decode < score.MIN_DECODE_TOK_S:
                    card["notes"] = (
                        f"works but impractically slow on kai: {decode} tok/s decode"
                    )
                if ctx_ok is False:
                    card["notes"] = (
                        card["notes"] or ""
                    ) + " context probe failed at 75% of max_model_len"
                card["suites"], usage, judge_usage = _run_suites(
                    f"openai-api/kvllm/{key}",
                    to_run,
                    log_root,
                    local=True,
                    base_url=base_url,
                )
                card["usage"], card["judge_usage"] = usage, judge_usage
                card["judge_cost_usd"] = score.estimate_cost(
                    judge_usage, score.load_config()["judge"]["model"]
                )

    # Fold in suites this run didn't cover (e.g. `--suite code` keeps prior tools results),
    # so the model's card — and its one leaderboard row — stays complete.
    card["suites"] = score.merge_prior_suites(key, card["suites"])
    card["verdict"] = score.verdict(
        card["operational"].get("served", False),
        card["suites"],
        card["operational"].get("decode_tok_s"),
        current_versions={cap: v[1] for cap, v in suites.items()},
    )
    if card["operational"].get("ctx_probe_ok") is False and card["verdict"] == (
        "worth trying"
    ):
        card["verdict"] = "has issues"  # breaks under context pressure
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
        if entry.get("provider"):
            print(f"[skip] {key}: API baseline — run explicitly (`just eval {key}`)")
            continue  # sweeps shouldn't silently spend API dollars
        needed = {
            cap: ver for cap, (_, ver) in _suites_for(entry, args.suite, suites).items()
        }
        prior = score.latest_scorecard(key)
        if prior and prior.get("verdict") == "skip" and not args.retry_skips:
            print(f"[skip] {key}: prior gate verdict 'skip' (--retry-skips to retest)")
            continue
        if not args.force and score.scorecard_current(key, needed):
            # Suites are current — but a v1-gate card (no decode split) still needs a
            # schema-2 gate refresh (deepseek/internvl carry blended v1 numbers).
            if prior and "decode_tok_s" not in prior.get("operational", {}):
                print(f"[gate-refresh] {key}: v1 gate data — re-measuring")
            else:
                print(
                    f"[skip] {key}: already scored on current suite versions "
                    "(--force to rerun)"
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
    p.add_argument(
        "--rebuild-board",
        action="store_true",
        help="rebuild the leaderboard from existing scorecards (after re-weighting "
        "eval-config.toml) — runs no evals",
    )
    args = p.parse_args(argv)

    if args.rebuild_board:
        suites = _suites()
        versions = {cap: v[1] for cap, v in suites.items()}
        for change in score.refresh_verdicts(versions):
            print("verdict:", change)
        paths = score.write_leaderboard(versions)
        print("rebuilt:", ", ".join(str(p) for p in paths))
        return 0

    if args.endpoint and (args.all or len(args.keys) != 1):
        sys.exit("error: --endpoint evaluates exactly one model key")

    registry = load_registry()
    suites = _suites()
    selected = _select_models(args, registry, suites)
    if not selected:
        print("nothing to do — all selected models are current")
        return 0
    current_versions = {cap: v[1] for cap, v in suites.items()}

    # Service is managed once per sweep, not per model: rapid stop/serve/kill/restart
    # cycling is what wedged the GPU (GSP hang, Xid 119) on 2026-07-02. API baselines
    # don't touch the GPU — a baselines-only run leaves the service alone.
    any_local = any(not registry[k].get("provider") for k in selected)
    manage_service = any_local and not args.endpoint and evalctl.service_active()
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
