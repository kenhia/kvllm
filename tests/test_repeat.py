"""kvllm.repeat unit tests — the noise-floor aggregation (pure; no eval, no GPU).

The behaviour that matters here is what korg:1499's mechanics comment warns about: a
repeat harness that silently reports a spread of 0.00 is worse than one that errors,
because 0.00 is exactly the answer a hopeful reader wants. So the aggregation only ever
spans suites that were actually re-executed, and a genuine 0.00 is labelled as such.
"""

from __future__ import annotations

import json

import pytest

from kvllm import repeat


def _card(agentic: float, tools: float = 0.8, **extra) -> dict:
    """A scorecard shaped like the ones evaluate() returns (only the fields we read)."""
    suites = {
        "agentic": {"version": 4, "pass_rate": agentic, "passed": 1, "total": 9},
        "tools": {"version": 3, "pass_rate": tools, "passed": 4, "total": 5},
    }
    return {"model": "m", "date": "2026-08-20", "suites": suites, **extra}


# --- spread -------------------------------------------------------------------------


def test_spread_reports_min_max_and_band_for_a_fresh_suite():
    cards = [_card(0.90), _card(0.95), _card(0.92)]
    s = repeat.spread(cards, fresh=["agentic"])["agentic"]
    assert s["runs"] == [0.90, 0.95, 0.92]
    assert s["n"] == 3
    assert s["min"] == 0.90
    assert s["max"] == 0.95
    assert s["spread"] == 0.05
    assert s["median"] == 0.92
    assert round(s["mean"], 4) == 0.9233
    assert s["identical"] is False


def test_spread_covers_only_freshly_run_suites():
    """`tools` is carried forward by merge_prior_suites — identical in all three cards
    because it was never re-executed. Including it would advertise a 0.00 'noise floor'
    for a suite that was measured once."""
    cards = [_card(0.90), _card(0.95), _card(0.92)]
    stats = repeat.spread(cards, fresh=["agentic"])
    assert set(stats) == {"agentic"}


def test_spread_flags_a_genuine_zero_rather_than_hiding_it():
    """`tools` and `code` really do come back bit-identical (sprint 15). A 0.00 there is a
    result, not an artifact — but it must never be read without the label."""
    cards = [_card(0.9, tools=0.8) for _ in range(3)]
    s = repeat.spread(cards, fresh=["agentic", "tools"])
    assert s["agentic"]["spread"] == 0.0
    assert s["agentic"]["identical"] is True
    assert s["tools"]["identical"] is True


def test_spread_records_a_suite_error_and_excludes_the_run():
    cards = [_card(0.90), _card(0.95), _card(0.92)]
    cards[1]["suites"]["agentic"]["error"] = "no inspect log produced"
    s = repeat.spread(cards, fresh=["agentic"])["agentic"]
    assert s["errors"] == ["run 2: no inspect log produced"]
    assert s["runs"] == [0.90, 0.92]
    assert s["n"] == 2


def test_spread_of_a_suite_with_no_usable_runs_is_reported_not_crashed():
    cards = [_card(0.9)]
    cards[0]["suites"]["agentic"]["error"] = "boom"
    s = repeat.spread(cards, fresh=["agentic"])["agentic"]
    assert s["n"] == 0
    assert s["spread"] is None
    assert s["identical"] is False


def test_spread_ignores_a_suite_absent_from_a_card():
    cards = [_card(0.9), _card(0.95)]
    del cards[1]["suites"]["agentic"]
    s = repeat.spread(cards, fresh=["agentic"])["agentic"]
    assert s["runs"] == [0.9]


# --- choosing what the board shows ----------------------------------------------------


def test_pick_median_selects_the_middle_run_not_the_last():
    """The whole point: left alone the board shows whichever run finished last."""
    cards = [_card(0.90), _card(0.95), _card(0.92)]
    assert repeat.pick_index(cards, "median", fresh=["agentic"]) == 2


def test_pick_first_and_last():
    cards = [_card(0.90), _card(0.95), _card(0.92)]
    assert repeat.pick_index(cards, "first", fresh=["agentic"]) == 0
    assert repeat.pick_index(cards, "last", fresh=["agentic"]) == 2


def test_pick_none_publishes_nothing():
    cards = [_card(0.90), _card(0.95)]
    assert repeat.pick_index(cards, "none", fresh=["agentic"]) is None


def test_pick_median_is_deterministic_on_ties():
    cards = [_card(0.9), _card(0.9), _card(0.9)]
    assert repeat.pick_index(cards, "median", fresh=["agentic"]) == 1


def test_pick_median_over_several_fresh_suites_uses_their_mean():
    lo, mid, hi = _card(0.1, tools=0.1), _card(0.5, tools=0.5), _card(0.9, tools=0.9)
    assert repeat.pick_index([hi, lo, mid], "median", fresh=["agentic", "tools"]) == 2


def test_pick_on_an_empty_run_set_is_none():
    assert repeat.pick_index([], "median", fresh=["agentic"]) is None


# --- the writeup --------------------------------------------------------------------


def test_render_markdown_states_the_band_and_the_within_night_caveat():
    cards = [_card(0.90), _card(0.95), _card(0.92)]
    stats = repeat.spread(cards, fresh=["agentic"])
    md = repeat.render_markdown(
        key="claude-sonnet-5", date="2026-08-20", stats=stats, chosen=2, n=3
    )
    assert "claude-sonnet-5" in md
    assert "0.050" in md  # the band
    assert "run 3" in md  # what the board was given
    assert "within-night" in md.lower()  # the confound, named


