from switch2db.models import Sku, Title, TitleStatus
from switch2db.report import (
    build_report,
    count_by,
    describe_format_divergences,
    list_pending_review_title_ids,
)


def test_count_by_success(eu_key_card_sku: Sku, asia_full_cart_sku: Sku, jp_unknown_sku: Sku) -> None:
    skus = [eu_key_card_sku, asia_full_cart_sku, jp_unknown_sku]

    assert count_by(skus, "region") == {"EU": 1, "ASIA": 1, "JP": 1}


def test_count_by_returns_empty_dict_without_rows() -> None:
    assert count_by([], "region") == {}


def test_list_pending_review_title_ids_success(title: Title) -> None:
    reviewed = title.model_copy(update={"title_id": "reviewed-game", "status": TitleStatus.REVIEWED})
    untouched = title.model_copy(update={"title_id": "new-game", "status": TitleStatus.NEW})

    assert list_pending_review_title_ids([reviewed, title, untouched]) == ["example-game"]


def test_list_pending_review_title_ids_returns_empty_list_when_all_reviewed(title: Title) -> None:
    assert list_pending_review_title_ids([title.model_copy(update={"status": TitleStatus.REVIEWED})]) == []


def test_describe_format_divergences_success(eu_key_card_sku: Sku, asia_full_cart_sku: Sku) -> None:
    assert describe_format_divergences([eu_key_card_sku, asia_full_cart_sku]) == {
        "example-game (standard)": {"EU": "game_key_card", "ASIA": "full_cart"}
    }


def test_build_report_success(title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku) -> None:
    report = build_report([title], [eu_key_card_sku, asia_full_cart_sku], fill_threshold=60.0)

    assert report.title_count == 1
    assert report.titles_by_status == {"pending": 1}
    assert report.pending_review_titles == ["example-game"]
    assert report.sku_count == 2
    assert report.skus_by_format == {"game_key_card": 1, "full_cart": 1}
    assert report.fill_rates["cart_size_gb"] == 100.0
    assert report.low_fill_fields == ["includes_download_code"]
    assert report.format_divergences == {
        "example-game (standard)": {"EU": "game_key_card", "ASIA": "full_cart"}
    }


def test_build_report_handles_empty_data() -> None:
    report = build_report([], [], fill_threshold=60.0)

    assert report.model_dump() == {
        "title_count": 0,
        "titles_by_status": {},
        "pending_review_titles": [],
        "sku_count": 0,
        "skus_by_region": {},
        "skus_by_format": {},
        "skus_by_status": {},
        "fill_rates": {},
        "low_fill_fields": [],
        "format_divergences": {},
    }
