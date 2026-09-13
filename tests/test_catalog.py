from datetime import date

from switch2db.catalog import (
    CatalogEntry,
    build_catalog,
    build_catalog_entry,
    convert_unix_timestamp_to_date,
)
from switch2db.igdb_models import IgdbGame


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
