import pytest
from rolling import RollingAverage


def test_window_must_be_positive():
    with pytest.raises(ValueError):
        RollingAverage(0)


def test_empty_value_is_zero():
    assert RollingAverage(3).value() == 0.0


def test_average_within_window():
    r = RollingAverage(3)
    r.add(1)
    r.add(2)
    r.add(3)
    assert r.value() == pytest.approx(2.0)


def test_evicts_oldest_when_full():
    r = RollingAverage(3)
    for x in (1, 2, 3, 4):
        r.add(x)
    assert r.value() == pytest.approx(3.0)


def test_window_of_one_keeps_last():
    r = RollingAverage(1)
    r.add(5)
    assert r.value() == pytest.approx(5.0)
    r.add(6)
    assert r.value() == pytest.approx(6.0)


def test_reset_returns_old_average_then_clears():
    r = RollingAverage(2)
    r.add(2)
    r.add(4)
    assert r.reset() == pytest.approx(3.0)
    assert r.value() == 0.0


# --- deeper probes ---


def test_negative_window_raises():
    with pytest.raises(ValueError):
        RollingAverage(-3)


def test_window_of_one_eviction_sequence():
    r = RollingAverage(1)
    for x in (1, 2, 3):
        r.add(x)
    assert r.value() == pytest.approx(3.0)


def test_exact_eviction_order():
    r = RollingAverage(2)
    for x in (1, 2, 3):
        r.add(x)  # holds 2, 3
    assert r.value() == pytest.approx(2.5)


def test_reset_on_empty_returns_zero():
    r = RollingAverage(2)
    assert r.reset() == 0.0


def test_usable_after_reset():
    r = RollingAverage(2)
    r.add(10)
    r.reset()
    r.add(4)
    r.add(8)
    assert r.value() == pytest.approx(6.0)
