from stats import Stats


def test_mean():
    s = Stats()
    s.add(2)
    s.add(4)
    assert s.mean() == 3.0


def test_count():
    s = Stats()
    s.add(1)
    s.add(1)
    s.add(1)
    assert s.count() == 3


def test_instances_independent():
    a = Stats()
    a.add(10)
    b = Stats()
    assert b.count() == 0
    assert b.mean() == 0.0


def test_empty_mean_is_zero():
    assert Stats().mean() == 0.0
