import pytest

from switch2db.slug import make_unique_slug, slugify


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Metroid Prime 4: Beyond", "metroid-prime-4-beyond"),
        ("Kingdom Come: Deliverance II", "kingdom-come-deliverance-ii"),
        ("Hitman: World of Assassination — Signature", "hitman-world-of-assassination-signature"),
        ("  Split/Fiction  ", "split-fiction"),
    ],
)
def test_slugify_success(name: str, expected: str) -> None:
    assert slugify(name) == expected


def test_slugify_raises_when_name_has_no_alphanumeric_characters() -> None:
    with pytest.raises(ValueError, match="No se puede generar un slug"):
        slugify("★★★")


def test_make_unique_slug_returns_base_when_free() -> None:
    assert make_unique_slug("Example Game", set()) == "example-game"


def test_make_unique_slug_appends_suffix_on_collision() -> None:
    taken = {"example-game", "example-game-2"}

    assert make_unique_slug("Example Game", taken) == "example-game-3"
