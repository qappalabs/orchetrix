from Utils.data_formatters import parse_age_to_seconds


def test_single_units():
    assert parse_age_to_seconds("5d") == 432000
    assert parse_age_to_seconds("12h") == 43200
    assert parse_age_to_seconds("30m") == 1800
    assert parse_age_to_seconds("45s") == 45


def test_years_and_months():
    assert parse_age_to_seconds("1y") == 31536000
    assert parse_age_to_seconds("2mo") == 5184000


def test_compound():
    assert parse_age_to_seconds("5d2h30m") == 441000


def test_invalid_returns_zero():
    assert parse_age_to_seconds("") == 0
    assert parse_age_to_seconds("xyz") == 0
    assert parse_age_to_seconds(None) == 0
