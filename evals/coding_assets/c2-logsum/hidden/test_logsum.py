import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logsum.py"
)


def _run(log_text):
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write(log_text)
        path = f.name
    r = subprocess.run(
        [sys.executable, SCRIPT, path], capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def test_ordering_and_ties():
    log = (
        "2026-07-01 00:00:00 INFO a\n"
        "2026-07-01 00:00:01 ERROR disk full\n"
        "2026-07-01 00:00:02 ERROR disk full\n"
        "2026-07-01 00:00:03 WARN w\n"
        "2026-07-01 00:00:04 INFO a\n"
        "2026-07-01 00:00:05 ERROR timeout\n"
        "2026-07-01 00:00:06 DEBUG d\n"
    )
    assert _run(log) == [
        "ERROR 3",
        "INFO 2",
        "DEBUG 1",
        "WARN 1",
        "top errors:",
        "2× disk full",
        "1× timeout",
    ]


def test_blank_lines_ignored():
    log = "\n2026-07-01 00:00:00 INFO x\n\n2026-07-01 00:00:01 INFO y\n\n"
    assert _run(log) == ["INFO 2", "top errors:"]


def test_top_errors_capped_at_three():
    lines = []
    # counts: e5=5, e4=4, e3=3, e2=2, e1=1  -> top 3 are e5,e4,e3
    for msg, n in [("e5", 5), ("e4", 4), ("e3", 3), ("e2", 2), ("e1", 1)]:
        for _ in range(n):
            lines.append(f"2026-07-01 00:00:00 ERROR {msg}")
    out = _run("\n".join(lines) + "\n")
    assert out[0] == "ERROR 15"
    assert out[1] == "top errors:"
    assert out[2:] == ["5× e5", "4× e4", "3× e3"]


def test_error_message_tie_alpha():
    log = "2026-07-01 00:00:00 ERROR beta\n2026-07-01 00:00:01 ERROR alpha\n"
    out = _run(log)
    assert out[out.index("top errors:") + 1 :] == ["1× alpha", "1× beta"]
