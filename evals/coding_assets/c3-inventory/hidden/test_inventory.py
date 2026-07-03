from inventory import Inventory


def test_add():
    inv = Inventory()
    inv.add("apple", 2)
    assert inv.report() == {"apple": 2}


def test_two_instances_independent():
    a = Inventory()
    a.add("x", 1)
    b = Inventory()
    assert b.report() == {}


def test_remove_missing_is_noop():
    inv = Inventory()
    inv.remove("ghost", 1)
    assert inv.report() == {}


def test_remove_more_than_present_clamps():
    inv = Inventory()
    inv.add("apple", 1)
    inv.remove("apple", 5)
    assert inv.report() == {}


# --- deeper probes (not in the visible suite) ---


def test_three_instances_independent():
    a, b, c = Inventory(), Inventory(), Inventory()
    a.add("x", 3)
    b.add("y", 1)
    assert c.report() == {}
    assert a.report() == {"x": 3}
    assert b.report() == {"y": 1}


def test_remove_then_readd():
    inv = Inventory()
    inv.add("a", 2)
    inv.remove("a", 2)
    assert inv.report() == {}
    inv.add("a", 1)
    assert inv.report() == {"a": 1}


def test_partial_remove():
    inv = Inventory()
    inv.add("a", 5)
    inv.remove("a", 2)
    assert inv.report() == {"a": 3}


def test_add_accumulates():
    inv = Inventory()
    inv.add("a")
    inv.add("a")
    inv.add("a")
    assert inv.report() == {"a": 3}
