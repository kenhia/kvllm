import pytest
from parse_size import parse_size


def test_bare_int():
    assert parse_size("42") == 42


def test_kilo():
    assert parse_size("3K") == 3072


def test_mega():
    assert parse_size("512M") == 536870912


def test_giga_float():
    assert parse_size("1.5G") == 1610612736


def test_trailing_b():
    assert parse_size("1.5GB") == 1610612736
    assert parse_size("512MB") == 536870912


def test_case_insensitive():
    assert parse_size("3k") == 3072
    assert parse_size("512m") == 536870912


def test_whitespace():
    assert parse_size("  10K  ") == 10240


def test_invalid_raises():
    with pytest.raises(ValueError):
        parse_size("nonsense")
    with pytest.raises(ValueError):
        parse_size("")
    with pytest.raises(ValueError):
        parse_size("1.2.3G")
