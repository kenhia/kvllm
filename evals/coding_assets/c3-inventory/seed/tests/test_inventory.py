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
