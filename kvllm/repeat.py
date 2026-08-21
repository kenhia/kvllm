"""N repeated evals of one model — the noise floor under the numbers on the board.

    uv run --group eval python -m kvllm.repeat <key> --suite agentic --n 3
      [--publish median|first|last|none] [--port 8000] [--endpoint URL] [--settle 45]
      [--confirm-cost]                          # required for API-priced models

Sprint 15 re-ran `claude-sonnet-5` with every variable *we* control held constant and
`agentic` still moved +0.14 — ±0.035 on the composite, against a #1/#2 gap of 0.02. Rank
ordering inside that is not a result. This runs the same model N times and reports the
band, so the board can say which differences are too small to mean anything.

**Why this is a separate entry point and not a shell loop.** From korg:1499, verified
against evalrun.py:

- `eval_set` RESUMES from completed logs. `for i in 1 2 3; do just eval ...; done` reports
  run 1 three times and yields a spread of exactly 0.00 — not an error, just a number that
  looks like an answer and would invalidate the whole exercise while appearing to satisfy
  it. Both non-`--force` paths collapse to that zero.
- `--force` is the only thing that re-executes, and it rmtree's the suite log dir first, so
  looping it leaves exactly one set of transcripts and nothing to compute a spread from.

So each run gets its OWN log directory (`evaluate(run_tag=...)`) and its card is harvested
in-process before the next run starts. Nothing resumes, nothing is destroyed.

Two more things it does deliberately:

- **The service is managed once for the whole batch**, not once per run. Rapid
  stop/serve/kill cycling is what wedged the GPU on 2026-07-02 (GSP hang, Xid 119); local
  runs also settle between iterations so VRAM drains.
- **It chooses what the board shows.** Every eval invocation rewrites the scorecard and the
  leaderboard, so left alone the board ends up displaying whichever run happened to finish
  last, presented as *the* number. `--publish` makes that a decision.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import date
from pathlib import Path

from kvllm import evalctl, evalrun, runstate, score
from kvllm.registry import load_registry

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "model-research" / "evals" / "noise-floor"


# --- aggregation ---------------------------------------------------------------------


def spread(cards: list[dict], fresh: list[str]) -> dict:
    """Per-suite band across the N cards, over `fresh` suites ONLY.

    `fresh` is what each run actually re-executed. A card also carries suites merged
    forward from earlier dates by `merge_prior_suites` — byte-identical in every run
    because they were measured once — and folding those in would publish a 0.00 "noise
    floor" for a suite that was never repeated. That is the artifact this module exists to
    avoid, so the caller states which suites were run and only those are reported.

    A real 0.00 (tools and code came back bit-identical in sprint 15) is kept and labelled
    `identical`, never dropped: it is a result, but it must not be read without the label.
    """
    out: dict[str, dict] = {}
    for cap in fresh:
        runs: list[float] = []
        errors: list[str] = []
        for i, card in enumerate(cards, 1):
            s = card.get("suites", {}).get(cap)
            if s is None:
                continue
            if s.get("error"):
                errors.append(f"run {i}: {s['error']}")
                continue
            runs.append(float(s.get("pass_rate", 0.0)))
        out[cap] = {
            "n": len(runs),
            "runs": runs,
            "errors": errors,
            "min": min(runs) if runs else None,
            "max": max(runs) if runs else None,
            "spread": round(max(runs) - min(runs), 4) if runs else None,
            "mean": statistics.fmean(runs) if runs else None,
            "median": statistics.median(runs) if runs else None,
            # Only meaningful once something was actually repeated.
            "identical": len(runs) > 1 and max(runs) == min(runs),
        }
    return out


def _run_value(card: dict, fresh: list[str]) -> float:
    """One number per run, for ranking them: the mean pass rate over the repeated suites.
    Errored/absent suites score 0 — a run that failed a suite should not out-rank one that
    completed it."""
    vals = [
        0.0
        if (s := card.get("suites", {}).get(cap)) is None or s.get("error")
        else float(s.get("pass_rate", 0.0))
        for cap in fresh
    ]
    return statistics.fmean(vals) if vals else 0.0


def pick_index(cards: list[dict], policy: str, fresh: list[str]) -> int | None:
    """Which run the board should show — a decision, not an accident.

    `median` is the default: with N=3 it discards the lucky and unlucky draw and publishes
    the representative one. `none` leaves the board untouched. Ties resolve by run order,
    so the answer is reproducible.
    """
    if not cards or policy == "none":
        return None
    if policy == "first":
        return 0
    if policy == "last":
        return len(cards) - 1
    if policy == "median":
        order = sorted(range(len(cards)), key=lambda i: _run_value(cards[i], fresh))
        return order[(len(order) - 1) // 2]
    raise ValueError(f"unknown publish policy: {policy}")


def render_markdown(
    *, key: str, date: str, stats: dict, chosen: int | None, n: int
) -> str:
    """The writeup that goes next to the scorecards. Deliberately states the confound:
    repeats inside one night hold provider-side drift roughly constant, so what comes out
    is a LOWER bound on run-to-run variance, not the total uncertainty."""
    lines = [
        f"# Noise floor — `{key}` ×{n} ({date})",
        "",
        "| suite | n | min | max | band | median | mean |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cap, s in sorted(stats.items()):
        if not s["n"]:
            lines.append(f"| `{cap}` | 0 | — | — | — | — | — |")
            continue
        flag = " *(identical)*" if s["identical"] else ""
        lines.append(
            f"| `{cap}` | {s['n']} | {s['min']:.3f} | {s['max']:.3f} | "
            f"**{s['spread']:.3f}**{flag} | {s['median']:.3f} | {s['mean']:.3f} |"
        )
    lines += ["", "Per-run pass rates:", ""]
    for cap, s in sorted(stats.items()):
        runs = ", ".join(f"{v:.3f}" for v in s["runs"]) or "—"
        lines.append(f"- `{cap}`: {runs}")
        for err in s["errors"]:
            lines.append(f"  - error — {err}")

    published = (
        f"run {chosen + 1}" if chosen is not None else "nothing (board untouched)"
    )
    lines += [
        "",
        f"**Published to the board:** {published}. Every eval invocation rewrites the "
        "scorecard and the leaderboard, so without a choice here the board would show "
        "whichever run finished last, presented as *the* number.",
        "",
        "**Read the band as a floor, not the uncertainty.** All N runs happened in one "
        "night, which holds provider-side drift roughly constant, so this is a "
        "*within-night* figure and a lower bound on real run-to-run variance across days. "
        'The honest board language is "differences below X are definitely not '
        'meaningful", not "X is the total uncertainty". A local model has no provider-drift '
        "confound, so its band is the cleaner read on pure harness noise — report the two "
        "separately rather than pooling them.",
        "",
        f"N={n} bounds a band. It does not give a trustworthy standard deviation and is "
        "not publishable as a variance study (korg:1499).",
        "",
    ]
    return "\n".join(lines)


# --- orchestration -------------------------------------------------------------------


def _fresh_caps(entry: dict, only_suite: str | None) -> list[str]:
    """The suites each repeat will actually re-execute. `--force` bypasses the staleness
    filter, so this is simply every suite the model is capable of (or the one named)."""
    return list(evalrun._suites_for(entry, only_suite, evalrun._suites()))


def _prior_cost(key: str) -> float | None:
    prior = score.latest_scorecard(key) or {}
    return prior.get("est_cost_usd")


def repeat_model(
    key: str,
    entry: dict,
    *,
    cards: list[dict],
    n: int,
    suite: str | None,
    port: int,
    endpoint: str | None,
    model_name: str | None,
    today: str,
    settle_s: int,
) -> list[dict]:
    """Run `key` n times, harvesting each card before the next run begins.

    Cards are appended to the caller's `cards` list rather than only returned, so a run
    that dies partway still leaves the completed ones where the caller's `finally` can
    persist them. Returning them alone would lose everything to the unwinding exception —
    a night that fails on run 3 must not throw away runs 1 and 2.
    """
    local = not entry.get("provider")
    for i in range(1, n + 1):
        print(f"\n########## {key}: run {i}/{n} ##########")
        runstate.set_model(key, i, n)
        card = evalrun.evaluate(
            key,
            entry,
            port=port,
            only_suite=suite,
            today=today,
            endpoint=endpoint,
            model_name=model_name,
            force=True,
            run_tag=f"r{i}",
        )
        card["run_index"] = i
        cards.append(card)
        for cap, s in sorted(card.get("suites", {}).items()):
            if suite in (None, cap):
                print(f"[run {i}] {cap}: {s.get('pass_rate', 0.0):.3f}")
        if local and not endpoint and i < n:
            # One model per process is already the rule; give VRAM time to drain before
            # the next serve rather than stop/serve cycling (GSP wedge, 2026-07-02).
            print(f"[settle] {settle_s}s before run {i + 1}")
            time.sleep(settle_s)
    return cards


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kvllm.repeat", description=__doc__)
    p.add_argument("key", help="registry model key to repeat")
    p.add_argument("--n", type=int, default=3, help="number of runs (default 3)")
    p.add_argument(
        "--suite", default=None, help="repeat only this suite (e.g. agentic)"
    )
    p.add_argument("--port", type=int, default=8000)
    p.add_argument(
        "--endpoint", default=None, help="eval this /v1 URL (no serve orchestration)"
    )
    p.add_argument("--model-name", default=None, help="served model id at --endpoint")
    p.add_argument(
        "--publish",
        default="median",
        choices=["median", "first", "last", "none"],
        help="which run the scorecard/leaderboard should show (default median)",
    )
    p.add_argument(
        "--settle",
        type=int,
        default=45,
        help="seconds to let VRAM drain between local runs (default 45)",
    )
    p.add_argument(
        "--confirm-cost",
        action="store_true",
        help="acknowledge the API spend; required for provider-priced models",
    )
    p.add_argument(
        "--date", default=os.environ.get("KVLLM_EVAL_DATE") or date.today().isoformat()
    )
    args = p.parse_args(argv)

    if args.n < 2:
        sys.exit("error: --n must be at least 2 (one run has no spread)")

    registry = load_registry()
    if args.key not in registry:
        sys.exit(f"error: unknown model '{args.key}' (try: just models-list)")
    entry = registry[args.key]

    # The cost gate from korg:1499, encoded rather than remembered. An overnight run must
    # never stall at 02:00 waiting for this, so it is answered here, at launch.
    if entry.get("provider"):
        per_run = _prior_cost(args.key)
        est = f"~${per_run * args.n:.2f}" if per_run else "unknown"
        print(
            f"[cost] {args.key} is API-priced: {args.n} runs ≈ {est}"
            + (f" (last full run measured ${per_run:.2f})" if per_run else "")
            + ("; restricting to one suite costs less" if args.suite else "")
        )
        if not args.confirm_cost:
            sys.exit(
                "error: refusing to spend without --confirm-cost. Check the balance at "
                "https://platform.claude.com/settings/billing first."
            )

    fresh = _fresh_caps(entry, args.suite)
    if not fresh:
        sys.exit(f"error: {args.key} has no suites matching --suite {args.suite}")
    print(f"[repeat] {args.key} ×{args.n} · suites: {', '.join(fresh)}")

    out_dir = RESULTS / f"{score._slug(args.key)}-{args.date}"
    out_dir.mkdir(parents=True, exist_ok=True)

    local = not entry.get("provider")
    manage_service = local and not args.endpoint and evalctl.service_active()
    if manage_service:
        evalctl.stop_service()

    runstate.begin(
        models=[args.key],
        argv=list(argv) if argv is not None else sys.argv[1:],
        label=f"noise floor · {args.key} ×{args.n}",
    )
    cards: list[dict] = []
    try:
        repeat_model(
            args.key,
            entry,
            cards=cards,
            n=args.n,
            suite=args.suite,
            port=args.port,
            endpoint=args.endpoint,
            model_name=args.model_name,
            today=args.date,
            settle_s=args.settle,
        )
    finally:
        # Cards are written even on a partial run — a night that dies at run 3 should not
        # throw away runs 1 and 2.
        for card in cards:
            (out_dir / f"run-{card['run_index']}.json").write_text(
                json.dumps(card, indent=2) + "\n"
            )
        if manage_service:
            evalctl.start_service()
            if not evalctl.wait_port_healthy(args.port):
                print(
                    "[orchestrate] WARNING: restored service is NOT healthy — check "
                    f"`journalctl --user -u kvllm` and nvidia-smi (port {args.port})",
                    file=sys.stderr,
                )

    if len(cards) < 2:
        runstate.end("failed", 1)
        print(f"[repeat] only {len(cards)} run(s) completed — no band to report")
        return 1

    stats = spread(cards, fresh)
    chosen = pick_index(cards, args.publish, fresh)

    for cap, s in sorted(stats.items()):
        if not s["n"]:
            print(f"[band] {cap}: no usable runs")
            continue
        note = "  (identical across runs)" if s["identical"] else ""
        print(
            f"[band] {cap}: {s['min']:.3f}–{s['max']:.3f}  "
            f"spread {s['spread']:.3f}  median {s['median']:.3f}{note}"
        )

    summary = {
        "model": args.key,
        "date": args.date,
        "n": args.n,
        "suites_repeated": fresh,
        "publish": args.publish,
        "published_run": None if chosen is None else chosen + 1,
        "stats": stats,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out_dir / "README.md").write_text(
        render_markdown(
            key=args.key, date=args.date, stats=stats, chosen=chosen, n=args.n
        )
    )
    print(f"[repeat] wrote {out_dir}/summary.json, {out_dir}/README.md")

    if chosen is None:
        print("[publish] --publish none: scorecard and leaderboard left untouched")
    else:
        versions = {cap: v[1] for cap, v in evalrun._suites().items()}
        paths = score.write_all(cards[chosen], versions)
        print(
            f"[publish] board shows run {chosen + 1} of {args.n} "
            f"({args.publish}): {', '.join(str(x) for x in paths)}"
        )

    runstate.end("done", 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
