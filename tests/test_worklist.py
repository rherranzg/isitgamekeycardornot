from datetime import UTC, date, datetime

import pytest

from switch2db.models import PhysicalRelease, Region, Sku, Title, TitleStatus
from switch2db.worklist import (
    build_work_queue,
    drop_checked_since,
    find_titles_missing_regions,
    list_missing_regions,
    list_skus_without_source,
    list_titles_by_status,
    list_titles_to_complete,
    list_upcoming_titles,
    release_period_end,
)


def build_no_box(region: Region, source_url: str | None) -> PhysicalRelease:
    """ "No box in that region" entry for example-game."""
    return PhysicalRelease.model_validate(
        {
            "title_id": "example-game",
            "has_physical_release": False,
            "region": region,
            "evidence": "official" if source_url else "unconfirmed",
            "source_url": source_url,
            "checked_at": "2026-10-09",
        }
    )


def test_list_titles_by_status_keeps_file_order(title: Title) -> None:
    to_refresh = title.model_copy(update={"title_id": "refresh-game", "status": TitleStatus.REFRESH})
    second_pending = title.model_copy(update={"title_id": "another-game"})

    assert list_titles_by_status([title, to_refresh, second_pending], TitleStatus.PENDING) == [
        "example-game",
        "another-game",
    ]


def test_list_titles_to_complete_puts_the_least_recently_checked_first(title: Title) -> None:
    older = title.model_copy(update={"title_id": "older-game", "last_checked_at": date(2026, 9, 1)})
    never = title.model_copy(update={"title_id": "never-game", "last_checked_at": None})
    completed = title.model_copy(update={"title_id": "completed-game", "status": TitleStatus.COMPLETED})

    assert list_titles_to_complete([title, older, completed, never]) == [
        "never-game",
        "older-game",
        "example-game",
    ]


def test_list_titles_to_complete_orders_checks_with_time_after_day_only_checks_of_earlier_days(
    title: Title,
) -> None:
    with_time = title.model_copy(
        update={"title_id": "timed-game", "last_checked_at": datetime(2026, 9, 13, 10, 0, tzinfo=UTC)}
    )
    earlier_time = title.model_copy(
        update={"title_id": "early-game", "last_checked_at": datetime(2026, 9, 13, 9, 0, tzinfo=UTC)}
    )

    assert list_titles_to_complete([with_time, title, earlier_time]) == [
        "example-game",
        "early-game",
        "timed-game",
    ]


def test_list_skus_without_source_returns_sku_ids_without_source_url(
    eu_key_card_sku: Sku, sku_without_source: Sku
) -> None:
    assert list_skus_without_source([eu_key_card_sku, sku_without_source]) == ["kr-example-game-standard"]


def test_list_missing_regions_returns_regions_without_sku(eu_key_card_sku: Sku) -> None:
    assert list_missing_regions("example-game", [eu_key_card_sku], []) == ["NA", "JP", "KR", "ASIA"]


def test_list_missing_regions_counts_only_sourced_no_box_regions(eu_key_card_sku: Sku) -> None:
    releases = [build_no_box(Region.KR, "https://example.com/kr"), build_no_box(Region.ASIA, None)]

    assert list_missing_regions("example-game", [eu_key_card_sku], releases) == ["NA", "JP", "ASIA"]


def test_find_titles_missing_regions_skips_titles_without_any_sku(title: Title, eu_key_card_sku: Sku) -> None:
    untouched = title.model_copy(update={"title_id": "untouched-game"})

    assert find_titles_missing_regions([title, untouched], [eu_key_card_sku], []) == {
        "example-game": ["NA", "JP", "KR", "ASIA"]
    }


def test_build_work_queue_splits_titles_by_status_and_skus_by_source(
    title: Title, eu_key_card_sku: Sku, sku_without_source: Sku
) -> None:
    untouched = title.model_copy(
        update={"title_id": "untouched-game", "status": TitleStatus.NEW, "last_checked_at": None}
    )
    to_refresh = title.model_copy(update={"title_id": "refresh-game", "status": TitleStatus.REFRESH})

    queue = build_work_queue([title, untouched, to_refresh], [eu_key_card_sku, sku_without_source], [])

    assert queue.titles_to_research == ["untouched-game"]
    assert queue.titles_to_refresh == ["refresh-game"]
    assert queue.titles_to_complete == ["example-game"]
    assert queue.skus_without_source == ["kr-example-game-standard"]


@pytest.mark.parametrize(
    ("release_date", "expected"),
    [
        ("2026-11-20", date(2026, 11, 20)),
        ("2026-02", date(2026, 2, 28)),
        ("2026-12", date(2026, 12, 31)),
        ("2026-Q3", date(2026, 9, 30)),
        ("2026-Q4", date(2026, 12, 31)),
        ("2027", date(2027, 12, 31)),
    ],
)
def test_release_period_end_returns_the_last_day_of_the_period(release_date: str, expected: date) -> None:
    assert release_period_end(release_date) == expected


def test_list_upcoming_titles_sorts_by_period_end_and_skips_past_and_undated_titles(title: Title) -> None:
    def dated(title_id: str, release_date: str | None) -> Title:
        return title.model_copy(update={"title_id": title_id, "release_date": release_date})

    titles = [
        dated("next-year", "2027"),
        dated("this-month", "2026-11"),
        dated("released", "2026-11-01"),
        dated("undated", None),
        dated("end-of-month", "2026-11-30"),
        dated("today", "2026-11-02"),
        dated("past-quarter", "2026-Q3"),
    ]

    upcoming = list_upcoming_titles(titles, date(2026, 11, 2), limit=3)

    assert [upcoming_title.title_id for upcoming_title in upcoming] == ["today", "end-of-month", "this-month"]


def test_drop_checked_since_drops_titles_checked_on_or_after_the_day(title: Title) -> None:
    on_the_day = title.model_copy(
        update={"title_id": "on-the-day", "last_checked_at": datetime(2026, 10, 26, 22, 0, tzinfo=UTC)}
    )
    before = title.model_copy(update={"title_id": "before", "last_checked_at": date(2026, 10, 25)})
    never = title.model_copy(update={"title_id": "never", "last_checked_at": None})

    kept = drop_checked_since([on_the_day, before, never], date(2026, 10, 26))

    assert [kept_title.title_id for kept_title in kept] == ["before", "never"]
