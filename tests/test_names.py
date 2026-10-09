import pytest

from switch2db.names import normalize_name


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Absolum - Nintendo Switch™ 2 Edition", "absolum"),
        ("EARTH DEFENSE FORCE5 for Nintendo Switch™ 2", "earth defense force5"),
        ("FATAL FURY: City of the Wolves - STANDARD Edition", "fatal fury city of the wolves"),
        ("Pokémon™ Pokopia", "pokemon pokopia"),
        ("Clive Barker’s Hellraiser: Revival", "clive barker s hellraiser revival"),
    ],
)
def test_normalize_name_success(name: str, expected: str) -> None:
    assert normalize_name(name) == expected


def test_normalize_name_keeps_edition_in_the_middle() -> None:
    assert (
        normalize_name("Nintendo Switch 2 Edition Upgrade Pack") == "nintendo switch 2 edition upgrade pack"
    )


def test_normalize_name_returns_empty_string_for_japanese_text() -> None:
    assert normalize_name("ドンキーコング バナンザ") == ""
