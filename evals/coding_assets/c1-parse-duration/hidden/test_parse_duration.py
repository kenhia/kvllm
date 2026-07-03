import pytest
from parse_duration import parse_duration


def test_hours_minutes():
    assert parse_duration("1h30m") == 5400


def test_seconds_suffix():
    assert parse_duration("90s") == 90


def test_hours_only():
    assert parse_duration("2h") == 7200


def test_bare_seconds():
    assert parse_duration("45") == 45


def test_minutes_seconds():
    assert parse_duration("30m15s") == 1815


def test_zero():
    assert parse_duration("0") == 0
    assert parse_duration("0s") == 0


def test_wrong_order_raises():
    with pytest.raises(ValueError):
        parse_duration("1m30h")


def test_invalid_raises():
    with pytest.raises(ValueError):
        parse_duration("")
    with pytest.raises(ValueError):
        parse_duration("5x")
