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


# --- sprint 22: the controller floor and the effort tool, against a scripted client ------


class _Msg:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.model_extra = {}


class _Call:
    def __init__(self, i, name, args):
        from types import SimpleNamespace as NS

        self.id = f"call-{i}"
        self.function = NS(name=name, arguments=json.dumps(args))


class _Client:
    """A candidate that does exactly what its script says, one turn per entry. Records
    the params of every request so a test can see what kwargs each turn was sent with."""

    def __init__(self, script):
        from types import SimpleNamespace as NS

        self.script = list(script)
        self.requests = []
        self._NS = NS
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **params):
        NS = self._NS
        self.requests.append(params)
        calls = self.script.pop(0) if self.script else []
        msg = _Msg("", [_Call(i, n, a) for i, (n, a) in enumerate(calls)])
        return NS(
            usage=NS(prompt_tokens=10, completion_tokens=5),
            choices=[NS(message=msg, finish_reason="stop")],
        )


import json  # noqa: E402

from interview.run import attempt  # noqa: E402


def _scenario():
    return {
        "task": "check kubsdb",
        "world": {
            "hosts": {
                "kubsdb": {
                    "commands": {"df -h": "61% /", "journalctl -u sshd": "quiet"},
                    "files": {},
                }
            },
            "manifest": {},
            "korg": [],
        },
        "truth": {"solvable": True, "action": "handle", "finding_keywords": ["fine"]},
    }


def _rep(action="handle"):
    return (
        "report",
        {
            "action": action,
            "confidence": 0.9,
            "finding": "fine",
            "evidence": "",
            "next_step": "",
        },
    )


def test_controller_floor_refuses_until_met_then_accepts():
    c = _Client(
        [
            [("run_command", {"host": "kubsdb", "command": "df -h"})],
            [_rep("handle")],  # refused: four items missing on kubsdb
            [
                (
                    "run_command",
                    {
                        "host": "kubsdb",
                        "command": "systemctl --failed; journalctl -p warning -n 100; journalctl -k; last",
                    },
                )
            ],
            [_rep("handle")],  # accepted
        ]
    )
    r = attempt(c, "m", "sys", _scenario(), {}, 1000, None, 16, floor="controller")
    assert r["report"] is not None and r["turns"] == 4
    assert r["floor_refusals"] == 1
    assert r["floor_missing_first"] == {
        "kubsdb": ["failed-units", "warnings", "kernel", "auth"]
    }
    assert r["floor_met"] is True and r["floor_missing_at_report"] is None
    assert r["judge"]["cell"] == "correct"
    # the refusal reached the candidate as the report tool's result
    refused = r["transcript"][1]["tool_calls"][0]["output"]
    assert refused.startswith("report refused") and "kubsdb: failed-units" in refused


def test_controller_floor_never_holds_an_escalation_and_no_floor_never_refuses():
    c = _Client(
        [
            [("run_command", {"host": "kubsdb", "command": "df -h"})],
            [_rep("escalate_now")],
        ]
    )
    r = attempt(c, "m", "sys", _scenario(), {}, 1000, None, 16, floor="controller")
    assert r["report"]["action"] == "escalate_now" and r["floor_refusals"] == 0
    assert r["floor_missing_at_report"] == {
        "kubsdb": ["failed-units", "warnings", "kernel", "auth"]
    }
    c = _Client(
        [
            [("run_command", {"host": "kubsdb", "command": "df -h"})],
            [_rep("handle")],
        ]
    )
    r = attempt(c, "m", "sys", _scenario(), {}, 1000, None, 16)
    assert r["report"] is not None and r["floor_refusals"] == 0
    assert r["floor"] == "none" and r["floor_met"] is False


def test_effort_tool_switches_kwargs_for_the_rest_of_the_attempt():
    c = _Client(
        [
            [("run_command", {"host": "kubsdb", "command": "df -h"})],
            [("request_effort", {"reason": "rates to reconcile"})],
            [("request_effort", {"reason": "again"})],
            [_rep("handle")],
        ]
    )
    r = attempt(
        c,
        "m",
        "sys",
        _scenario(),
        {"reasoning_effort": "medium"},
        1000,
        None,
        16,
        effort={"reasoning_effort": "xhigh"},
        effort_base="medium",
        effort_cost="4× wall-clock",
    )
    assert r["effort_turn"] == 2 and r["effort_reason"] == "rates to reconcile"
    assert r["kwargs_final"] == {"reasoning_effort": "xhigh"}
    sent = [
        q["extra_body"]["chat_template_kwargs"]["reasoning_effort"] for q in c.requests
    ]
    assert sent == ["medium", "medium", "xhigh", "xhigh"]
    assert "already granted" in r["transcript"][2]["tool_calls"][0]["output"]
    # the tool and the note are only present when the condition is on
    assert any(
        t["function"]["name"] == "request_effort" for t in c.requests[0]["tools"]
    )
    assert "request_effort" in c.requests[0]["messages"][0]["content"]
    c2 = _Client([[_rep("handle")]])
    attempt(c2, "m", "sys", _scenario(), {}, 1000, None, 16)
    assert all(
        t["function"]["name"] != "request_effort" for t in c2.requests[0]["tools"]
    )
    assert "request_effort" not in c2.requests[0]["messages"][0]["content"]
