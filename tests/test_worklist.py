from datetime import date

from switch2db.models import PhysicalRelease, Region, Sku, Title, TitleStatus
from switch2db.worklist import (
    build_work_queue,
    find_titles_missing_regions,
    list_missing_regions,
    list_skus_without_source,
    list_titles_by_status,
    list_titles_to_complete,
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
