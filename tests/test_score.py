"""Unit tests for kvllm.score — verdicts, scorecard/leaderboard rendering, registry write-back.

Port of the Phase 0 report/runner tests to harness v2 (schema-2 scorecards: suite versions,
decode_tok_s/ttft_s, stale markers). Filesystem paths (score.EVALS / score.REGISTRY) are
monkeypatched to tmp_path so nothing touches the real evals dir or models.toml.
"""

from __future__ import annotations

import json
import tomllib

from kvllm import score


def _card(**overrides) -> dict:
    card = {
        "schema": 2,
        "model": "test-model",
        "date": "2026-07-02",
        "hf_repo": "org/test-model",
        "operational": {
            "served": True,
            "cold_start_s": 12.3,
            "gpu_used_mib": 1234,
            "ttft_s": 0.4,
            "decode_tok_s": 55.0,
        },
        "suites": {
            "tools": {
                "version": 2,
                "passed": 10,
                "total": 11,
                "pass_rate": 0.91,
                "cases": [
                    {
                        "name": "single_call",
                        "passed": True,
                        "detail": "get_weather(...)",
                    }
                ],
                "log": "eval-logs/test-model/2026-07-02/x.eval",
            }
        },
        "notes": "",
        "verdict": "worth trying",
    }
    card.update(overrides)
    return card


# --- verdict -----------------------------------------------------------------------------


def test_verdict_not_served_is_skip():
    assert score.verdict(False, {}) == "skip"


def test_verdict_served_no_suites_is_worth_trying():
    assert score.verdict(True, {}) == "worth trying"


def test_verdict_suite_below_threshold_has_issues():
    assert score.verdict(True, {"tools": {"pass_rate": 0.5}}) == "has issues"


def test_verdict_passing_but_slow_decode_has_issues():
    suites = {"tools": {"pass_rate": 1.0}}
    assert score.verdict(True, suites, score.MIN_DECODE_TOK_S - 0.1) == "has issues"


def test_verdict_passing_and_fast_is_worth_trying():
    suites = {"tools": {"pass_rate": 1.0}}
    assert score.verdict(True, suites, score.MIN_DECODE_TOK_S + 5) == "worth trying"


def test_verdict_decode_none_does_not_downgrade():
    assert score.verdict(True, {"tools": {"pass_rate": 1.0}}, None) == "worth trying"


# --- _slug / _row ------------------------------------------------------------------------


def test_slug_replaces_slashes_and_keeps_dots():
    assert score._slug("org/model-name") == "org_model-name"
    # the Sprint 7 bug: Path.with_suffix mangles dotted keys; _slug must not
    assert score._slug("qwen2.5-7b-instruct") == "qwen2.5-7b-instruct"


def test_row_marks_stale_suites():
    row = score._row(_card(), {"tools": 3}, score.load_config())
    assert row["suites"]["tools"] == {"pass_rate": 0.91, "stale": True}


def test_row_current_suite_not_stale():
    row = score._row(_card(), {"tools": 2}, score.load_config())
    assert row["suites"]["tools"]["stale"] is False


def test_row_v1_card_falls_back_to_tokens_per_sec():
    card = _card(
        operational={"served": True, "gpu_used_mib": 1, "tokens_per_sec": 90.3},
        suites={"tools": {"passed": 7, "total": 7, "pass_rate": 1.0, "cases": []}},
    )
    row = score._row(card, {"tools": 2}, score.load_config())
    assert row["tok_s"] == 90.3
    assert row["suites"]["tools"]["stale"] is True  # v1 card has no version


# --- write_scorecard ---------------------------------------------------------------------


def test_write_scorecard_writes_json_and_md(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "EVALS", tmp_path)
    card = _card()

    jpath, mpath = score.write_scorecard(card)

    assert jpath.name == "test-model-2026-07-02.json"
    assert json.loads(jpath.read_text()) == card
    md = mpath.read_text()
    assert "worth trying" in md
    assert "tools v2" in md
    assert "single_call" in md
    assert "inspect view" in md  # transcript pointer


def test_write_scorecard_dotted_model_key_not_mangled(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "EVALS", tmp_path)
    jpath, _ = score.write_scorecard(_card(model="qwen2.5-7b-instruct"))
    assert jpath.name == "qwen2.5-7b-instruct-2026-07-02.json"


