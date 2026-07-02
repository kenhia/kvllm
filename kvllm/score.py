"""Scoring & reporting — scorecards, verdicts, the tri-format leaderboard, models.toml write-back.

Successor to kvllm/eval/report.py for harness v2 (fable-planning/02): scorecards now record a
suite `version` and the Inspect `.eval` log path per suite, operational gains ttft_s/decode_tok_s,
and the leaderboard marks scores from older suite versions as stale (†). Weighted composite
ranking lands in Phase 3; verdict logic is unchanged from v1 (threshold + speed floor).

Scorecard schema (v2):
    {"schema": 2, "model", "date", "hf_repo",
     "operational": {"served", "cold_start_s", "gpu_used_mib", "ttft_s", "decode_tok_s", "error"?},
     "suites": {"tools": {"version", "passed", "total", "pass_rate", "cases": [...], "log"}},
     "verdict", "notes"}
"""

from __future__ import annotations

import html
import json
import tomllib
from pathlib import Path

import tomlkit

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "docs" / "model-research" / "evals"
REGISTRY = REPO / "models.toml"
CONFIG = REPO / "eval-config.toml"

VERDICT_EMOJI = {
    "worth trying": "✅",
    "has issues": "⚠️",
    "skip": "❌",
    "baseline": "🌐",
}

MIN_DECODE_TOK_S = 10.0  # config [speed].floor_tok_s default; kept as a module fallback

_DEFAULT_CONFIG = {
    "weights": {"tools": 0.30, "code": 0.35, "agentic": 0.25, "judged": 0.10},
    "speed": {"floor_tok_s": 10, "full_tok_s": 40},
    "verdict": {"composite_floor": 0.55, "suite_floor": 0.40},
    "judge": {"model": "anthropic/claude-haiku-4-5-20251001", "calibrated": False},
}


def load_config() -> dict:
    """eval-config.toml with defaults filled per-section (missing file → all defaults)."""
    cfg = {k: dict(v) for k, v in _DEFAULT_CONFIG.items()}
    if CONFIG.is_file():
        for section, values in tomllib.loads(CONFIG.read_text()).items():
            cfg.setdefault(section, {}).update(values)
    return cfg


# --- composite score (fable-planning/03) -------------------------------------------------


def speed_factor(decode_tok_s: float | None, cfg: dict) -> float:
    """Multiplier from decode tok/s: ≤ floor → 0.5, ≥ full → 1.0, linear between.
    Unmeasured speed → 1.0 (the gate warns loudly when it can't measure)."""
    if decode_tok_s is None:
        return 1.0
    floor = cfg["speed"]["floor_tok_s"]
    full = cfg["speed"]["full_tok_s"]
    if decode_tok_s <= floor:
        return 0.5
    if decode_tok_s >= full:
        return 1.0
    return round(0.5 + 0.5 * (decode_tok_s - floor) / (full - floor), 3)


def composite(
    card: dict, cfg: dict, current_versions: dict[str, int] | None = None
) -> dict | None:
    """Weighted composite over the suites the model is ELIGIBLE for: weight > 0, scored at the
    current suite version (stale scores are shown † but never ranked), and — for `judged` —
    only once the judge is calibrated. Weights renormalize over eligible suites. Returns None
    when no suite is eligible (gate-only models are unranked, not zero-ranked)."""
    weights = cfg["weights"]
    eligible: dict[str, float] = {}
    for cap, s in card.get("suites", {}).items():
        w = weights.get(cap, 0.0)
        if w <= 0:
            continue
        if cap == "judged" and not cfg["judge"].get("calibrated"):
            continue
        if (
            current_versions
            and cap in current_versions
            and s.get("version") != current_versions[cap]
        ):
            continue
        eligible[cap] = s.get("pass_rate", 0.0)
    if not eligible:
        return None
    wsum = sum(weights[cap] for cap in eligible)
    base = sum(weights[cap] * rate for cap, rate in eligible.items()) / wsum
    sf = speed_factor(card.get("operational", {}).get("decode_tok_s"), cfg)
    return {
        "composite": round(sf * base, 3),
        "base": round(base, 3),
        "speed_factor": sf,
        "eligible": sorted(eligible),
    }


