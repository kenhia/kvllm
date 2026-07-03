from dedupe import dedupe


def test_basic_order_preserved():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_empty():
    assert dedupe([]) == []


def test_all_dupes():
    assert dedupe([7, 7, 7]) == [7]


def test_no_dupes():
    assert dedupe([1, 2, 3]) == [1, 2, 3]


def test_key_lower():
    assert dedupe(["A", "a", "B", "b"], key=str.lower) == ["A", "B"]


def test_key_keeps_first():
    assert dedupe(["Apple", "apple", "APPLE"], key=str.lower) == ["Apple"]


def test_strings_default():
    assert dedupe(["x", "y", "x", "z", "y"]) == ["x", "y", "z"]
