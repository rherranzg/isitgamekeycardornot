from switch2db.models import Sku
from switch2db.report import build_report, count_skus_by, describe_format_divergences


def test_count_skus_by_success(eu_key_card_sku: Sku, asia_full_cart_sku: Sku, jp_unknown_sku: Sku) -> None:
    skus = [eu_key_card_sku, asia_full_cart_sku, jp_unknown_sku]

    assert count_skus_by(skus, "region") == {"EU": 1, "ASIA": 1, "JP": 1}


def test_count_skus_by_returns_empty_dict_without_skus() -> None:
    assert count_skus_by([], "region") == {}


def test_describe_format_divergences_success(eu_key_card_sku: Sku, asia_full_cart_sku: Sku) -> None:
    assert describe_format_divergences([eu_key_card_sku, asia_full_cart_sku]) == {
        "example-game (standard)": {"EU": "game_key_card", "ASIA": "full_cart"}
    }


def test_build_report_success(eu_key_card_sku: Sku, asia_full_cart_sku: Sku) -> None:
    report = build_report([eu_key_card_sku, asia_full_cart_sku], fill_threshold=60.0)

    assert report.sku_count == 2
    assert report.skus_by_format == {"game_key_card": 1, "full_cart": 1}
    assert report.low_fill_fields == ["cart_size_gb"]
    assert report.format_divergences == {
        "example-game (standard)": {"EU": "game_key_card", "ASIA": "full_cart"}
    }


def test_build_report_handles_empty_skus() -> None:
    report = build_report([], fill_threshold=60.0)

    assert report.model_dump() == {
        "sku_count": 0,
        "skus_by_region": {},
        "skus_by_format": {},
        "fill_rates": {},
        "low_fill_fields": [],
        "format_divergences": {},
    }