def verdict(
    served: bool,
    suites: dict,
    decode_tok_s: float | None = None,
    *,
    cfg: dict | None = None,
    current_versions: dict[str, int] | None = None,
) -> str:
    """worth trying / has issues / skip, derived from the composite (fable-planning/03):
    `skip` = gate failed; `has issues` = composite < floor, decode at/below the speed floor,
    or any weighted suite < suite_floor; else `worth trying`. Gate-only models (no eligible
    suites) fall back to the speed check alone — v1 behavior."""
    if not served:
        return "skip"
    cfg = cfg or load_config()
    floor = cfg["speed"]["floor_tok_s"]
    if decode_tok_s is not None and decode_tok_s <= floor:
        return "has issues"
    comp = composite(
        {"suites": suites, "operational": {"decode_tok_s": decode_tok_s}},
        cfg,
        current_versions,
    )
    if comp is None:
        return "worth trying"
    if comp["composite"] < cfg["verdict"]["composite_floor"]:
        return "has issues"
    suite_floor = cfg["verdict"]["suite_floor"]
    weights = cfg["weights"]
    for cap in comp["eligible"]:
        if weights.get(cap, 0) > 0 and suites[cap].get("pass_rate", 0.0) < suite_floor:
            return "has issues"
    return "worth trying"


# --- inspect log → suite result ---------------------------------------------------------


def _normalize_log_path(log_path: str | Path) -> str:
    """Repo-relative form of an Inspect log location. eval_set returns cached-log
    locations as file: URIs; fresh runs return plain paths — normalize both."""
    loc = str(log_path)
    if loc.startswith("file://"):
        loc = loc[7:]
    elif loc.startswith("file:"):
        loc = loc[5:]
    p = Path(loc).resolve()
    try:
        return str(p.relative_to(REPO))
    except ValueError:  # log dir outside the repo — keep it absolute
        return str(p)


def _points(value) -> float:
    """A score value → [0, 1] points. Binary suites (tools) use CORRECT/INCORRECT ('C'/'I');
    partial-credit suites (coding) use a float 0..1. Both collapse here."""
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return 1.0 if value == "C" else 0.0
    return 0.0


def suite_from_log(log_path: str | Path, version: int) -> dict:
    """Reduce one Inspect .eval log to the scorecard suite shape. Handles both binary
    (tools: pass_rate = fraction correct) and partial-credit (coding: pass_rate = mean of the
    per-task float scores) suites. If any case carries a `saw_failing_run` flag, an
    `iteration_rate` (share of those that then recovered) is added — the coding suite's metric."""
    from inspect_ai.log import read_eval_log  # heavy import; only when aggregating

    log = read_eval_log(str(log_path))
    cases = []
    for sample in log.samples or []:
        sc = next(iter((sample.scores or {}).values()), None)
        meta = dict(sc.metadata) if sc and sc.metadata else {}
        detail = (sc.explanation if sc else "no score recorded") or ""
        if "raw_frac" in meta:
            # Partial-credit suite: recompute canonically from the logged evidence, so old
            # logs (whose scorer penalized ×0.9 for merely not calling submit) and new ones
            # score identically: penalty only when a REAL limit terminated the sample.
            real_limit = bool(getattr(sample, "limit", None))
            pts = meta["raw_frac"] * (0.9 if real_limit else 1.0)
            passed = meta["raw_frac"] >= 0.999
            if not real_limit:
                detail = detail.replace("; hit message/time limit (×0.9)", "")
        else:
            pts = _points(sc.value) if sc else 0.0
            passed = pts >= 0.999
        cases.append(
            {
                "name": str(sample.id),
                "passed": passed,
                "score": round(pts, 3),
                "detail": detail,
                "meta": meta,
            }
        )
    n = len(cases)
    result = {
        "version": version,
        "passed": sum(1 for c in cases if c["passed"]),
        "total": n,
        "pass_rate": round(sum(c["score"] for c in cases) / n, 2) if n else 0.0,
        "cases": cases,
        "log": _normalize_log_path(log_path),
    }
    iter_cases = [c for c in cases if c["meta"].get("saw_failing_run")]
    if iter_cases:
        result["iteration_rate"] = round(
            sum(1 for c in iter_cases if c["meta"].get("recovered")) / len(iter_cases),
            2,
        )
    if log.status != "success":
        result["error"] = f"inspect run status: {log.status}"
    return result


