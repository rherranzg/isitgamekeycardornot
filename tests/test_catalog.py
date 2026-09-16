from datetime import date

import pytest

from switch2db.catalog import (
    CatalogEntry,
    build_catalog,
    build_catalog_entry,
    convert_unix_timestamp_to_date,
    is_catalog_candidate,
    list_publishers,
)
from switch2db.igdb_models import IgdbGame


def build_game(igdb_id: int, name: str, game_type: str) -> IgdbGame:
    """Juego de IGDB con el tipo indicado, tal como llega de la API."""
    return IgdbGame.model_validate({"id": igdb_id, "name": name, "game_type": {"id": 0, "type": game_type}})


@pytest.mark.parametrize(
    "game_type,expected",
    [
        ("Main Game", True),
        ("Port", True),
        ("Remaster", True),
        ("Expanded Game", True),
        ("Standalone Expansion", True),
        (None, True),
        ("DLC", False),
        ("Pack / Addon", False),
        ("Expansion", False),
        ("Bundle", False),
        ("Season", False),
        ("Update", False),
    ],
)
def test_is_catalog_candidate_success(game_type: str | None, expected: bool) -> None:
    assert is_catalog_candidate(game_type) is expected


def test_build_catalog_drops_game_types_without_their_own_box() -> None:
    games = [
        build_game(1, "Base Game", "Main Game"),
        build_game(2, "Extra Content", "DLC"),
        build_game(3, "Season Pass", "Pack / Addon"),
        build_game(4, "Big Expansion", "Expansion"),
    ]

    assert [entry.name for entry in build_catalog(games)] == ["Base Game"]


def test_list_publishers_keeps_only_publishers_without_repeating(igdb_game: IgdbGame) -> None:
    assert list_publishers(igdb_game) == ["Example Publisher"]


def test_convert_unix_timestamp_to_date_success() -> None:
    assert convert_unix_timestamp_to_date(1749081600) == date(2025, 6, 5)


def test_convert_unix_timestamp_to_date_returns_none_without_timestamp() -> None:
    assert convert_unix_timestamp_to_date(None) is None


def test_build_catalog_entry_success(igdb_game: IgdbGame) -> None:
    assert build_catalog_entry(igdb_game) == CatalogEntry(
        igdb_id=12345,
        name="Example Game",
        game_type="Main Game",
        first_release_date=date(2025, 6, 5),
        publishers="Example Publisher",
    )


def test_build_catalog_entry_leaves_missing_data_empty() -> None:
    entry = build_catalog_entry(IgdbGame(id=1, name="Bare Game"))

    assert entry.game_type is None
    assert entry.first_release_date is None
    assert entry.publishers is None


def test_build_catalog_sorts_by_name_ignoring_case() -> None:
    games = [IgdbGame(id=1, name="beta"), IgdbGame(id=2, name="Alpha"), IgdbGame(id=3, name="gamma")]

    assert [entry.name for entry in build_catalog(games)] == ["Alpha", "beta", "gamma"]


def test_build_catalog_returns_empty_list_without_games() -> None:
    assert build_catalog([]) == []
