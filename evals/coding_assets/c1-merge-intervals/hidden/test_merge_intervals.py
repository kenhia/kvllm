from merge_intervals import merge_intervals


def _norm(result):
    # accept lists or tuples from the implementation
    return [tuple(x) for x in result]


def test_empty():
    assert _norm(merge_intervals([])) == []


def test_single():
    assert _norm(merge_intervals([(1, 4)])) == [(1, 4)]


def test_overlap():
    assert _norm(merge_intervals([(1, 3), (2, 6), (8, 10)])) == [(1, 6), (8, 10)]


def test_touching_merges():
    assert _norm(merge_intervals([(1, 2), (2, 3)])) == [(1, 3)]


def test_nested():
    assert _norm(merge_intervals([(1, 10), (2, 5), (3, 4)])) == [(1, 10)]


def test_unsorted_input():
    assert _norm(merge_intervals([(5, 9), (1, 2)])) == [(1, 2), (5, 9)]


def test_disjoint_kept():
    assert _norm(merge_intervals([(1, 2), (4, 5), (7, 8)])) == [(1, 2), (4, 5), (7, 8)]
