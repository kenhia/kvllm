import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jsonmerge.py"
)


def _run(*objs):
    paths = []
    for o in objs:
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(o, f)
        f.close()
        paths.append(f.name)
    r = subprocess.run(
        [sys.executable, SCRIPT, *paths], capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_deep_merge_recurses_dicts():
    out = _run({"a": 1, "nested": {"x": 1}}, {"nested": {"y": 2}, "a": 5})
    assert json.loads(out) == {"a": 5, "nested": {"x": 1, "y": 2}}


def test_later_scalar_wins():
    assert json.loads(_run({"k": 1}, {"k": 2})) == {"k": 2}


def test_array_replaces_not_merges():
    assert json.loads(_run({"xs": [1, 2]}, {"xs": [3]})) == {"xs": [3]}


def test_type_mismatch_replaces():
    assert json.loads(_run({"k": {"a": 1}}, {"k": 5})) == {"k": 5}


def test_three_files():
    out = _run({"a": 1}, {"b": 2}, {"a": 9, "c": 3})
    assert json.loads(out) == {"a": 9, "b": 2, "c": 3}


def test_output_is_sorted_and_indented():
    out = _run({"b": 1, "a": 2})
    assert out.rstrip("\n") == json.dumps({"a": 2, "b": 1}, indent=2, sort_keys=True)
