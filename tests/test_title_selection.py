from datetime import date

import pytest

from switch2db.catalog import CatalogEntry
from switch2db.models import ExcludedTitle, Title, TitleStatus
from switch2db.title_selection import (
    build_new_title,
    is_settled_release_date,
    refresh_release_dates,
    select_new_titles,
)

TODAY = date(2026, 9, 24)


def build_entry(
    igdb_id: int, name: str, publishers: str | None = "Example Publisher", release_date: str | None = None
) -> CatalogEntry:
    """IGDB catalog entry ready to become a title."""
    return CatalogEntry(
        igdb_id=igdb_id, name=name, game_type="Main Game", release_date=release_date, publishers=publishers
    )


def test_build_new_title_slugifies_the_name_and_leaves_it_without_investigar() -> None:
    title = build_new_title(build_entry(1, "Metroid Prime 4: Beyond"), set())

    assert title.title_id == "metroid-prime-4-beyond"
    assert title.status == TitleStatus.NEW
    assert title.publisher == "Example Publisher"


def test_build_new_title_keeps_publisher_null_when_igdb_has_none() -> None:
    assert build_new_title(build_entry(1, "Bare Game", publishers=None), set()).publisher is None


def test_build_new_title_adds_a_suffix_when_the_slug_is_taken() -> None:
    assert build_new_title(build_entry(1, "Example Game"), {"example-game"}).title_id == "example-game-2"


def test_select_new_titles_skips_igdb_ids_already_in_titles(title: Title) -> None:
    catalog = [build_entry(12345, "Example Game"), build_entry(67890, "Other Game")]

    new_titles = select_new_titles(catalog, [title], [], None)

    assert [new.igdb_id for new in new_titles] == [67890]


def test_select_new_titles_respects_the_limit_in_catalog_order() -> None:
    catalog = [build_entry(1, "Alpha"), build_entry(2, "Beta"), build_entry(3, "Gamma")]

    assert [new.name for new in select_new_titles(catalog, [], [], 2)] == ["Alpha", "Beta"]


def test_select_new_titles_adds_nothing_when_the_limit_is_zero() -> None:
    assert select_new_titles([build_entry(1, "Alpha")], [], [], 0) == []


def test_select_new_titles_does_not_repeat_slugs_between_new_titles() -> None:
    catalog = [build_entry(1, "Example Game"), build_entry(2, "Example Game")]

    assert [new.title_id for new in select_new_titles(catalog, [], [], None)] == [
        "example-game",
        "example-game-2",
    ]


def test_select_new_titles_skips_excluded_igdb_ids() -> None:
    catalog = [build_entry(1, "Alpha"), build_entry(2, "Beta")]
    excluded = [ExcludedTitle(igdb_id=1, name="Alpha", reason="Solo en caja dentro de una recopilación")]

    assert [new.igdb_id for new in select_new_titles(catalog, [], excluded, None)] == [2]


def test_select_new_titles_does_not_count_excluded_games_against_the_limit() -> None:
    catalog = [build_entry(1, "Alpha"), build_entry(2, "Beta"), build_entry(3, "Gamma")]
    excluded = [ExcludedTitle(igdb_id=1, name="Alpha", reason="Solo en caja dentro de una recopilación")]

    assert [new.name for new in select_new_titles(catalog, [], excluded, 1)] == ["Beta"]


def test_build_new_title_copies_the_release_date() -> None:
    assert build_new_title(build_entry(1, "Alpha", release_date="2026-Q3"), set()).release_date == "2026-Q3"


@pytest.mark.parametrize(
    "release_date,expected",
    [
        ("2026-09-24", True),
        ("2025-06-05", True),
        ("2026-09-25", False),
        ("2026-09", False),
        ("2026-Q3", False),
        ("2026", False),
        (None, False),
    ],
)
def test_is_settled_release_date_only_for_past_exact_days(release_date: str | None, expected: bool) -> None:
    assert is_settled_release_date(release_date, TODAY) is expected


@pytest.mark.parametrize("stored", [None, "2026-Q4", "2026-12-01"])
def test_refresh_release_dates_takes_the_catalog_date_while_it_can_change(
    title: Title, stored: str | None
) -> None:
    titles = [title.model_copy(update={"release_date": stored})]
    catalog = [build_entry(title.igdb_id, title.name, release_date="2026-11-20")]

    assert refresh_release_dates(titles, catalog, TODAY)[0].release_date == "2026-11-20"


def test_refresh_release_dates_keeps_a_past_exact_date(title: Title) -> None:
    titles = [title.model_copy(update={"release_date": "2025-06-05"})]
    catalog = [build_entry(title.igdb_id, title.name, release_date="2025-06-06")]

    assert refresh_release_dates(titles, catalog, TODAY)[0].release_date == "2025-06-05"


def test_refresh_release_dates_keeps_a_manual_date_when_the_catalog_has_none(title: Title) -> None:
    titles = [title.model_copy(update={"release_date": "2026-11-05"})]
    catalog = [build_entry(title.igdb_id, title.name, release_date=None)]

    assert refresh_release_dates(titles, catalog, TODAY)[0].release_date == "2026-11-05"


def test_refresh_release_dates_keeps_titles_missing_from_the_catalog(title: Title) -> None:
    titles = [title.model_copy(update={"release_date": "2026-Q4"})]

    assert refresh_release_dates(titles, [], TODAY) == titles


def test_select_new_titles_skips_editions_whose_base_game_is_on_switch_2(title: Title) -> None:
    catalog = [
        build_entry(1, "Alpha"),
        build_entry(2, "Alpha: Deluxe Edition").model_copy(update={"version_parent": 1}),
        build_entry(3, "Example Game: Gold Edition").model_copy(update={"version_parent": title.igdb_id}),
    ]

    assert [new.name for new in select_new_titles(catalog, [title], [], None)] == ["Alpha"]


def test_select_new_titles_keeps_editions_whose_base_game_is_not_on_switch_2() -> None:
    catalog = [build_entry(2, "Beta: Signature Edition").model_copy(update={"version_parent": 1})]

    assert [new.name for new in select_new_titles(catalog, [], [], None)] == ["Beta: Signature Edition"]


def test_select_new_titles_skips_bundles() -> None:
    catalog = [
        build_entry(1, "Alpha"),
        build_entry(2, "Alpha Collection").model_copy(update={"game_type": "Bundle"}),
    ]

    assert [new.name for new in select_new_titles(catalog, [], [], None)] == ["Alpha"]


def test_refresh_release_dates_updates_bundles_added_by_hand(title: Title) -> None:
    bundle = build_entry(title.igdb_id, title.name, release_date="2026-12").model_copy(
        update={"game_type": "Bundle"}
    )

    assert refresh_release_dates([title], [bundle], TODAY)[0].release_date == "2026-12"
