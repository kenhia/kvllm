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
    row = score._row(_card(), {"tools": 3})
    assert row["suites"]["tools"] == {"pass_rate": 0.91, "stale": True}


def test_row_current_suite_not_stale():
    row = score._row(_card(), {"tools": 2})
    assert row["suites"]["tools"]["stale"] is False


def test_row_v1_card_falls_back_to_tokens_per_sec():
    card = _card(
        operational={"served": True, "gpu_used_mib": 1, "tokens_per_sec": 90.3},
        suites={"tools": {"passed": 7, "total": 7, "pass_rate": 1.0, "cases": []}},
    )
    row = score._row(card, {"tools": 2})
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
