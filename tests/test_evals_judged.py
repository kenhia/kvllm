"""Unit tests for the judged suite's pure functions (evals/judged.py) — no live judge."""

from __future__ import annotations

import json

from evals.judged import JTASKS, mechanical_check, parse_judge_json

# --- mechanical_check -------------------------------------------------------------------


def test_bullets3_pass():
    cap, v = mechanical_check("bullets3", "- a\n- b\n- c")
    assert cap == 10 and v == []


def test_bullets3_wrong_count_caps():
    cap, v = mechanical_check("bullets3", "- a\n- b")
    assert cap == 4 and "found 2" in v[0]


def test_bullets3_numbered_style_counts():
    cap, _ = mechanical_check("bullets3", "1. a\n2. b\n3. c")
    assert cap == 10


def test_json4keys_valid():
    ans = json.dumps(
        {
            "host": "kubsdb",
            "status": "degraded",
            "failed_units": ["postgresql", "nightly-backup"],
            "disk_free_gb": 42,
        }
    )
    assert mechanical_check("json4keys", ans) == (10, [])


def test_json4keys_fenced_tolerated():
    ans = '```json\n{"host": "h", "status": "s", "failed_units": [], "disk_free_gb": 1}\n```'
    cap, v = mechanical_check("json4keys", ans)
    assert cap == 10 and v == []


def test_json4keys_unparseable_is_zero():
    cap, v = mechanical_check("json4keys", "The host is kubsdb and it is degraded.")
    assert cap == 0 and "not parseable" in v[0]


def test_json4keys_wrong_keys_capped():
    cap, v = mechanical_check("json4keys", '{"hostname": "x", "status": "y"}')
    assert cap == 2 and "keys" in v[0]


def test_list5x8_pass():
    ans = "\n".join(f"{i}. check thing {i}" for i in range(1, 6))
    assert mechanical_check("list5x8", ans) == (10, [])


def test_list5x8_wrong_count():
    cap, v = mechanical_check("list5x8", "1. a\n2. b")
    assert cap == 4 and "found 2" in v[0]


def test_list5x8_too_long_item():
    ans = "\n".join(
        ["1. short one", "2. ok", "3. fine", "4. good", "5. " + "word " * 12]
    )
    cap, v = mechanical_check("list5x8", ans)
    assert cap == 4 and "over 8 words" in v[-1]


def test_no_mech_key_never_caps():
    assert mechanical_check(None, "anything") == (10, [])


# --- parse_judge_json --------------------------------------------------------------------


def test_parse_judge_clean():
    out = parse_judge_json('{"score": 8, "rationale": "good", "violations": []}')
    assert out == {"score": 8.0, "rationale": "good", "violations": []}


def test_parse_judge_fenced_and_prose():
    text = 'Here is my grade:\n```json\n{"score": 3, "rationale": "meh", "violations": ["x"]}\n```'
    out = parse_judge_json(text)
    assert out["score"] == 3.0 and out["violations"] == ["x"]


def test_parse_judge_clamps_range():
    assert parse_judge_json('{"score": 15, "rationale": ""}')["score"] == 10.0
    assert parse_judge_json('{"score": -2, "rationale": ""}')["score"] == 0.0


def test_parse_judge_garbage_none():
    assert parse_judge_json("I think it deserves an 8.") is None
    assert parse_judge_json('{"rationale": "no score"}') is None
    assert parse_judge_json("") is None


# --- manifest sanity ----------------------------------------------------------------------


def test_jtasks_manifest():
    assert len(JTASKS) == 6
    names = [t.name for t in JTASKS]
    assert len(set(names)) == 6
    for t in JTASKS:
        assert t.prompt and t.rubric and t.auto_zero
        if t.mech:
            assert t.mech in ("bullets3", "json4keys", "list5x8")
