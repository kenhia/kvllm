import os
import subprocess
import sys

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dumon.py"
)


def _run(threshold, stdin_text):
    r = subprocess.run(
        [sys.executable, SCRIPT, str(threshold)],
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def test_basic_threshold_and_order():
    stdin = "2097152\t/var/log\n512\t/etc\n1572864\t/home\n"
    assert _run(1, stdin) == ["2048 MB  /var/log", "1536 MB  /home"]


def test_two_spaces_before_path():
    assert _run(0, "2097152\t/a\n")[0] == "2048 MB  /a"


def test_strictly_greater():
    # exactly 1 MB (1024 KiB) is NOT > 1
    assert _run(1, "1024\t/exactly-1mb\n") == []


def test_tie_broken_by_path():
    stdin = "2097152\t/b\n2097152\t/a\n"
    assert _run(1, stdin) == ["2048 MB  /b".replace("/b", "/a"), "2048 MB  /b"]


def test_rounding_to_nearest_mb():
    # 1075000 KiB / 1024 = 1049.8 -> rounds to 1050
    assert _run(1, "1075000\t/x\n") == ["1050 MB  /x"]


def test_blank_lines_ignored():
    assert _run(1, "\n2097152\t/a\n\n") == ["2048 MB  /a"]
