from datetime import date

import pytest

from switch2db.catalog import (
    CatalogEntry,
    build_catalog,
    build_catalog_entry,
    convert_unix_timestamp_to_date,
    find_platform_release_date,
    format_release_date,
    is_catalog_candidate,
    list_publishers,
)
from switch2db.igdb_models import IgdbGame, IgdbReleaseDate

SWITCH2_PLATFORM_ID = 508


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

    assert [entry.name for entry in build_catalog(games, SWITCH2_PLATFORM_ID)] == ["Base Game"]


def test_build_catalog_keeps_bundles_for_their_release_dates() -> None:
    games = [build_game(1, "Base Game", "Main Game"), build_game(2, "Collection", "Bundle")]

    assert [entry.name for entry in build_catalog(games, SWITCH2_PLATFORM_ID)] == ["Base Game", "Collection"]


def test_list_publishers_keeps_only_publishers_without_repeating(igdb_game: IgdbGame) -> None:
    assert list_publishers(igdb_game) == ["Example Publisher"]


def test_convert_unix_timestamp_to_date_success() -> None:
    assert convert_unix_timestamp_to_date(1749081600) == date(2025, 6, 5)


def build_release(
    date_format: str, *, platform: int = SWITCH2_PLATFORM_ID, timestamp: int | None = 1787184000
) -> IgdbReleaseDate:
    """Lanzamiento de IGDB del 20-08-2026 (año 2026, mes 8) con la precisión indicada."""
    return IgdbReleaseDate.model_validate(
        {
            "platform": platform,
            "date": timestamp,
            "y": 2026,
            "m": 8,
            "date_format": {"id": 0, "format": date_format},
        }
    )


@pytest.mark.parametrize(
    "date_format,expected",
    [
        ("YYYYMMDD", "2026-08-20"),
        ("YYYYMM", "2026-08"),
        ("YYYYQ3", "2026-Q3"),
        ("YYYY", "2026"),
        ("TBD", None),
    ],
)
def test_format_release_date_keeps_the_precision_of_igdb(date_format: str, expected: str | None) -> None:
    assert format_release_date(build_release(date_format)) == expected


def test_format_release_date_returns_none_without_timestamp() -> None:
    assert format_release_date(build_release("YYYYMMDD", timestamp=None)) is None


def test_find_platform_release_date_ignores_other_platforms(igdb_game: IgdbGame) -> None:
    assert find_platform_release_date(igdb_game, SWITCH2_PLATFORM_ID) == "2025-06-05"


def test_find_platform_release_date_prefers_the_earliest_known_date() -> None:
    game = IgdbGame(
        id=1,
        name="Regional Game",
        release_dates=[
            build_release("YYYYQ3", timestamp=1790726400),
            build_release("YYYYMMDD"),
            build_release("TBD", timestamp=None),
        ],
    )

    assert find_platform_release_date(game, SWITCH2_PLATFORM_ID) == "2026-08-20"


def test_find_platform_release_date_returns_none_without_a_date_on_the_platform() -> None:
    game = IgdbGame(id=1, name="PC Game", release_dates=[build_release("YYYYMMDD", platform=6)])

    assert find_platform_release_date(game, SWITCH2_PLATFORM_ID) is None


def test_build_catalog_entry_success(igdb_game: IgdbGame) -> None:
    assert build_catalog_entry(igdb_game, SWITCH2_PLATFORM_ID) == CatalogEntry(
        igdb_id=12345,
        name="Example Game",
        game_type="Main Game",
        release_date="2025-06-05",
        publishers="Example Publisher",
    )


def test_build_catalog_entry_leaves_missing_data_empty() -> None:
    entry = build_catalog_entry(IgdbGame(id=1, name="Bare Game"), SWITCH2_PLATFORM_ID)

    assert entry.game_type is None
    assert entry.release_date is None
    assert entry.publishers is None


def test_build_catalog_sorts_by_name_ignoring_case() -> None:
    games = [IgdbGame(id=1, name="beta"), IgdbGame(id=2, name="Alpha"), IgdbGame(id=3, name="gamma")]

    assert [entry.name for entry in build_catalog(games, SWITCH2_PLATFORM_ID)] == ["Alpha", "beta", "gamma"]


def test_build_catalog_returns_empty_list_without_games() -> None:
    assert build_catalog([], SWITCH2_PLATFORM_ID) == []


def test_build_catalog_entry_keeps_the_game_an_edition_belongs_to() -> None:
    edition = IgdbGame(id=2, name="Example Game: Deluxe Edition", version_parent=1)

    assert build_catalog_entry(edition, SWITCH2_PLATFORM_ID).version_parent == 1