def usage_from_log(log_path: str | Path, model_str: str) -> tuple[dict, dict]:
    """(model-under-test usage, judge/other usage) from one Inspect log's stats — token counts
    keyed {input, output, cache_read, cache_write}. Cost comparison needs the subject model's
    spend; everything else in the log (the judge) is harness overhead, tracked separately."""
    from inspect_ai.log import read_eval_log

    log = read_eval_log(str(log_path), header_only=True)
    subject = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    other = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    for model, mu in (log.stats.model_usage or {}).items():
        bucket = subject if model == model_str else other
        bucket["input"] += mu.input_tokens or 0
        bucket["output"] += mu.output_tokens or 0
        bucket["cache_read"] += mu.input_tokens_cache_read or 0
        bucket["cache_write"] += mu.input_tokens_cache_write or 0
    return subject, other


def add_usage(total: dict, part: dict) -> dict:
    for k, v in part.items():
        total[k] = total.get(k, 0) + v
    return total


def estimate_cost(usage: dict, provider: str, cfg: dict | None = None) -> float | None:
    """Estimated USD for `usage` at [pricing.<provider>] rates (per MTok; cache read 0.1×,
    cache write 1.25× input). None when the provider isn't priced (local models)."""
    cfg = cfg or load_config()
    price = cfg.get("pricing", {}).get(provider)
    if not price:
        return None
    in_rate, out_rate = price["input"], price["output"]
    usd = (
        usage.get("input", 0) * in_rate
        + usage.get("output", 0) * out_rate
        + usage.get("cache_read", 0) * 0.1 * in_rate
        + usage.get("cache_write", 0) * 1.25 * in_rate
    ) / 1_000_000
    return round(usd, 4)


def merge_prior_suites(model: str, fresh: dict) -> dict:
    """Fold suites from the model's most-recent prior scorecard under the freshly-run ones, so a
    `--suite X` run doesn't drop the model's other suites from its card (and off the leaderboard,
    which shows one card per model). Fresh suites win on key collision. A carried suite whose
    transcript log no longer exists keeps its scores but drops the dangling `log` pointer (e.g.
    after `--force` wiped that date's logs)."""
    prior = latest_scorecard(model)
    if not prior:
        return fresh
    merged: dict[str, dict] = {}
    for cap, s in prior.get("suites", {}).items():
        if cap in fresh:
            continue
        s = dict(s)
        log = s.get("log")
        if log and not (REPO / log).exists():
            s.pop("log", None)
        merged[cap] = s
    merged.update(fresh)
    return merged


# --- scorecards -----------------------------------------------------------------------


def _slug(model: str) -> str:
    return model.replace("/", "_")


