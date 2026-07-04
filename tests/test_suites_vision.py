"""Vision suite unit tests — manifest, fact matching, image fixtures (no model/GPU)."""

from __future__ import annotations

from suites.vision import ASSETS, VERSION, VTASKS, fact_score


def test_manifest_fifteen_unique_tasks_v2():
    assert VERSION == 2
    assert len(VTASKS) == 15
    assert len({t.name for t in VTASKS}) == 15
    for t in VTASKS:
        assert t.groups, f"{t.name} has no fact groups"


def test_all_fixture_images_exist():
    for t in VTASKS:
        assert (ASSETS / t.image).is_file(), t.image


def test_fact_score_all_groups_case_insensitive():
    frac, missing = fact_score([["/var"], ["87"]], "It's /VAR at 87% usage.")
    assert frac == 1.0 and missing == []


def test_fact_score_partial_credit_and_missing_render():
    frac, missing = fact_score([["/var"], ["87"]], "/var looks high")
    assert frac == 0.5
    assert missing == ["87"]


def test_digit_alternatives_require_word_boundary():
    frac, _ = fact_score([["20"]], "it uses 205 GB")
    assert frac == 0.0
    frac, _ = fact_score([["20"]], "est VRAM is 20 GB")
    assert frac == 1.0
    frac, _ = fact_score([["3"]], "13 warnings")
    assert frac == 0.0


def test_alternatives_any_of_matches():
    frac, _ = fact_score([["oom", "out of memory"]], "kernel reported Out of Memory")
    assert frac == 1.0


def test_v4_accepts_device_or_mount():
    from suites.vision import VTASKS

    t = next(t for t in VTASKS if t.name == "v4-terminal-df")
    frac, _ = fact_score(t.groups, "/dev/nvme1n1p1 at 91%")
    assert frac == 1.0
    frac, _ = fact_score(t.groups, "/data is at 91%")
    assert frac == 1.0
