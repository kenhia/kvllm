"""Self-test the vision suite WITHOUT a model, GPU, or Docker: every fixture image must
exist and load; every task's reference answer must score 1.0 through the real fact scorer;
and a wrong-but-plausible answer must NOT score 1.0 (guards against vacuous groups).
Run: `just test-vision-suite`."""

from __future__ import annotations

import sys

from PIL import Image

from suites.vision import ASSETS, VTASKS, fact_score

# Reference answer + an adversarial near-miss per task.
REFERENCE = {
    "v1-dashboard-down": (
        "backup-sync is DOWN; everything else is UP.",
        "postgresql is down",
    ),
    "v2-gauge-disk": ("/var is nearly full at 87%.", "/data is at 12%"),
    "v3-chart-peak": ("Peak was Thursday at about 83 °C.", "peak Friday at 68"),
    "v4-terminal-df": ("/data is fullest at 91% use.", "/ at 36%"),
    "v5-journal-error": (
        "The kernel OOM-killed postgres (out of memory); postgresql restarted.",
        "a cron job ran healthping",
    ),
    "v6-table-registry": ("20 GB", "205 GB total"),
    "v7-count-warnings": ("3 checks show WARN.", "13 warnings"),
    "v8-diagram-backup": ("Backups go to nas-01.", "backups go to kubsdb"),
    "v9-render-broken": (
        "No — the third box's text ('integration test suite') overflows outside its border.",
        "the diagram renders correctly",
    ),
    "v10-render-clean": (
        "Yes, the diagram renders correctly; no defects.",
        "the deploy box text overflows its border",
    ),
    "p1-animal": (
        "A corgi (dog) wearing a flamingo-print bandana.",
        "a cat wearing a collar",
    ),
    "p2-hardware": (
        "A Raspberry Pi with a PoE HAT, connected to a network via Ethernet cable.",
        "a laptop with no cables attached",
    ),
    "p3-tools": ("A digital caliper and a steel ruler.", "a tape measure"),
    "p4-count-people": ("0 — no people are visible.", "2 people"),
    "p5-activity": (
        "Road cycling (a triathlon leg); 2 riders visible.",
        "a running race with 5 runners",
    ),
}


def main() -> int:
    ok = True
    for t in VTASKS:
        path = ASSETS / t.image
        img_ok = path.is_file()
        if img_ok:
            with Image.open(path) as im:
                img_ok = im.size[0] >= 250  # p5 is a natively-small photo; the bar catches broken/empty files
        good, wrong = REFERENCE[t.name]
        gfrac, _ = fact_score(t.groups, good)
        wfrac, _ = fact_score(t.groups, wrong)
        passed = img_ok and gfrac == 1.0 and wfrac < 1.0
        ok = ok and passed
        print(
            f"  {'OK ' if passed else 'BAD'} {t.name}: image={'✓' if img_ok else '✗'} "
            f"reference={gfrac:.0%} adversarial={wfrac:.0%} (must be <100%)"
        )
    print(f"\nvision self-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
