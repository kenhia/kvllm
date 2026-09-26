"""Re-judge stored interview transcripts against the current scenario truth — no model.

    uv run python -m interview.rescore [--dir model-research/ra-interview/interview] [--write]

A truth change (a rung's answer set, WI 2024) should move the recorded cells without
spending card time: every attempt keeps its `report`, so `judge()` can simply run again.
Dry run by default — prints each attempt whose cell would change. `--write` rewrites only
the files that change: `truth` becomes the current truth, each attempt's `judge` is
replaced, and a `rescored` list records the date and the cells before, so the original
reading stays in the file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from interview.run import judge

REPO = Path(__file__).resolve().parent.parent
DEFAULT = REPO / "model-research" / "ra-interview" / "interview"
SCENARIOS = Path(__file__).resolve().parent / "scenarios"


def rescore(doc: dict, truth: dict, when: str) -> list[tuple[int, str, str]]:
    """Re-judge one transcript in place; returns (attempt, before, after) per changed cell.
    Leaves `doc` untouched when nothing changes."""
    judged = [judge(a.get("report"), truth) for a in doc["attempts"]]
    changes = [
        (i + 1, a["judge"]["cell"], j["cell"])
        for i, (a, j) in enumerate(zip(doc["attempts"], judged))
        if a["judge"]["cell"] != j["cell"]
    ]
    if changes:
        doc.setdefault("rescored", []).append(
            {"on": when, "before": [a["judge"]["cell"] for a in doc["attempts"]]}
        )
        doc["truth"] = truth
        for a, j in zip(doc["attempts"], judged):
            a["judge"] = j
    return changes


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="interview.rescore", description=__doc__)
    p.add_argument("--dir", default=str(DEFAULT))
    p.add_argument("--write", action="store_true")
    a = p.parse_args(argv)
    truths = {
        f.stem: json.loads(f.read_text())["truth"] for f in SCENARIOS.glob("*.json")
    }
    when = dt.date.today().isoformat()
    n = 0
    for f in sorted(Path(a.dir).rglob("*.json")):
        if f.name.startswith("summary-"):
            continue
        doc = json.loads(f.read_text())
        if "attempts" not in doc or doc.get("scenario") not in truths:
            continue
        changes = rescore(doc, truths[doc["scenario"]], when)
        for i, before, after in changes:
            print(f"{f.parent.name}/{f.name} #{i}: {before} → {after}")
        if changes and a.write:
            f.write_text(json.dumps(doc, indent=1))
        n += len(changes)
    print(f"[rescore] {n} cell(s) {'rewritten' if a.write else 'would change'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
