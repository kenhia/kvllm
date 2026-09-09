"""interview.floor — the checklist floor reads the world's call log (pure; no model)."""

from __future__ import annotations

from interview import floor
from interview.world import World


def _calls(*cmds: tuple[str, str]) -> list[dict]:
    return [
        {"tool": "run_command", "args": {"host": h, "command": c}, "chars": 0}
        for h, c in cmds
    ]


def test_each_item_has_its_commands():
    it = floor.items_of
    assert it("run_command", {"host": "a", "command": "systemctl --failed"}) == {
        "failed-units"
    }
    assert it(
        "run_command",
        {"host": "a", "command": "systemctl list-units --state=failed --no-pager"},
    ) == {"failed-units"}
    assert it("run_command", {"host": "a", "command": "systemctl status"}) == {
        "failed-units"
    }
    assert (
        it("run_command", {"host": "a", "command": "systemctl status postgresql"})
        == set()
    )
    assert it(
        "run_command", {"host": "a", "command": "journalctl -p warning -n 100"}
    ) == {"warnings"}
    assert it(
        "run_command",
        {"host": "a", "command": "journalctl --priority=err --since '1 hour ago'"},
    ) == {"warnings"}
    assert it(
        "run_command",
        {
            "host": "a",
            "command": "journalctl --since '2026-09-07 01:00' --until '2026-09-07 03:00'",
        },
    ) == {"warnings"}
    # a unit-scoped journal is not the whole journal
    assert (
        it("run_command", {"host": "a", "command": "journalctl -u kmon -p warning"})
        == set()
    )
    assert it("run_command", {"host": "a", "command": "journalctl -n 200"}) == set()
    assert it("run_command", {"host": "a", "command": "journalctl -k"}) == {"kernel"}
    assert it("run_command", {"host": "a", "command": "dmesg | tail -50"}) == {"kernel"}
    assert it(
        "run_command", {"host": "a", "command": "sudo journalctl -k -p warning"}
    ) == {"kernel"}
    assert it("run_command", {"host": "a", "command": "df -h"}) == {"disk"}
    assert it("run_command", {"host": "a", "command": "journalctl -u sshd -n 50"}) == {
        "auth"
    }
    assert it("run_command", {"host": "a", "command": "journalctl -u ssh.service"}) == {
        "auth"
    }
    assert it(
        "run_command", {"host": "a", "command": "journalctl -t sshd --since today"}
    ) == {"auth"}
    assert it("run_command", {"host": "a", "command": "last -n 20"}) == {"auth"}
    assert it(
        "run_command", {"host": "a", "command": "grep -i accepted /var/log/auth.log"}
    ) == {"auth"}
    assert it("read_file", {"host": "a", "path": "/var/log/auth.log"}) == {"auth"}
    assert it("read_file", {"host": "a", "path": "/etc/kmon/kmon.toml"}) == set()
    assert it("manifest_lookup", {"service": "all"}) == set()


def test_chains_and_pipes_count_first_stage_only():
    got = floor.items_of(
        "run_command",
        {
            "host": "a",
            "command": "systemctl --failed --no-pager; journalctl -p warning -n 100 | grep -i disk; journalctl -k | tail -20 && df -h; journalctl -u sshd -n 20",
        },
    )
    assert got == set(floor.ITEMS)
    # `grep` after a pipe is a filter, not a floor read
    assert (
        floor.items_of(
            "run_command", {"host": "a", "command": "journalctl -n 50 | grep -i sshd"}
        )
        == set()
    )


def test_missing_is_per_touched_host_and_refusal_names_the_gaps():
    calls = _calls(
        (
            "kubsdb",
            "systemctl --failed; journalctl -p warning -n 100; journalctl -k; df -h; last",
        ),
        ("kubs0", "systemctl --failed; df -h"),
        ("kai", "nvidia-smi"),
    )
    miss = floor.missing(calls, {"kubsdb", "kubs0", "kai"})
    assert "kubsdb" not in miss
    assert miss["kubs0"] == ["warnings", "kernel", "auth"]
    assert miss["kai"] == list(floor.ITEMS)
    # hosts the candidate never touched are not on the hook
    assert floor.missing(calls, {"kubsdb"}) == {}
    text = floor.refusal(miss)
    assert text.startswith("report refused")
    assert "kubs0: warnings, kernel, auth" in text
    assert "kai: failed-units, warnings, kernel, disk, auth" in text
    assert "escalate_now" in text


def test_world_records_touched_reachable_hosts():
    w = World(
        {
            "hosts": {"kubsdb": {"commands": {"df -h": "61% /"}, "files": {}}},
            "manifest": {},
            "korg": [],
        }
    )
    w.dispatch("run_command", {"host": "kubsdb", "command": "df -h"})
    w.dispatch("run_command", {"host": "cleo", "command": "ls /gratch"})
    w.dispatch("read_file", {"host": "kubsdb", "path": "/nope"})
    w.dispatch("manifest_lookup", {"service": "all"})
    assert w.touched == {"kubsdb"}
    assert floor.missing(w.calls, w.touched) == {
        "kubsdb": ["failed-units", "warnings", "kernel", "auth"]
    }
