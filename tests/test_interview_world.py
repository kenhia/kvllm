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


def test_fixture_implies_a_filesystem():
    w = _w()
    assert "pg-2026-09-07.sql.zst" in w.run_command(
        "kubsdb", "ls -la /srv/backup/ | tail -10"
    )
    assert "backup" in w.run_command("kubsdb", "ls -la /srv/")
    assert "korg.service" in w.run_command("kubsdb", "ls /etc/systemd/system")
    assert "ExecStart=/usr/local/bin/korg" in w.run_command(
        "kubsdb", "cat /etc/systemd/system/korg.service"
    )
    assert "korg" in w.run_command("kubsdb", "ls -la /usr/local/bin/")
    assert "managed by k-homelab" in w.read_file("kubsdb", "/usr/local/bin/korg")
    assert (
        w.run_command("kubsdb", "which docker korg restic")
        == "/usr/bin/docker\n/usr/local/bin/korg"
    )
    assert w.run_command("kubsdb", "crontab -l") == "no crontab for ken"
    assert "zst" == w.run_command("kubsdb", "cat /srv/backup/pg-2026-09-07.sql.zst")


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


def test_world_never_contradicts_itself_and_refuses_scripts():
    w = World(
        {
            "hosts": {
                "kubsdb": {
                    "commands": {
                        "du -sh /var/lib/docker": "1.3T\t/var/lib/docker",
                        "docker ps": "CONTAINER ID IMAGE STATUS NAMES",
                        "nvidia-smi --query-gpu=memory.used --format=csv": "memory.used [MiB]\n30846 MiB",
                    }
                }
            },
            "manifest": {},
            "korg": [],
        }
    )
    assert w.run_command("kubsdb", "du -sh /var/lib/docker") == "1.3T\t/var/lib/docker"
    assert w.run_command("kubsdb", "du -sh /var/lib").startswith("1.3T")
    assert (
        w.run_command("kubsdb", "du -xh --max-depth=1 / | sort -rh | head -3")
        .splitlines()[0]
        .startswith("1.3T")
    )
    assert "overlay2" in w.run_command("kubsdb", "ls -la /var/lib/docker")
    assert "No such file" in w.run_command("kubsdb", "du -sh /nope")
    assert "read-only session runs simple commands only" in w.run_command(
        "kubsdb", "for d in /var/lib/docker/*/; do du -sh $d; done"
    )
    assert "read-only session runs simple commands only" in w.run_command(
        "kubsdb", "bash -c 'echo > /dev/tcp/cleo/22'"
    )
    assert "read-only session runs simple commands only" in w.run_command(
        "kubsdb", "python3 -c 'print(1)'"
    )
    out = w.run_command("kubsdb", "nvidia-smi -L")
    assert out.startswith("nvidia-smi: unsupported invocation") and "--query-gpu" in out


def test_listed_files_are_real_and_loops_are_refused_by_position():
    w = World(
        {
            "hosts": {
                "kubsdb": {
                    "commands": {
                        "ls -la /srv/backup": "-rw-r----- 1 postgres postgres 2043118820 Sep  7 02:14 pg-2026-09-07.sql.zst",
                        "journalctl -u nightly-backup": "Sep 07 02:14:41 kubsdb nightly-backup[5120]: OK (2m40s)",
                    }
                }
            },
            "manifest": {},
            "korg": [],
        }
    )
    assert "Size: 2043118820" in w.run_command(
        "kubsdb", "stat /srv/backup/pg-2026-09-07.sql.zst"
    )
    assert (
        w.run_command("kubsdb", "find /srv/backup -maxdepth 1 -type f")
        == "/srv/backup/pg-2026-09-07.sql.zst"
    )
    assert "pg-2026-09-07" in w.run_command("kubsdb", "ls -lab /srv/backup")
    assert "binary data" in w.run_command(
        "kubsdb", "head -c 4 /srv/backup/pg-2026-09-07.sql.zst"
    )
    assert "OK (2m40s)" in w.run_command(
        "kubsdb",
        "journalctl -u nightly-backup --since '2026-09-07 02:00' --until '2026-09-07 03:00'",
    )
    assert "simple commands only" in w.run_command(
        "kubsdb", "for f in /srv/backup/*; do stat $f; done"
    )
    assert "simple commands only" in w.run_command(
        "kubsdb", "ls /srv; while true; do sleep 1; done"
    )


def test_wrapper_targets_exist():
    w = _w()
    assert "binary data" in w.run_command("kubsdb", "cat /opt/korg/korg")
    assert "korg" in w.run_command("kubsdb", "ls /opt")
    assert "Size:" in w.run_command("kubsdb", "stat /opt/korg/korg")


def test_singleton_binaries_and_find_predicates():
    w = _w()
    assert "61% /" in w.run_command("kubsdb", "df -hT /")
    assert "61% /" in w.run_command("kubsdb", "df -h --output=pcent /var/lib")
    assert "not supported in this session" in w.run_command(
        "kubsdb", "find / -xdev -type f -size +10M"
    )
    assert w.run_command("kubsdb", "find /srv/backup -maxdepth 1 -type f").startswith(
        "/srv/backup/"
    )


def test_whole_journal_includes_kernel_lines():
    w = World(
        {
            "hosts": {
                "kubs0": {
                    "commands": {
                        "journalctl -k": "Sep 07 01:12:04 kubs0 kernel: igc eno1: NIC Link is Down",
                        "journalctl -u kmon": "Sep 07 01:12:05 kubs0 kmon[2210]: WARN target dial timeout",
                    }
                }
            },
            "manifest": {},
            "korg": [],
        }
    )
    whole = w.run_command(
        "kubs0", "journalctl --since '2026-09-07 01:00' --until '2026-09-07 03:00'"
    )
    assert "NIC Link is Down" in whole and "dial timeout" in whole
    assert (
        w.run_command("kubs0", "journalctl -u kmon")
        == "Sep 07 01:12:05 kubs0 kmon[2210]: WARN target dial timeout"
    )


def test_grep_bre_alternation_and_timer_units():
    w = World(
        {
            "hosts": {
                "kubsdb": {
                    "commands": {
                        "journalctl -u postgresql": "Sep 07 02:52:10 kubsdb postgres[1188]: PANIC:  could not write to file: No space left on device",
                        "systemctl status nightly-backup.timer": "○ nightly-backup.timer - Nightly\n     Active: inactive (dead)",
                    }
                }
            },
            "manifest": {},
            "korg": [],
        }
    )
    assert "No space left" in w.run_command(
        "kubsdb", 'journalctl -p warning -n 100 | grep -i "disk\\|spac"'
    )
    assert "No space left" in w.run_command(
        "kubsdb", "journalctl -p warning | grep -iE 'disk|space'"
    )
    assert w.run_command("kubsdb", 'journalctl -p warning | grep -i "zzz\\|yyy"') == ""
    assert "[Timer]" in w.run_command(
        "kubsdb", "cat /etc/systemd/system/nightly-backup.timer"
    )
    assert "[Timer]" in w.run_command("kubsdb", "systemctl cat nightly-backup.timer")
