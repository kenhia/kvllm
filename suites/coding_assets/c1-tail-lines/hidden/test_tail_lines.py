import os
import tempfile

from tail_lines import tail_lines


def _write(content):
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def test_basic():
    p = _write("a\nb\nc\n")
    assert tail_lines(p, 2) == ["b", "c"]


def test_n_zero():
    p = _write("a\nb\nc\n")
    assert tail_lines(p, 0) == []


def test_n_negative():
    p = _write("a\nb\n")
    assert tail_lines(p, -1) == []


def test_n_larger_than_file():
    p = _write("a\nb\n")
    assert tail_lines(p, 10) == ["a", "b"]


def test_empty_file():
    p = _write("")
    assert tail_lines(p, 3) == []


def test_no_final_newline():
    p = _write("x\ny\nz")
    assert tail_lines(p, 2) == ["y", "z"]


def test_all_lines():
    p = _write("one\ntwo\nthree\n")
    assert tail_lines(p, 3) == ["one", "two", "three"]