def write_scorecard(card: dict) -> list[Path]:
    EVALS.mkdir(parents=True, exist_ok=True)
    # Build names directly — model keys contain dots (qwen2.5), which Path.with_suffix mangles.
    stem = f"{_slug(card['model'])}-{card['date']}"
    jpath = EVALS / f"{stem}.json"
    jpath.write_text(json.dumps(card, indent=2) + "\n")

    op = card["operational"]
    lines = [
        f"# Eval — {card['model']} ({card['date']})",
        "",
        f"**Verdict: {VERDICT_EMOJI.get(card['verdict'], '')} {card['verdict']}** · "
        f"`{card.get('hf_repo', '')}`",
        "",
        "## Operational",
        f"- served: {op.get('served')}",
        f"- cold start: {op.get('cold_start_s')} s",
        f"- GPU used: {op.get('gpu_used_mib')} MiB",
        f"- TTFT: {op.get('ttft_s')} s",
        f"- decode tok/s: {op.get('decode_tok_s')}",
    ]
    if op.get("error"):
        lines.append(f"- error: {op['error']}")
    if card.get("usage"):
        u = card["usage"]
        cost = card.get("est_cost_usd")
        lines.append(
            f"- tokens: {u.get('input', 0):,} in / {u.get('output', 0):,} out"
            + (f" · est cost ${cost:.2f}" if cost is not None else "")
        )
    if card.get("judge_usage"):
        ju = card["judge_usage"]
        jc = card.get("judge_cost_usd")
        lines.append(
            f"- judge overhead: {ju.get('input', 0):,} in / {ju.get('output', 0):,} out"
            + (f" · ${jc:.2f}" if jc is not None else "")
        )
    for cap, s in card["suites"].items():
        lines += [
            "",
            f"## Suite: {cap} v{s.get('version', 1)} — "
            f"{s['passed']}/{s['total']} ({s['pass_rate']:.0%})",
        ]
        if "iteration_rate" in s:
            lines.append(
                f"_iteration (recovered after a failing test run): "
                f"{s['iteration_rate']:.0%}_"
            )
        if s.get("log"):
            lines.append(f"_Transcript: `{s['log']}` (open with `inspect view`)._")
        for c in s["cases"]:
            pts = c.get("score")
            frac = f" ({pts:.0%})" if (pts is not None and not c["passed"]) else ""
            lines.append(
                f"- {'✅' if c['passed'] else '❌'} `{c['name']}`{frac} — {c['detail']}"
            )
    mpath = EVALS / f"{stem}.md"
    mpath.write_text("\n".join(lines) + "\n")
    return [jpath, mpath]


def _latest_scorecards() -> list[dict]:
    cards: dict[str, dict] = {}
    for f in sorted(EVALS.glob("*-*.json")):
        if f.name.startswith("leaderboard"):
            continue
        try:
            c = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        prev = cards.get(c["model"])
        if prev is None or c.get("date", "") >= prev.get("date", ""):
            cards[c["model"]] = c
    return sorted(cards.values(), key=lambda c: c["model"])


def latest_scorecard(model: str) -> dict | None:
    return next((c for c in _latest_scorecards() if c["model"] == model), None)


def scorecard_current(model: str, needed_versions: dict[str, int]) -> bool:
    """True if the model's latest scorecard already covers every requested suite at its
    current version (the batch runner's resume check)."""
    card = latest_scorecard(model)
    if card is None:
        return False
    suites = card.get("suites", {})
    return all(
        cap in suites and suites[cap].get("version") == ver
        for cap, ver in needed_versions.items()
    )


# --- leaderboard -----------------------------------------------------------------------


def _row(card: dict, current_versions: dict[str, int] | None, cfg: dict) -> dict:
    op = card["operational"]
    suites = {}
    for cap, s in card["suites"].items():
        stale = bool(
            current_versions
            and cap in current_versions
            and s.get("version") != current_versions[cap]
        )
        suites[cap] = {"pass_rate": s["pass_rate"], "stale": stale}
    comp = composite(card, cfg, current_versions)
    return {
        "model": card["model"],
        "verdict": card["verdict"],
        "date": card["date"],
        "composite": comp["composite"] if comp else None,
        "speed_factor": comp["speed_factor"] if comp else None,
        "eligible": comp["eligible"] if comp else [],
        "gpu_mib": op.get("gpu_used_mib"),
        # v1 cards measured a single blended tokens_per_sec; fall back so old rows still show
        "tok_s": op.get("decode_tok_s", op.get("tokens_per_sec")),
        "ttft_s": op.get("ttft_s"),
        "cold_s": op.get("cold_start_s"),
        "est_cost_usd": card.get("est_cost_usd"),
        "suites": suites,
    }


_MEDALS = {0: "①", 1: "②", 2: "③"}


def _ranked(rows: list[dict]) -> list[dict]:
    """Sort by composite desc (unranked models after, alphabetical); attach medal ranks."""
    ranked = sorted(
        rows,
        key=lambda r: (r["composite"] is None, -(r["composite"] or 0), r["model"]),
    )
    place = 0
    for r in ranked:
        r["rank"] = None
        if r["composite"] is not None:
            r["rank"] = place + 1
            r["medal"] = _MEDALS.get(place, "")
            place += 1
        else:
            r["medal"] = ""
    return ranked


