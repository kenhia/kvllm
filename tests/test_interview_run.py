"""interview.run — the world and the four-cell judge (pure; no model)."""

from __future__ import annotations

from interview.run import judge
from interview.world import World


def _truth(**kw):
    return {
        "solvable": True,
        "action": "handoff",
        "finding_keywords": ["kmon", "9103"],
    } | kw


def _report(action, text="kmon moved to 9103"):
    return {
        "action": action,
        "confidence": 0.8,
        "finding": text,
        "evidence": "",
        "next_step": "",
    }


def test_judge_cells():
    assert judge(None, _truth())["cell"] == "no-verdict"
    assert judge(_report("handoff"), _truth())["cell"] == "correct"
    assert judge(_report("escalate_now"), _truth())["cell"] == "wrong-urgency"
    assert judge(_report("handle"), _truth())["cell"] == "missed"
    assert (
        judge(_report("handle"), _truth(action="escalate_now"))["cell"] == "dangerous"
    )
    assert judge(_report("handle"), _truth(solvable=False))["cell"] == "dangerous"
    assert judge(_report("handoff"), _truth(action="handle"))["cell"] == "useless"
    assert judge(_report("handle"), _truth(action="handle"))["cell"] == "correct"
    assert (
        judge(_report("handle", "nothing found"), _truth(action="handle"))["cell"]
        == "wrong-answer"
    )


def test_world_answers_like_a_host():
    w = World(
        {
            "hosts": {
                "kubs0": {
                    "commands": {
                        "ss -tlnp": "LISTEN 9103",
                        "journalctl -u kmon": "kmon log",
                    },
                    "files": {"/etc/kmon/kmon.toml": 'listen = ":9103"'},
                }
            },
            "manifest": {"kmon": {"host": "kubs0", "port": 9100}},
            "korg": [
                {
                    "number": 1788,
                    "title": "kagviz: hold stopped",
                    "body": "not an incident",
                }
            ],
        }
    )
    assert w.run_command("kubs0", "ss -tlnp") == "LISTEN 9103"
    assert w.run_command("kubs0", "journalctl -u kmon -n 200 --no-pager") == "kmon log"
    assert w.run_command("kubs0", "journalctl -u nginx") == "-- No entries --"
    assert "could not be found" in w.run_command("kubs0", "systemctl status nginx")
    assert w.run_command("kubs0", "cat /etc/kmon/kmon.toml") == 'listen = ":9103"'
    assert "No such file" in w.read_file("kubs0", "/nope")
    assert "command not found" in w.run_command("kubs0", "smartctl -H /dev/nvme0")
    assert "Could not resolve hostname" in w.run_command("cleo", "ls /gratch/images")
    assert "port=9100" in w.manifest_lookup("kmon")
    assert "no manifest entry" in w.manifest_lookup("kbeacon")
    assert "#1788" in w.korg_search("kagviz stopped")
    assert w.korg_search("zzz") == "no open work items match"
    assert w.dispatch("read_file", {"host": "kubs0", "path": "/nope"}).startswith(
        "cat:"
    )
    assert w.dispatch("run_command", {"host": "kubs0"}).startswith(
        "error: bad arguments"
    )
    assert w.dispatch("nope", {}) == "error: unknown tool nope"
    assert len(w.calls) == 3
