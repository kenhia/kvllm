import csv
import io
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "csvfilter.py"
)

DATA = [
    ["name", "dept", "status"],
    ["alice", "eng", "active"],
    ["bob", "eng", "inactive"],
    ["carol", "sales", "active"],
    ["dave", "sales", "active"],
    ["eve, jr", "sales", "active"],  # embedded comma -> forces quoting
]


def _run(args):
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
        csv.writer(f).writerows(DATA)
        path = f.name
    r = subprocess.run(
        [sys.executable, SCRIPT, path, *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    return list(csv.reader(io.StringIO(r.stdout)))


def test_no_conditions_returns_all():
    assert _run([]) == DATA


def test_single_condition():
    assert _run(["dept=eng"]) == [DATA[0], DATA[1], DATA[2]]


def test_multi_condition_and():
    assert _run(["dept=sales", "status=active"]) == [DATA[0], DATA[3], DATA[4], DATA[5]]


def test_no_matches_header_only():
    assert _run(["dept=marketing"]) == [DATA[0]]


def test_quoting_preserved():
    rows = _run(["name=eve, jr"])
    assert rows == [DATA[0], DATA[5]]