# --- CLI wiring (the eval itself is stubbed; nothing is served, nothing is spent) -----


def _stub_run(monkeypatch, tmp_path, rates):
    """Replace the eval with canned cards and redirect every write into tmp_path."""
    from kvllm import evalctl, evalrun, score

    calls = []

    def fake_evaluate(key, entry, **kw):
        calls.append(kw)
        return _card(rates[len(calls) - 1])

    monkeypatch.setattr(evalrun, "evaluate", fake_evaluate)
    monkeypatch.setattr(evalctl, "service_active", lambda: False)
    monkeypatch.setattr(repeat, "RESULTS", tmp_path / "noise-floor")
    monkeypatch.setattr(score, "write_all", lambda card, versions: [tmp_path / "board"])
    monkeypatch.setenv("KVLLM_RUN_STATE", str(tmp_path / "run.json"))
    return calls


def test_main_gives_every_run_its_own_log_dir_and_forces_reexecution(
    tmp_path, monkeypatch
):
    """The core defence: distinct run_tag per run (nothing resumes) and force=True
    (something actually re-executes). Without both the spread is a meaningless 0.00."""
    calls = _stub_run(monkeypatch, tmp_path, [0.90, 0.95, 0.92])
    rc = repeat.main(
        ["gemma-4-31b-it-awq", "--suite", "agentic", "--n", "3", "--settle", "0"]
    )
    assert rc == 0
    assert [c["run_tag"] for c in calls] == ["r1", "r2", "r3"]
    assert all(c["force"] for c in calls)


def test_main_writes_per_run_cards_and_a_summary(tmp_path, monkeypatch):
    _stub_run(monkeypatch, tmp_path, [0.90, 0.95, 0.92])
    repeat.main(
        ["gemma-4-31b-it-awq", "--suite", "agentic", "--n", "3", "--settle", "0"]
    )
    out = next((tmp_path / "noise-floor").iterdir())
    assert {p.name for p in out.iterdir()} == {
        "run-1.json",
        "run-2.json",
        "run-3.json",
        "summary.json",
        "README.md",
    }
    summary = json.loads((out / "summary.json").read_text())
    assert summary["suites_repeated"] == ["agentic"]
    assert summary["stats"]["agentic"]["spread"] == 0.05
    assert summary["published_run"] == 3  # the median draw, not "the last one"


def test_main_refuses_to_spend_on_an_api_model_without_the_cost_gate(
    tmp_path, monkeypatch, capsys
):
    """korg:1499 makes the gate mandatory, and an overnight run cannot ask at 02:00 —
    so the tool refuses at launch rather than assuming."""
    _stub_run(monkeypatch, tmp_path, [0.9, 0.9, 0.9])
    with pytest.raises(SystemExit) as e:
        repeat.main(["claude-sonnet-5", "--suite", "agentic", "--n", "3"])
    assert "--confirm-cost" in str(e.value)
    assert not (tmp_path / "noise-floor").exists()  # nothing ran


def test_main_runs_an_api_model_once_the_cost_gate_is_answered(tmp_path, monkeypatch):
    calls = _stub_run(monkeypatch, tmp_path, [0.9, 0.95, 0.92])
    rc = repeat.main(
        ["claude-sonnet-5", "--suite", "agentic", "--n", "3", "--confirm-cost"]
    )
    assert rc == 0 and len(calls) == 3


def test_main_publish_none_leaves_the_board_alone(tmp_path, monkeypatch):
    from kvllm import score

    _stub_run(monkeypatch, tmp_path, [0.9, 0.95, 0.92])
    written = []
    monkeypatch.setattr(
        score, "write_all", lambda card, versions: written.append(card) or []
    )
    repeat.main(
        [
            "gemma-4-31b-it-awq",
            "--suite",
            "agentic",
            "--n",
            "3",
            "--settle",
            "0",
            "--publish",
            "none",
        ]
    )
    assert written == []
    out = next((tmp_path / "noise-floor").iterdir())
    assert json.loads((out / "summary.json").read_text())["published_run"] is None


def test_main_rejects_n_below_two():
    with pytest.raises(SystemExit) as e:
        repeat.main(["gemma-4-31b-it-awq", "--n", "1"])
    assert "at least 2" in str(e.value)


def test_main_keeps_completed_runs_when_a_later_one_dies(tmp_path, monkeypatch):
    """A night that dies on run 3 must not throw away runs 1 and 2."""
    from kvllm import evalctl, evalrun

    calls = []

    def flaky(key, entry, **kw):
        calls.append(kw)
        if len(calls) == 3:
            raise RuntimeError("GPU wedged")
        return _card([0.9, 0.95][len(calls) - 1])

    monkeypatch.setattr(evalrun, "evaluate", flaky)
    monkeypatch.setattr(evalctl, "service_active", lambda: False)
    monkeypatch.setattr(repeat, "RESULTS", tmp_path / "noise-floor")
    monkeypatch.setenv("KVLLM_RUN_STATE", str(tmp_path / "run.json"))

    with pytest.raises(RuntimeError):
        repeat.main(
            ["gemma-4-31b-it-awq", "--suite", "agentic", "--n", "3", "--settle", "0"]
        )
    out = next((tmp_path / "noise-floor").iterdir())
    assert {p.name for p in out.iterdir()} == {"run-1.json", "run-2.json"}