def _comp_cell(r: dict) -> str:
    if r["composite"] is None:
        return "—"
    return f"{r['medal']} {r['composite']:.2f}".strip()


def _cell(row: dict, cap: str) -> str:
    s = row["suites"].get(cap)
    if s is None:
        return "—"
    return f"{s['pass_rate']:.0%}{'†' if s['stale'] else ''}"


def _weights_note(cfg: dict) -> str:
    ws = ", ".join(f"{k} {v:.2f}" for k, v in cfg["weights"].items() if v > 0)
    judged = (
        "" if cfg["judge"].get("calibrated") else " · judged excluded until calibrated"
    )
    return (
        f"composite = speed_factor × weighted mean ({ws}); "
        f"speed floor {cfg['speed']['floor_tok_s']} / full {cfg['speed']['full_tok_s']} tok/s"
        f"{judged} — tune in eval-config.toml"
    )


def write_leaderboard(current_versions: dict[str, int] | None = None) -> list[Path]:
    cfg = load_config()
    rows = _ranked([_row(c, current_versions, cfg) for c in _latest_scorecards()])
    suite_keys = sorted({k for r in rows for k in r["suites"]})
    any_stale = any(s["stale"] for r in rows for s in r["suites"].values())

    jpath = EVALS / "leaderboard.json"
    jpath.write_text(
        json.dumps(
            {
                "rows": rows,
                "suites": suite_keys,
                "current_versions": current_versions or {},
                "config": {k: cfg[k] for k in ("weights", "speed", "verdict")},
            },
            indent=2,
        )
        + "\n"
    )

    hdr = [
        "rank",
        "model",
        "composite",
        "verdict",
        *suite_keys,
        "GPU MiB",
        "tok/s",
        "TTFT s",
        "cold s",
        "est $/run",
        "date",
    ]
    md = [
        "# kvllm eval leaderboard",
        "",
        "_Generated by `kvllm.evalrun`. Source: `leaderboard.json`. "
        "tok/s is decode rate (TTFT excluded)._",
        "",
        "| " + " | ".join(hdr) + " |",
        "|" + "---|" * len(hdr),
    ]
    for r in rows:
        cells = [
            str(r["rank"] or "—"),
            r["model"],
            _comp_cell(r),
            f"{VERDICT_EMOJI.get(r['verdict'], '')} {r['verdict']}",
        ]
        cells += [_cell(r, k) for k in suite_keys]
        cells += [
            str(r["gpu_mib"] or "—"),
            str(r["tok_s"] or "—"),
            str(r["ttft_s"] or "—"),
            str(r["cold_s"] or "—"),
            f"${r['est_cost_usd']:.2f}" if r.get("est_cost_usd") is not None else "—",
            r["date"],
        ]
        md.append("| " + " | ".join(cells) + " |")
    md += ["", f"_{_weights_note(cfg)}_"]
    if any_stale:
        md += ["", "† scored on an older suite version — re-run `just eval <key>`."]
    mpath = EVALS / "leaderboard.md"
    mpath.write_text("\n".join(md) + "\n")

    hpath = EVALS / "leaderboard.html"
    hpath.write_text(_html(rows, suite_keys, any_stale, cfg))
    return [jpath, mpath, hpath]