def test_write_scorecard_includes_error_line(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "EVALS", tmp_path)
    card = _card(operational={"served": False, "error": "OOM: boom"}, suites={})
    _, mpath = score.write_scorecard(card)
    assert "OOM: boom" in mpath.read_text()


# --- leaderboard ---------------------------------------------------------------------------


def test_leaderboard_keeps_latest_per_model(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "EVALS", tmp_path)
    (tmp_path / "test-model-2026-06-01.json").write_text(
        json.dumps(_card(date="2026-06-01", verdict="has issues"))
    )
    (tmp_path / "test-model-2026-07-02.json").write_text(json.dumps(_card()))

    score.write_leaderboard({"tools": 2})

    rows = json.loads((tmp_path / "leaderboard.json").read_text())["rows"]
    assert len(rows) == 1
    assert rows[0]["verdict"] == "worth trying"


def test_leaderboard_all_three_formats_with_stale_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "EVALS", tmp_path)
    (tmp_path / "test-model-2026-07-02.json").write_text(json.dumps(_card()))

    paths = score.write_leaderboard({"tools": 3})  # current is 3 → this card is stale

    assert {p.name for p in paths} == {
        "leaderboard.json",
        "leaderboard.md",
        "leaderboard.html",
    }
    md = (tmp_path / "leaderboard.md").read_text()
    assert "91%†" in md
    assert "older suite version" in md
    assert "91%†" in (tmp_path / "leaderboard.html").read_text()


def test_leaderboard_ignores_its_own_output(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "EVALS", tmp_path)
    (tmp_path / "test-model-2026-07-02.json").write_text(json.dumps(_card()))
    (tmp_path / "leaderboard.json").write_text(json.dumps({"rows": [], "suites": []}))

    score.write_leaderboard({"tools": 2})

    rows = json.loads((tmp_path / "leaderboard.json").read_text())["rows"]
    assert len(rows) == 1


# --- resume helpers ------------------------------------------------------------------------


def test_scorecard_current_true_when_versions_match(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "EVALS", tmp_path)
    (tmp_path / "test-model-2026-07-02.json").write_text(json.dumps(_card()))
    assert score.scorecard_current("test-model", {"tools": 2})
    assert not score.scorecard_current("test-model", {"tools": 3})
    assert not score.scorecard_current("test-model", {"tools": 2, "coding": 1})
    assert not score.scorecard_current("other-model", {"tools": 2})


# --- update_registry --------------------------------------------------------------------


def test_update_registry_writes_verdict_fields(tmp_path, monkeypatch):
    registry_path = tmp_path / "models.toml"
    registry_path.write_text(
        '[models."test-model"]\nhf_repo = "org/test-model"\ntested = false\n'
    )
    monkeypatch.setattr(score, "REGISTRY", registry_path)

    assert score.update_registry(_card()) == registry_path
    entry = tomllib.loads(registry_path.read_text())["models"]["test-model"]
    assert entry["tested"] is True
    assert entry["eval_verdict"] == "worth trying"
    assert entry["eval_date"] == "2026-07-02"
    assert "eval_notes" not in entry


def test_update_registry_clears_stale_notes_on_pass(tmp_path, monkeypatch):
    registry_path = tmp_path / "models.toml"
    registry_path.write_text(
        '[models."test-model"]\n'
        'hf_repo = "org/test-model"\n'
        "tested = false\n"
        'eval_notes = "used to fail"\n'
    )
    monkeypatch.setattr(score, "REGISTRY", registry_path)

    score.update_registry(_card(notes=""))

    data = tomllib.loads(registry_path.read_text())
    assert "eval_notes" not in data["models"]["test-model"]


def test_update_registry_unknown_model_returns_none(tmp_path, monkeypatch):
    registry_path = tmp_path / "models.toml"
    registry_path.write_text('[models."other-model"]\nhf_repo = "org/other"\n')
    monkeypatch.setattr(score, "REGISTRY", registry_path)
    assert score.update_registry(_card()) is None


# --- log path normalization -----------------------------------------------------------


def test_normalize_log_path_plain_and_file_uri():
    p = score.REPO / "eval-logs" / "m" / "x.eval"
    assert score._normalize_log_path(p) == "eval-logs/m/x.eval"
    assert score._normalize_log_path(f"file://{p}") == "eval-logs/m/x.eval"
    assert score._normalize_log_path(f"file:{p}") == "eval-logs/m/x.eval"


