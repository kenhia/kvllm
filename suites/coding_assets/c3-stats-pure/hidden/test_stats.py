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


# --- deeper probes ---


def test_three_instances_independent():
    a, b, c = Stats(), Stats(), Stats()
    a.add(1)
    a.add(2)
    b.add(100)
    assert a.count() == 2 and a.mean() == 1.5
    assert b.count() == 1 and b.mean() == 100.0
    assert c.count() == 0 and c.mean() == 0.0


def test_reset_clears_only_this_instance():
    a = Stats()
    a.add(5)
    b = Stats()
    b.add(9)
    a.reset()
    assert a.count() == 0
    assert b.count() == 1 and b.mean() == 9.0


def test_mean_after_reset():
    s = Stats()
    s.add(3)
    s.reset()
    assert s.mean() == 0.0
    s.add(6)
    s.add(6)
    assert s.mean() == 6.0