def _html(rows: list[dict], suite_keys: list[str], any_stale: bool, cfg: dict) -> str:
    head = [
        "rank",
        "model",
        "composite",
        "verdict",
        *suite_keys,
        "GPU MiB",
        "tok/s",
        "TTFT s",
        "cold s",
        "est $/run",
        "date",
    ]
    th = "".join(f"<th>{html.escape(h)}</th>" for h in head)
    trs = []
    for r in rows:
        cls = {"worth trying": "ok", "has issues": "warn", "skip": "bad"}.get(
            r["verdict"], ""
        )
        tds = [
            f"<td>{r['rank'] or '—'}</td>",
            f'<td class="m">{html.escape(r["model"])}</td>',
            f'<td class="m">{html.escape(_comp_cell(r))}</td>',
            f'<td class="{cls}">{VERDICT_EMOJI.get(r["verdict"], "")} '
            f"{html.escape(r['verdict'])}</td>",
        ]
        tds += [f"<td>{html.escape(_cell(r, k))}</td>" for k in suite_keys]
        tds += [
            f"<td>{r['gpu_mib'] or '—'}</td>",
            f"<td>{r['tok_s'] or '—'}</td>",
            f"<td>{r['ttft_s'] or '—'}</td>",
            f"<td>{r['cold_s'] or '—'}</td>",
            f"<td>{'$' + format(r['est_cost_usd'], '.2f') if r.get('est_cost_usd') is not None else '—'}</td>",
            f"<td>{html.escape(r['date'])}</td>",
        ]
        trs.append("<tr>" + "".join(tds) + "</tr>")
    stale_note = f'<div class="sub">{html.escape(_weights_note(cfg))}</div>'
    if any_stale:
        stale_note += (
            '<div class="sub">† scored on an older suite version — '
            "re-run <code>just eval</code>.</div>"
        )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>kvllm evals</title>
<style>
 :root {{ color-scheme: dark; }}
 body {{ font: 15px system-ui, sans-serif; background:#0f1115; color:#e6e6e6; margin:0; padding:24px; }}
 h1 {{ font-size:19px; }} .sub {{ color:#7b8494; font-size:13px; margin-bottom:16px; }}
 table {{ border-collapse:collapse; width:100%; }}
 th,td {{ padding:8px 12px; border-bottom:1px solid #232733; text-align:left; white-space:nowrap; }}
 th {{ color:#9aa4b2; font-weight:500; font-size:13px; }}
 td.m {{ font-weight:600; }}
 td.ok {{ color:#36c46a; }} td.warn {{ color:#e0a93b; }} td.bad {{ color:#c9484b; }}
 tr:hover td {{ background:#151823; }}
</style></head><body>
<h1>kvllm eval leaderboard</h1>
<div class="sub">Our own "worth trying / has issues" testing on kai (RTX 5090). Generated by kvllm.evalrun; tok/s is decode rate.</div>
<table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>
{stale_note}
</body></html>
"""


# --- models.toml write-back --------------------------------------------------------------


def update_registry(card: dict) -> Path | None:
    """Write tested / eval_verdict / eval_date back into the model's models.toml entry."""
    doc = tomlkit.parse(REGISTRY.read_text())
    models = doc.get("models", {})
    entry = models.get(card["model"])
    if entry is None:
        return None
    if not card.get("baseline"):
        # `tested` means "served on kai" — never true for API baselines
        entry["tested"] = bool(card["operational"].get("served"))
    entry["eval_verdict"] = card["verdict"]
    entry["eval_date"] = card["date"]
    if card.get("notes"):
        entry["eval_notes"] = card["notes"]
    elif "eval_notes" in entry:
        del entry["eval_notes"]  # clear a stale failure note when the model now passes
    REGISTRY.write_text(tomlkit.dumps(doc))
    return REGISTRY


def refresh_verdicts(current_versions: dict[str, int] | None = None) -> list[str]:
    """Recompute every latest scorecard's verdict under the current eval-config.toml (verdicts
    are derived from the composite, so re-weighting can change them). Rewrites the scorecard +
    models.toml for any model whose verdict changed; returns the changed model keys."""
    cfg = load_config()
    changed = []
    for card in _latest_scorecards():
        if card.get("baseline"):
            continue  # baselines keep the "baseline" verdict — kai thresholds don't apply
        op = card.get("operational", {})
        new = verdict(
            op.get("served", False),
            card.get("suites", {}),
            op.get("decode_tok_s"),
            cfg=cfg,
            current_versions=current_versions,
        )
        if new != card.get("verdict"):
            changed.append(f"{card['model']}: {card.get('verdict')} → {new}")
            card["verdict"] = new
            write_scorecard(card)
            update_registry(card)
    return changed


def write_all(card: dict, current_versions: dict[str, int] | None = None) -> list[Path]:
    paths = write_scorecard(card)
    paths += write_leaderboard(current_versions)
    reg = update_registry(card)
    if reg:
        paths.append(reg)
    return paths