def test_normalize_log_path_outside_repo_stays_absolute():
    assert score._normalize_log_path("/tmp/elsewhere/x.eval") == "/tmp/elsewhere/x.eval"


# --- partial-credit recompute (coding-style cases) ------------------------------------


def _fake_log(monkeypatch, samples):
    """Point suite_from_log's read_eval_log at a canned log object."""
    import kvllm.score as score_mod

    class _Log:
        status = "success"

        def __init__(self, samples):
            self.samples = samples

    import inspect_ai.log as ial

    monkeypatch.setattr(ial, "read_eval_log", lambda p: _Log(samples))
    return score_mod


def test_suite_from_log_recomputes_from_raw_frac(tmp_path, monkeypatch):
    from types import SimpleNamespace as NS

    samples = [
        # solved fully, no real limit, old-style ×0.9 explanation -> cleaned + full credit
        NS(
            id="a",
            limit=None,
            scores={
                "s": NS(
                    value=0.9,
                    metadata={"raw_frac": 1.0},
                    explanation="8/8 hidden tests; hit message/time limit (×0.9)",
                )
            },
        ),
        # partial + REAL limit -> ×0.9 kept
        NS(
            id="b",
            limit=NS(type="message", limit=30),
            scores={"s": NS(value=0.45, metadata={"raw_frac": 0.5}, explanation="4/8")},
        ),
    ]
    score_mod = _fake_log(monkeypatch, samples)
    result = score_mod.suite_from_log("x.eval", 1)
    by = {c["name"]: c for c in result["cases"]}
    assert by["a"]["score"] == 1.0 and by["a"]["passed"] is True
    assert "×0.9" not in by["a"]["detail"]
    assert by["b"]["score"] == 0.45 and by["b"]["passed"] is False
    assert result["pass_rate"] == round((1.0 + 0.45) / 2, 2)


def test_suite_from_log_binary_cases_unchanged(tmp_path, monkeypatch):
    from types import SimpleNamespace as NS

    samples = [
        NS(
            id="t1",
            limit=None,
            scores={"s": NS(value="C", metadata=None, explanation="ok")},
        ),
        NS(
            id="t2",
            limit=None,
            scores={"s": NS(value="I", metadata=None, explanation="no")},
        ),
    ]
    score_mod = _fake_log(monkeypatch, samples)
    result = score_mod.suite_from_log("x.eval", 2)
    assert result["passed"] == 1 and result["total"] == 2 and result["pass_rate"] == 0.5


# --- composite / speed factor / verdict v2 -----------------------------------------------


def _cfg(**over):
    cfg = {
        "weights": {"tools": 0.30, "code": 0.35, "agentic": 0.25, "judged": 0.10},
        "speed": {"floor_tok_s": 10, "full_tok_s": 40},
        "verdict": {"composite_floor": 0.55, "suite_floor": 0.40},
        "judge": {"model": "anthropic/x", "calibrated": False},
    }
    cfg.update(over)
    return cfg


def test_speed_factor_curve():
    cfg = _cfg()
    assert score.speed_factor(None, cfg) == 1.0
    assert score.speed_factor(5, cfg) == 0.5
    assert score.speed_factor(10, cfg) == 0.5
    assert score.speed_factor(40, cfg) == 1.0
    assert score.speed_factor(100, cfg) == 1.0
    assert score.speed_factor(25, cfg) == 0.75


def _comp_card(suites, decode=100.0):
    return {"suites": suites, "operational": {"decode_tok_s": decode}}


def test_composite_renormalizes_over_eligible():
    # tools 1.0 (w .30) + code 0.5 (w .35) -> (0.3 + 0.175) / 0.65
    card = _comp_card(
        {
            "tools": {"version": 2, "pass_rate": 1.0},
            "code": {"version": 1, "pass_rate": 0.5},
        }
    )
    comp = score.composite(card, _cfg(), {"tools": 2, "code": 1})
    assert comp["composite"] == round((0.3 + 0.175) / 0.65, 3)
    assert comp["eligible"] == ["code", "tools"]
    assert comp["speed_factor"] == 1.0


