from switch2db.models import Sku, SkuStatus, Title, TitleStatus
from switch2db.worklist import (
    build_work_queue,
    find_titles_missing_regions,
    list_missing_regions,
    list_skus_by_status,
    list_titles_by_status,
)


def test_list_titles_by_status_keeps_file_order(title: Title) -> None:
    reviewed = title.model_copy(update={"title_id": "reviewed-game", "status": TitleStatus.REVIEWED})
    second_pending = title.model_copy(update={"title_id": "another-game"})

    assert list_titles_by_status([title, reviewed, second_pending], TitleStatus.PENDING) == [
        "example-game",
        "another-game",
    ]


def test_list_skus_by_status_returns_matching_sku_ids(eu_key_card_sku: Sku, new_sku: Sku) -> None:
    assert list_skus_by_status([eu_key_card_sku, new_sku], SkuStatus.NEW) == ["na-example-game-standard"]


def test_list_missing_regions_returns_regions_without_sku(eu_key_card_sku: Sku) -> None:
    assert list_missing_regions("example-game", [eu_key_card_sku]) == ["NA", "JP", "KR", "ASIA"]


def test_find_titles_missing_regions_skips_titles_without_any_sku(title: Title, eu_key_card_sku: Sku) -> None:
    untouched = title.model_copy(update={"title_id": "untouched-game"})

    assert find_titles_missing_regions([title, untouched], [eu_key_card_sku]) == {
        "example-game": ["NA", "JP", "KR", "ASIA"]
    }


def test_build_work_queue_splits_titles_and_skus_by_status(
    title: Title, eu_key_card_sku: Sku, new_sku: Sku, pending_sku: Sku
) -> None:
    untouched = title.model_copy(update={"title_id": "untouched-game", "status": TitleStatus.NEW})

    queue = build_work_queue([title, untouched], [eu_key_card_sku, new_sku, pending_sku])

    assert queue.titles_to_review == ["example-game"]
    assert queue.titles_to_research == ["untouched-game"]
    assert queue.new_skus == ["na-example-game-standard"]
    assert queue.skus_without_source == ["kr-example-game-standard"]
    assert queue.skus_to_refresh == []
