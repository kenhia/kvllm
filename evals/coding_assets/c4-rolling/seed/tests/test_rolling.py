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
        r.add(x)  # 1 is evicted; window holds 2, 3, 4
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