def test_composite_excludes_stale_and_uncalibrated_judged():
    card = _comp_card(
        {
            "tools": {"version": 1, "pass_rate": 1.0},  # stale (current is 2)
            "judged": {"version": 1, "pass_rate": 1.0},  # uncalibrated
            "code": {"version": 1, "pass_rate": 0.6},
        }
    )
    comp = score.composite(card, _cfg(), {"tools": 2, "code": 1, "judged": 1})
    assert comp["eligible"] == ["code"]
    assert comp["composite"] == 0.6


def test_composite_none_when_no_eligible_suites():
    assert score.composite(_comp_card({}), _cfg(), {}) is None


def test_composite_applies_speed_factor():
    card = _comp_card({"code": {"version": 1, "pass_rate": 1.0}}, decode=25)
    comp = score.composite(card, _cfg(), {"code": 1})
    assert comp["speed_factor"] == 0.75
    assert comp["composite"] == 0.75


def test_verdict_v2_composite_floor():
    # tools 100% + code 53% -> composite (0.3 + 0.1855)/0.65 = 0.747 -> worth trying
    suites = {
        "tools": {"version": 2, "pass_rate": 1.0},
        "code": {"version": 1, "pass_rate": 0.53},
    }
    v = score.verdict(
        True, suites, 105.0, cfg=_cfg(), current_versions={"tools": 2, "code": 1}
    )
    assert v == "worth trying"


def test_verdict_v2_suite_floor_caps():
    # coder: tools 27% (< suite_floor 0.40) -> has issues regardless of composite
    suites = {
        "tools": {"version": 2, "pass_rate": 0.27},
        "code": {"version": 1, "pass_rate": 0.9},
    }
    v = score.verdict(
        True, suites, 105.0, cfg=_cfg(), current_versions={"tools": 2, "code": 1}
    )
    assert v == "has issues"


def test_verdict_v2_speed_floor_still_caps():
    suites = {"tools": {"version": 2, "pass_rate": 1.0}}
    assert score.verdict(True, suites, 9.0, cfg=_cfg()) == "has issues"


def test_ranked_ordering_and_medals():
    rows = [
        {"model": "b", "composite": 0.5},
        {"model": "gate-only", "composite": None},
        {"model": "a", "composite": 0.9},
        {"model": "c", "composite": 0.7},
    ]
    ranked = score._ranked(rows)
    assert [r["model"] for r in ranked] == ["a", "c", "b", "gate-only"]
    assert [r.get("medal") for r in ranked] == ["①", "②", "③", ""]
    assert ranked[3]["rank"] is None


# --- HTML detail panels ----------------------------------------------------------------------


def test_html_detail_panel_shows_cases_and_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "EVALS", tmp_path)
    monkeypatch.setattr(score, "REGISTRY", tmp_path / "absent.toml")
    card = _card()
    card["suites"]["tools"]["cases"].append(
        {
            "name": "judged-case",
            "passed": False,
            "score": 0.4,
            "detail": "judge 4/10 — weak <answer> & vague",
            "meta": {
                "violations": ["fabricated a metric"],
                "fabricated": True,
                "tool_calls": 7,
            },
        }
    )
    (tmp_path / "test-model-2026-07-02.json").write_text(json.dumps(card))

    score.write_leaderboard({"tools": 2})
    h = (tmp_path / "leaderboard.html").read_text()

    assert 'class="detail"' in h and 'class="row"' in h
    assert "judged-case" in h
    # detail text is escaped, not raw-injected
    assert "weak &lt;answer&gt; &amp; vague" in h
    assert "<answer>" not in h
    assert "fabricated a metric" in h
    assert "7 tool calls" in h
    assert "55 tok/s decode" in h
    assert "org/test-model" in h


def test_html_detail_panel_registry_notes_and_eq(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "EVALS", tmp_path)
    reg = tmp_path / "models.toml"
    reg.write_text(
        '[models."test-model"]\nhf_repo = "org/test-model"\n'
        'notes = "registry-note-text"\neval_notes = "old OOM trace"\n'
    )
    monkeypatch.setattr(score, "REGISTRY", reg)
    (tmp_path / "test-model-2026-07-02.json").write_text(json.dumps(_card()))

    score.write_leaderboard({"tools": 2})
    h = (tmp_path / "leaderboard.html").read_text()

    assert "registry-note-text" in h
    assert "old OOM trace" in h
    assert "speed ×" in h  # composite equation rendered
