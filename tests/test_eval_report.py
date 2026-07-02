"""Unit tests for kvllm.eval.report — scorecard/leaderboard rendering + registry write-back.

Filesystem paths (report.EVALS / report.REGISTRY) are monkeypatched to a tmp_path so nothing
touches the real docs/model-research/evals/ or models.toml.
"""

from __future__ import annotations

import json
import tomllib

from kvllm.eval import report


def _card(**overrides) -> dict:
    card = {
        "model": "test-model",
        "date": "2026-07-02",
        "hf_repo": "org/test-model",
        "operational": {
            "served": True,
            "cold_start_s": 12.3,
            "gpu_used_mib": 1234,
            "tokens_per_sec": 55.0,
        },
        "suites": {
            "tools": {
                "passed": 7,
                "total": 7,
                "pass_rate": 1.0,
                "cases": [
                    {
                        "name": "single_call",
                        "passed": True,
                        "detail": "get_weather(...)",
                    }
                ],
            }
        },
        "notes": "",
        "verdict": "worth trying",
    }
    card.update(overrides)
    return card


# --- _slug / _row --------------------------------------------------------------------


def test_slug_replaces_slashes():
    assert report._slug("org/model-name") == "org_model-name"


def test_slug_leaves_dotted_keys_alone():
    # the bug Sprint 07 caught: Path.with_suffix mangles dotted keys; _slug must not
    assert report._slug("qwen2.5-7b-instruct") == "qwen2.5-7b-instruct"


def test_row_extracts_operational_and_suite_fields():
    row = report._row(_card())
    assert row["model"] == "test-model"
    assert row["verdict"] == "worth trying"
    assert row["gpu_mib"] == 1234
    assert row["tok_s"] == 55.0
    assert row["cold_s"] == 12.3
    assert row["suites"] == {"tools": 1.0}


# --- write_scorecard -------------------------------------------------------------------


def test_write_scorecard_writes_json_and_md(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "EVALS", tmp_path)
    card = _card()

    paths = report.write_scorecard(card)

    jpath, mpath = paths
    assert jpath.name == "test-model-2026-07-02.json"
    assert json.loads(jpath.read_text()) == card
    md = mpath.read_text()
    assert "test-model" in md
    assert "worth trying" in md
    assert "single_call" in md


def test_write_scorecard_dotted_model_key_not_mangled(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "EVALS", tmp_path)
    card = _card(model="qwen2.5-7b-instruct")

    jpath, _ = report.write_scorecard(card)

    assert jpath.name == "qwen2.5-7b-instruct-2026-07-02.json"


def test_write_scorecard_includes_error_line_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "EVALS", tmp_path)
    card = _card(operational={"served": False, "error": "OOM: boom"})

    _, mpath = report.write_scorecard(card)

    assert "OOM: boom" in mpath.read_text()


# --- write_leaderboard -----------------------------------------------------------------


def test_write_leaderboard_keeps_latest_per_model(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "EVALS", tmp_path)
    older = _card(date="2026-06-01", verdict="has issues")
    newer = _card(date="2026-07-02", verdict="worth trying")
    (tmp_path / "test-model-2026-06-01.json").write_text(json.dumps(older))
    (tmp_path / "test-model-2026-07-02.json").write_text(json.dumps(newer))

    report.write_leaderboard()

    rows = json.loads((tmp_path / "leaderboard.json").read_text())["rows"]
    assert len(rows) == 1
    assert rows[0]["verdict"] == "worth trying"
    assert rows[0]["date"] == "2026-07-02"


def test_write_leaderboard_produces_all_three_formats(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "EVALS", tmp_path)
    (tmp_path / "test-model-2026-07-02.json").write_text(json.dumps(_card()))

    paths = report.write_leaderboard()

    names = {p.name for p in paths}
    assert names == {"leaderboard.json", "leaderboard.md", "leaderboard.html"}
    assert "test-model" in (tmp_path / "leaderboard.md").read_text()
    assert "test-model" in (tmp_path / "leaderboard.html").read_text()


def test_write_leaderboard_ignores_its_own_output(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "EVALS", tmp_path)
    (tmp_path / "test-model-2026-07-02.json").write_text(json.dumps(_card()))
    # a leftover leaderboard.json from a previous run must not be read back as a scorecard
    (tmp_path / "leaderboard.json").write_text(json.dumps({"rows": [], "suites": []}))

    report.write_leaderboard()

    rows = json.loads((tmp_path / "leaderboard.json").read_text())["rows"]
    assert len(rows) == 1


# --- update_registry ---------------------------------------------------------------------


def test_update_registry_writes_verdict_fields(tmp_path, monkeypatch):
    registry_path = tmp_path / "models.toml"
    registry_path.write_text(
        '[models."test-model"]\nhf_repo = "org/test-model"\ntested = false\n'
    )
    monkeypatch.setattr(report, "REGISTRY", registry_path)

    result = report.update_registry(_card())

    assert result == registry_path
    data = tomllib.loads(registry_path.read_text())
    entry = data["models"]["test-model"]
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
    monkeypatch.setattr(report, "REGISTRY", registry_path)

    report.update_registry(_card(notes=""))

    data = tomllib.loads(registry_path.read_text())
    assert "eval_notes" not in data["models"]["test-model"]


def test_update_registry_unknown_model_returns_none(tmp_path, monkeypatch):
    registry_path = tmp_path / "models.toml"
    registry_path.write_text('[models."other-model"]\nhf_repo = "org/other"\n')
    monkeypatch.setattr(report, "REGISTRY", registry_path)

    assert report.update_registry(_card()) is None
