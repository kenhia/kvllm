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
from pathlib import Path

import tomlkit

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "docs" / "model-research" / "evals"
REGISTRY = REPO / "models.toml"

VERDICT_EMOJI = {"worth trying": "✅", "has issues": "⚠️", "skip": "❌"}

PASS_THRESHOLD = 0.8
MIN_DECODE_TOK_S = 10.0  # below this a model "works" but is too slow to be practical


def verdict(served: bool, suites: dict, decode_tok_s: float | None = None) -> str:
    """worth trying / has issues / skip — same thresholds as v1 (weights are Phase 3)."""
    if not served:
        return "skip"
    rates = [s.get("pass_rate", 0.0) for s in suites.values()]
    base = (
        "worth trying"
        if (not suites or all(r >= PASS_THRESHOLD for r in rates))
        else "has issues"
    )
    if (
        base == "worth trying"
        and decode_tok_s is not None
        and decode_tok_s < MIN_DECODE_TOK_S
    ):
        return "has issues"
    return base


# --- inspect log → suite result ---------------------------------------------------------


def suite_from_log(log_path: str | Path, version: int) -> dict:
    """Reduce one Inspect .eval log to the scorecard suite shape (per-case pass/detail)."""
    from inspect_ai.log import read_eval_log  # heavy import; only when aggregating

    log = read_eval_log(str(log_path))
    cases = []
    for sample in log.samples or []:
        score = next(iter((sample.scores or {}).values()), None)
        passed = bool(score and score.value == "C")
        cases.append(
            {
                "name": str(sample.id),
                "passed": passed,
                "detail": (score.explanation if score else "no score recorded") or "",
            }
        )
    n = len(cases)
    passed_n = sum(c["passed"] for c in cases)
    result = {
        "version": version,
        "passed": passed_n,
        "total": n,
        "pass_rate": round(passed_n / n, 2) if n else 0.0,
        "cases": cases,
        "log": str(Path(log_path).resolve().relative_to(REPO)),
    }
    if log.status != "success":
        result["error"] = f"inspect run status: {log.status}"
    return result


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
    for cap, s in card["suites"].items():
        lines += [
            "",
            f"## Suite: {cap} v{s.get('version', 1)} — "
            f"{s['passed']}/{s['total']} ({s['pass_rate']:.0%})",
        ]
        if s.get("log"):
            lines.append(f"_Transcript: `{s['log']}` (open with `inspect view`)._")
        for c in s["cases"]:
            lines.append(
                f"- {'✅' if c['passed'] else '❌'} `{c['name']}` — {c['detail']}"
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


def _row(card: dict, current_versions: dict[str, int] | None) -> dict:
    op = card["operational"]
    suites = {}
    for cap, s in card["suites"].items():
        stale = bool(
            current_versions
            and cap in current_versions
            and s.get("version") != current_versions[cap]
        )
        suites[cap] = {"pass_rate": s["pass_rate"], "stale": stale}
    return {
        "model": card["model"],
        "verdict": card["verdict"],
        "date": card["date"],
        "gpu_mib": op.get("gpu_used_mib"),
        # v1 cards measured a single blended tokens_per_sec; fall back so old rows still show
        "tok_s": op.get("decode_tok_s", op.get("tokens_per_sec")),
        "ttft_s": op.get("ttft_s"),
        "cold_s": op.get("cold_start_s"),
        "suites": suites,
    }


def _cell(row: dict, cap: str) -> str:
    s = row["suites"].get(cap)
    if s is None:
        return "—"
    return f"{s['pass_rate']:.0%}{'†' if s['stale'] else ''}"


def write_leaderboard(current_versions: dict[str, int] | None = None) -> list[Path]:
    rows = [_row(c, current_versions) for c in _latest_scorecards()]
    suite_keys = sorted({k for r in rows for k in r["suites"]})
    any_stale = any(s["stale"] for r in rows for s in r["suites"].values())

    jpath = EVALS / "leaderboard.json"
    jpath.write_text(
        json.dumps(
            {
                "rows": rows,
                "suites": suite_keys,
                "current_versions": current_versions or {},
            },
            indent=2,
        )
        + "\n"
    )

    hdr = [
        "model",
        "verdict",
        *suite_keys,
        "GPU MiB",
        "tok/s",
        "TTFT s",
        "cold s",
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
        cells = [r["model"], f"{VERDICT_EMOJI.get(r['verdict'], '')} {r['verdict']}"]
        cells += [_cell(r, k) for k in suite_keys]
        cells += [
            str(r["gpu_mib"] or "—"),
            str(r["tok_s"] or "—"),
            str(r["ttft_s"] or "—"),
            str(r["cold_s"] or "—"),
            r["date"],
        ]
        md.append("| " + " | ".join(cells) + " |")
    if any_stale:
        md += ["", "† scored on an older suite version — re-run `just eval <key>`."]
    mpath = EVALS / "leaderboard.md"
    mpath.write_text("\n".join(md) + "\n")

    hpath = EVALS / "leaderboard.html"
    hpath.write_text(_html(rows, suite_keys, any_stale))
    return [jpath, mpath, hpath]


def _html(rows: list[dict], suite_keys: list[str], any_stale: bool) -> str:
    head = [
        "model",
        "verdict",
        *suite_keys,
        "GPU MiB",
        "tok/s",
        "TTFT s",
        "cold s",
        "date",
    ]
    th = "".join(f"<th>{html.escape(h)}</th>" for h in head)
    trs = []
    for r in rows:
        cls = {"worth trying": "ok", "has issues": "warn", "skip": "bad"}.get(
            r["verdict"], ""
        )
        tds = [
            f'<td class="m">{html.escape(r["model"])}</td>',
            f'<td class="{cls}">{VERDICT_EMOJI.get(r["verdict"], "")} '
            f"{html.escape(r['verdict'])}</td>",
        ]
        tds += [f"<td>{html.escape(_cell(r, k))}</td>" for k in suite_keys]
        tds += [
            f"<td>{r['gpu_mib'] or '—'}</td>",
            f"<td>{r['tok_s'] or '—'}</td>",
            f"<td>{r['ttft_s'] or '—'}</td>",
            f"<td>{r['cold_s'] or '—'}</td>",
            f"<td>{html.escape(r['date'])}</td>",
        ]
        trs.append("<tr>" + "".join(tds) + "</tr>")
    stale_note = (
        '<div class="sub">† scored on an older suite version — re-run <code>just eval</code>.</div>'
        if any_stale
        else ""
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
    entry["tested"] = bool(card["operational"].get("served"))
    entry["eval_verdict"] = card["verdict"]
    entry["eval_date"] = card["date"]
    if card.get("notes"):
        entry["eval_notes"] = card["notes"]
    elif "eval_notes" in entry:
        del entry["eval_notes"]  # clear a stale failure note when the model now passes
    REGISTRY.write_text(tomlkit.dumps(doc))
    return REGISTRY


def write_all(card: dict, current_versions: dict[str, int] | None = None) -> list[Path]:
    paths = write_scorecard(card)
    paths += write_leaderboard(current_versions)
    reg = update_registry(card)
    if reg:
        paths.append(reg)
    return paths
