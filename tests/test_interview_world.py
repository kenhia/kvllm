"""interview.world — the fake fleet answers like real hosts (pure; no model)."""

from __future__ import annotations

from interview.world import World


def _w():
    return World(
        {
            "hosts": {
                "kubsdb": {
                    "commands": {
                        "systemctl status postgresql": "× postgresql.service - postgresql\n     Active: failed (Result: signal) since Mon 2026-09-07 02:41:07 UTC",
                        "systemctl status korg": "● korg.service - korg\n     Active: active (running) since Tue 2026-07-28",
                        "journalctl -u postgresql": "Sep 07 02:40:58 kubsdb kernel: Out of memory: Killed process 1188 (postgres)\nSep 07 02:41:07 kubsdb systemd[1]: postgresql.service: Failed with result 'signal'.",
                        "ss -tlnp": 'State  Recv-Q\nLISTEN 0 4096 0.0.0.0:8720 users:(("korg",pid=1301,fd=7))',
                        "df -h": "Filesystem Size Used Avail Use% Mounted on\n/dev/mapper/vg-root 1.8T 1.1T 650G 61% /",
                        "docker ps": "CONTAINER ID IMAGE STATUS NAMES\n9a1f grafana/grafana Up 5 weeks grafana",
                    },
                    "files": {
                        "/etc/kmon/kmon.toml": 'listen = ":9103"',
                        "/srv/backup/pg-2026-09-07.sql.zst": "zst",
                    },
                }
            },
            "manifest": {
                "kmon": {"host": "kubs0", "port": 9100},
                "korg": {"host": "kubsdb", "port": 8720},
            },
            "korg": [
                {
                    "number": 1788,
                    "title": "kagviz: hold stopped",
                    "body": "not an incident",
                }
            ],
        }
    )


def test_fixture_keys_tolerate_flags_and_suffixes():
    w = _w()
    assert "Out of memory" in w.run_command(
        "kubsdb", "journalctl -u postgresql -n 200 --no-pager"
    )
    assert "Active: failed" in w.run_command(
        "kubsdb", "systemctl status postgresql.service --no-pager"
    )
    assert "Active: failed" in w.run_command(
        "kubsdb", "sudo systemctl status postgresql"
    )


def test_chains_pipes_and_redirects():
    w = _w()
    out = w.run_command(
        "kubsdb",
        "systemctl --failed --no-pager; echo ---; df -h 2>/dev/null | tail -n 1",
    )
    assert "postgresql.service" in out and "failed" in out
    assert "---" in out
    assert out.strip().endswith("61% /")
    assert (
        w.run_command(
            "kubsdb", "journalctl -u postgresql | grep -i 'out of memory' | wc -l"
        )
        == "1"
    )
    assert w.run_command("kubsdb", "ss -tlnp | grep 5432") == ""
    assert "korg" in w.run_command("kubsdb", "ss -tlnp | grep 8720")


def test_generic_coreutils_are_consistent():
    w = _w()
    assert w.run_command("kubsdb", "hostname") == "kubsdb"
    assert w.run_command("kubsdb", "whoami") == "ken"
    assert w.run_command("kubsdb", "pwd") == "/home/ken"
    assert w.run_command("kubsdb", "echo $PATH") == "/usr/local/bin:/usr/bin:/bin"
    assert w.run_command("kubsdb", "echo hello") == "hello"
    assert "var" in w.run_command("kubsdb", "ls /")
    assert "backups" in w.run_command("kubsdb", "ls -la /var")
    assert "pg-2026-09-07.sql.zst" in w.run_command("kubsdb", "ls -la /srv/backup")
    assert "kmon.toml" in w.run_command("kubsdb", "ls /etc/kmon")
    assert "No such file" in w.run_command("kubsdb", "ls /nonexistent")
    assert "shm" in w.run_command("kubsdb", "ls /dev")
    assert "tmpfs on /dev/shm" in w.run_command("kubsdb", "mount | grep shm")
    assert (
        w.run_command("kubsdb", "ls -la /var/lib/postgresql/ 2>/dev/null")
        == "ls: cannot access '/var/lib/postgresql': No such file or directory"
    )
    assert (
        "cat /etc/hostname" and w.run_command("kubsdb", "cat /etc/hostname") == "kubsdb"
    )
    assert "0.31" in w.run_command("kubsdb", "cat /proc/loadavg")
    assert 'listen = ":9103"' == w.run_command("kubsdb", "cat /etc/kmon/kmon.toml")
    assert "No such file" in w.read_file("kubsdb", "/nope")
    assert "korg" in w.run_command(
        "kubsdb", "ps aux"
    ) and "postgres" not in w.run_command("kubsdb", "ps aux | grep -v grep")
    assert "Mem:" in w.run_command("kubsdb", "free -m")
    assert "Linux kubsdb" in w.run_command("kubsdb", "uname -a")


def test_systemctl_and_journalctl_derive_from_fixture():
    w = _w()
    assert w.run_command("kubsdb", "systemctl is-active postgresql") == "failed"
    assert w.run_command("kubsdb", "systemctl is-active korg") == "active"
    assert w.run_command("kubsdb", "systemctl is-active nginx") == "inactive"
    assert "postgresql.service" in w.run_command(
        "kubsdb", "systemctl list-units --failed"
    )
    assert "korg.service" not in w.run_command("kubsdb", "systemctl --failed")
    assert "korg.service" in w.run_command(
        "kubsdb", "systemctl list-units --type=service"
    )
    assert "could not be found" in w.run_command("kubsdb", "systemctl status nginx")
    assert "Access denied" in w.run_command("kubsdb", "systemctl restart postgresql")
    assert "Out of memory" in w.run_command("kubsdb", "journalctl -p err -n 50")
    assert "Out of memory" in w.run_command("kubsdb", "journalctl --since '1 hour ago'")
    assert w.run_command("kubsdb", "journalctl -u nginx -n 20") == "-- No entries --"
    assert w.run_command("kubsdb", "journalctl -k") == "-- No entries --"


def test_absent_things_fail_like_bash():
    w = _w()
    assert "Could not resolve hostname" in w.run_command("cleo", "ls /gratch/images")
    assert "command not found" in w.run_command("kubsdb", "smartctl -H /dev/nvme0")
    assert "command not found" in w.run_command("kubsdb", "frobnicate --now")
    assert "unknown command" in w.run_command("kubsdb", "docker frob")
    assert "no manifest entry" in w.manifest_lookup("kbeacon")
    assert "port=8720" in w.manifest_lookup("kubsdb")  # host lookup lists its services
    assert "#1788" in w.korg_search("kagviz stopped")
    assert w.dispatch("run_command", {"host": "kubsdb"}).startswith(
        "error: bad arguments"
    )
    assert len(w.calls) == 1
