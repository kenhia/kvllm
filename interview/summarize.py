"""Roll up interview runs into the tables the write-up needs.

    uv run python -m interview.summarize [--dir model-research/ra-interview/interview]

For every per-scenario transcript file under each model directory: the cell histogram per
(model, prompt, tag) with mean turns/calls and the sprint-22 counters (floor refusals,
effort requests), a scenario × configuration matrix of the action each attempt took
(truth in the first column), and — where rungs carry a `family` — the urgency-gradient
view, one family at a time in severity order. Reads only; nothing here judges.

    --only <substr>   keep configurations whose model/prompt/tag contains the substring
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT = REPO / "model-research" / "ra-interview" / "interview"
CELLS = [
    "correct",
    "wrong-answer",
    "useless",
    "wrong-urgency",
    "missed",
    "dangerous",
    "no-verdict",
]
SHORT = {"handle": "H", "escalate_now": "NOW", "handoff": "HO", "-": "·"}


def load(root: Path) -> list[dict]:
    """One row per attempt, from the per-scenario files (the source of truth — a re-run
    of one rung replaces that rung's file, and superseded files are moved out)."""
    runs = []
    for model_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for f in sorted(model_dir.glob("*.json")):
            if f.name.startswith("summary-"):
                continue
            d = json.loads(f.read_text())
            if "scenario" not in d or "attempts" not in d:
                continue
            # <scenario>-<prompt>[-<tag>]-<YYYY-MM-DD-HHMMSS>.json ; scenario and prompt are known
            label = f.stem[len(d["scenario"]) + 1 :].rsplit("-", 4)[0]
            pp = label.split("-")
            prompts = ("p0", "p1", "p2", "p3")
            prompt = "-".join(pp[:2]) if pp[0] in prompts else pp[0]
            tag = "-".join(pp[2:]) if pp[0] in prompts else "-".join(pp[1:])
            for i, a in enumerate(d["attempts"]):
                r = a.get("report") or {}
                runs.append(
                    {
                        "scenario": d["scenario"],
                        "attempt": i + 1,
                        "action": r.get("action", "-"),
                        "truth": d["truth"]["action"],
                        **a["judge"],
                        "turns": a["turns"],
                        "tool_calls": a["tool_calls"],
                        "tokens_out": a["tokens_out"],
                        "wall_s": a["wall_s"],
                        "error": a.get("error"),
                        "floor_refusals": a.get("floor_refusals", 0),
                        "effort_turn": a.get("effort_turn"),
                        "family": d["truth"].get("family"),
                        "variant": d["truth"].get("variant"),
                        "order": d["truth"].get("order", 0),
                        "effort_worth_it": d["truth"].get("effort_worth_it"),
                        "model": model_dir.name,
                        "prompt": prompt,
                        "tag": tag,
                        "file": f.name,
                    }
                )
    return runs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="interview.summarize", description=__doc__)
    p.add_argument("--dir", default=str(DEFAULT))
    p.add_argument("--only", default=None)
    a = p.parse_args(argv)
    runs = load(Path(a.dir))
    if a.only:
        runs = [r for r in runs if a.only in f"{r['model']}/{r['prompt']}/{r['tag']}"]
    if not runs:
        print("no summaries found")
        return 0
    configs = sorted({(r["model"], r["prompt"], r["tag"]) for r in runs})
    print("## cells per configuration\n")
    print(
        "| model | prompt | config | n | "
        + " | ".join(CELLS)
        + " | mean conf | turns | calls | refusals | effort asks |"
    )
    print("|---|---|---|---|" + "---|" * len(CELLS) + "---|---|---|---|---|")
    for m, pr, tg in configs:
        rs = [r for r in runs if (r["model"], r["prompt"], r["tag"]) == (m, pr, tg)]
        c = Counter(r["cell"] for r in rs)
        confs = [
            r["confidence"] for r in rs if isinstance(r.get("confidence"), (int, float))
        ]
        mean = f"{sum(confs) / len(confs):.2f}" if confs else "-"
        turns = sum(r["turns"] for r in rs) / len(rs)
        calls = sum(r["tool_calls"] for r in rs) / len(rs)
        refusals = sum(r["floor_refusals"] or 0 for r in rs)
        asks = sum(1 for r in rs if r["effort_turn"])
        print(
            f"| {m} | {pr} | {tg or '-'} | {len(rs)} | "
            + " | ".join(str(c.get(k, 0)) for k in CELLS)
            + f" | {mean} | {turns:.1f} | {calls:.1f} | {refusals} | {asks} |"
        )
    print(
        "\n## action per scenario (truth first; H=handle NOW=escalate_now HO=handoff, * = correct cell)\n"
    )
    scen = sorted({r["scenario"] for r in runs})
    truth = {r["scenario"]: r["truth"] for r in runs}
    cols = [
        f"{m.split('-')[0]}/{pr.split('-')[0]}/{tg or 'as-is'}" for m, pr, tg in configs
    ]
    print("| scenario | truth | " + " | ".join(cols) + " |")
    print("|---|---|" + "---|" * len(cols))
    by = defaultdict(list)
    for r in runs:
        by[(r["scenario"], r["model"], r["prompt"], r["tag"])].append(r)
    for s in scen:
        cells = []
        for m, pr, tg in configs:
            rs = by.get((s, m, pr, tg), [])
            cells.append(
                " ".join(
                    SHORT.get(r["action"], r["action"])
                    + ("*" if r["cell"] == "correct" else "")
                    for r in rs
                )
                or "·"
            )
        print(f"| {s} | {SHORT[truth[s]]} | " + " | ".join(cells) + " |")

    fam = {
        (r["family"], r["order"], r["scenario"], r["variant"])
        for r in runs
        if r["family"]
    }
    if fam:
        print(
            "\n## the urgency gradient (families in severity order; same key as above)\n"
        )
        print("| family | variant | rung | truth | " + " | ".join(cols) + " |")
        print("|---|---|---|---|" + "---|" * len(cols))
        for family, order, s, variant in sorted(fam):
            cells = []
            for m, pr, tg in configs:
                rs = by.get((s, m, pr, tg), [])
                cells.append(
                    " ".join(
                        SHORT.get(r["action"], r["action"])
                        + ("*" if r["cell"] == "correct" else "")
                        for r in rs
                    )
                    or "·"
                )
            print(
                f"| {family} | {variant} | {s} | {SHORT[truth[s]]} | "
                + " | ".join(cells)
                + " |"
            )

    eff_cfgs = sorted(
        {(r["model"], r["prompt"], r["tag"]) for r in runs if "effort" in r["tag"]}
    )
    if eff_cfgs:
        print(
            "\n## choose-your-own-effort (asked / attempts, by whether the rung was labelled worth it)\n"
        )
        print(
            "| model | prompt | config | worth it: asked/n | correct | not worth it: asked/n | correct |"
        )
        print("|---|---|---|---|---|---|---|")
        for m, pr, tg in eff_cfgs:
            rs = [r for r in runs if (r["model"], r["prompt"], r["tag"]) == (m, pr, tg)]
            w = [r for r in rs if r["effort_worth_it"]]
            nw = [r for r in rs if not r["effort_worth_it"]]

            def cell(group):
                asked = sum(1 for r in group if r["effort_turn"])
                ok = sum(1 for r in group if r["cell"] == "correct")
                return f"{asked}/{len(group)}", f"{ok}/{len(group)}"

            wa, wc = cell(w)
            na, nc = cell(nw)
            print(f"| {m} | {pr} | {tg} | {wa} | {wc} | {na} | {nc} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
