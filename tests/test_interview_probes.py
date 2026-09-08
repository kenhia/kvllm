"""interview.longctx generator and interview.effort checks (pure; no model)."""

from __future__ import annotations

import json
from pathlib import Path

from interview.effort import PROBES, check
from interview.longctx import MANIFEST, Day, cap_targets, score


def test_day_plants_every_fact_and_questions_find_them():
    day = Day(7)
    blocks = day.build(40)
    text = "\n\n".join(blocks)
    qs = day.questions()
    assert [q["id"] for q in qs] == [
        "needle",
        "absence",
        "contradiction",
        "count",
        "order",
    ]
    # needle: user, ip, time all literally present
    assert f"Accepted publickey for ken from 100.64.0.{day.needle_ip}" in text
    # absence: kbeacon listens on kubsdb and is in no manifest/WI block
    assert f'"{day.absent_svc}"' in text and "[services.kbeacon]" not in text
    # contradiction: kmon's live port differs from the manifest's
    assert (
        f"0.0.0.0:{day.contra_live}" in text and day.contra_live != MANIFEST["kmon"][1]
    )
    # count: exactly one df block per host, high ones match disk_hosts
    dfs = [b for b in blocks if b.startswith("[tool_result: df -h /]")]
    assert len(dfs) == 6
    high = {
        b.split("(host ")[1].split(")")[0]
        for b in dfs
        if int(b.rsplit("  ", 1)[-1].split("%")[0]) > 80
    }
    assert high == set(day.disk_hosts)
    # order: both events present with the expected times
    assert qs[4]["expect"][1] in text and qs[4]["expect"][2] in text


def test_day_is_deterministic_per_seed():
    assert Day(3).build(20) == Day(3).build(20)
    assert Day(3).questions() == Day(3).questions()
    assert Day(3).build(20) != Day(4).build(20)


def test_score_counts_expectations():
    assert score(
        "ken logged in from 100.64.0.5 at 03:10:11", ["ken", "100.64.0.5", "03:10:11"]
    ) == (3, 3)
    assert score("no idea", ["ken"]) == (0, 1)


def test_effort_checks():
    probes = {p["id"]: p for p in json.loads(Path(PROBES).read_text())["probes"]}
    ok, _ = check(
        "1. replicate\n2. cutover\n3. rollback: promote old primary",
        probes["plan-migration"]["check"],
    )
    assert ok
    ok, note = check(
        "\n".join(f"{i}. step" for i in range(1, 9)) + " rollback",
        probes["plan-migration"]["check"],
    )
    assert not ok and "8 steps" in note
    assert check(
        "It restarts only when it fails, not on clean stops.",
        probes["explain-config"]["check"],
    )[0]
    assert not check("It always restarts.", probes["explain-config"]["check"])[0]
    assert check("a=3.9 b=118000 c=79000", probes["kv-arith"]["check"])[0]
    assert not check("a=3.9 b=200000 c=79000", probes["kv-arith"]["check"])[0]
    assert check(
        '{"host": "kubsdb", "status": "degraded", "services": [], "disk_free_gb": 42}',
        probes["constrained-json"]["check"],
    )[0]
    assert not check("", probes["constrained-json"]["check"])[0]


def test_cap_targets_fits_the_window():
    # 65536 window, 6144 answer, 768 margin → 58624 / 1.05 ≈ 55832 usable target
    assert cap_targets([8192, 32768, 61440], 65536, 6144) == [8192, 32768, 55832]
    assert cap_targets([61440, 65536], 65536, 6144) == [55832]
    assert cap_targets([8192], None, 6144) == [8192]
