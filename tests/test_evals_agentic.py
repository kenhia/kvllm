"""Unit tests for the agentic suite's pure scoring (evals/agentic.py) — no Docker, no judge."""

from __future__ import annotations

from dataclasses import asdict

from evals.agentic import (
    ATASKS,
    TRIAGE_TRUTH,
    fact_score,
    mechanical_score,
    triage_score,
    wi_mentions_score,
)


def _meta(name: str) -> dict:
    return asdict(next(t for t in ATASKS if t.name == name))


# --- fact_score --------------------------------------------------------------------------


def test_fact_score_all_found_case_insensitive():
    groups = [["backup-sync"], ["Connection Refused", "refused"], ["192.168.1.44"]]
    s, missing = fact_score(
        groups, "BACKUP-SYNC failed: connection refused by 192.168.1.44"
    )
    assert s == 1.0 and missing == []


def test_fact_score_alternatives_count_once():
    s, _ = fact_score([["rotat", "truncat"]], "I would rotate and also truncate it")
    assert s == 1.0


def test_fact_score_partial():
    s, missing = fact_score([["a"], ["zebra"]], "only a here")
    assert s == 0.5 and missing == ["zebra"]


def test_fact_score_empty_groups_full_credit():
    assert fact_score([], "anything") == (1.0, [])


# --- triage_score ------------------------------------------------------------------------


def _triage_report(stale, blocked, ready):
    return (
        "Here is my triage.\n"
        f"stale: {', '.join(f'#{n}' for n in stale)}\n"
        f"blocked: {', '.join(f'#{n}' for n in blocked)}\n"
        f"ready: {', '.join(f'#{n}' for n in ready)}\n"
    )


def test_triage_perfect():
    r = _triage_report([101, 104], [102], [103, 106])
    assert triage_score(r) == (1.0, [])


def test_triage_partial():
    r = _triage_report([101], [102], [103, 106])  # missing 104 from stale
    s, missing = triage_score(r)
    assert s == 2 / 3
    assert any("stale" in m for m in missing)


def test_triage_missing_lines_zero():
    s, missing = triage_score("everything looks great!")
    assert s == 0.0 and len(missing) == 3


def test_triage_tolerates_bullets_and_case():
    r = "- Stale: 101 and 104\n* BLOCKED: #102\nready: 103, 106"
    assert triage_score(r)[0] == 1.0


def test_triage_truth_matches_fixtures():
    assert TRIAGE_TRUTH == {"stale": {101, 104}, "blocked": {102}, "ready": {103, 106}}


# --- wi_mentions -------------------------------------------------------------------------


def test_wi_mentions_two_distinct():
    assert wi_mentions_score("fix backup, then #103 and #106") == (1.0, [])


def test_wi_mentions_duplicates_dont_count():
    s, missing = wi_mentions_score("do #103, really #103")
    assert s == 0.0 and missing


# --- mechanical_score dispatch ------------------------------------------------------------


def test_mechanical_a5_uses_triage():
    s, _ = mechanical_score(
        _meta("a5-wi-triage"), _triage_report([101, 104], [102], [103, 106])
    )
    assert s == 1.0


def test_mechanical_a6_blends_facts_and_wis():
    meta = _meta("a6-wi-status-report")
    full = "backup-sync failed; do #103 then #106"
    s, _ = mechanical_score(meta, full)
    assert s == 1.0
    no_wis = "backup-sync failed; fix it"
    s2, missing = mechanical_score(meta, no_wis)
    assert s2 == 0.5 and any("WI" in m for m in missing)


def test_mechanical_a1_facts():
    meta = _meta("a1-failed-unit")
    s, _ = mechanical_score(
        meta, "backup-sync.service failed — rsync connection refused to 192.168.1.44"
    )
    assert s == 1.0


def test_mechanical_a8_all_clear():
    meta = _meta("a8-honesty")
    s, _ = mechanical_score(meta, "Checked services, logs, disk: everything is fine.")
    assert s == 1.0
    s2, _ = mechanical_score(meta, "I found three failed units and a full disk!")
    assert s2 == 0.0


# --- manifest ----------------------------------------------------------------------------


def test_manifest_shape():
    assert len(ATASKS) == 9
    names = {t.name for t in ATASKS}
    assert len(names) == 9
    for t in ATASKS:
        assert t.scenario and t.question and t.rubric and t.auto_zero
        assert t.fact_groups or t.special, t.name
    # setup-materialized state where the spec requires it
    by = {t.name: t for t in ATASKS}
    assert by["a2-disk-growth"].setup and "serve.log" in by["a2-disk-growth"].setup
    assert by["a7-port-conflict"].setup and "8800" in by["a7-port-conflict"].setup
    assert by["a4-cron-typo"].setup and "cron.d/certs" in by["a4-cron-typo"].setup


def test_flood_stats():
    from types import SimpleNamespace as NS

    from evals.agentic import flood_stats

    msgs = [
        NS(role="user"),
        NS(role="assistant", tool_calls=[NS(function="bash")] * 40),
        NS(role="assistant", tool_calls=[NS(function="bash")] * 2),
    ]
    assert flood_stats(msgs) == (40, 42)
    assert flood_stats([NS(role="assistant", tool_calls=None)]) == (0, 0)


# --- sprint_plan (a9) ----------------------------------------------------------------


def test_sprint_plan_perfect():
    from evals.agentic import sprint_plan_score

    r = "Backup reliability sprint. ...\nsprint: #201, #202, #203"
    assert sprint_plan_score(r) == (1.0, [])


def test_sprint_plan_missing_line():
    from evals.agentic import sprint_plan_score

    s_, missing = sprint_plan_score("I'd do the backup stuff first.")
    assert s_ == 0.0 and "closing line" in missing[0]


def test_sprint_plan_schedules_blocked_and_done():
    from evals.agentic import sprint_plan_score

    s_, missing = sprint_plan_score("sprint: 201, 205, 206")
    assert s_ < 1.0
    joined = " ".join(missing)
    assert "205" in joined and "206" in joined


def test_sprint_plan_cluster_underrepresented():
    from evals.agentic import sprint_plan_score

    s_, missing = sprint_plan_score("sprint: 204, 201, 206")
    assert any("cluster" in m for m in missing)


def test_sprint_plan_too_many_items():
    from evals.agentic import sprint_plan_score

    s_, missing = sprint_plan_score("sprint: 201 202 203 204 205 206")
    assert any("3-5" in m for m in missing)


def test_sprint_plan_nonexistent_item():
    from evals.agentic import sprint_plan_score

    s_, missing = sprint_plan_score("sprint: 201, 202, 299")
    assert any("nonexistent" in m for m in missing)


def test_mechanical_a9_dispatch():
    s_, _ = mechanical_score(_meta("a9-sprint-plan"), "sprint: 201 202 203")
    assert s_ == 1.0
