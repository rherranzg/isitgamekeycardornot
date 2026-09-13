from switch2db.fill_rate import compute_fill_rates, find_low_fill_fields
from switch2db.models import Sku


def test_compute_fill_rates_returns_empty_dict_without_skus() -> None:
    assert compute_fill_rates([]) == {}


def test_compute_fill_rates_success(eu_key_card_sku: Sku, asia_full_cart_sku: Sku) -> None:
    fill_rates = compute_fill_rates([eu_key_card_sku, asia_full_cart_sku])

    assert list(fill_rates) == list(Sku.model_fields)
    assert fill_rates["sku_id"] == 100.0
    assert fill_rates["cart_size_gb"] == 50.0


def test_compute_fill_rates_rounds_to_one_decimal(
    eu_key_card_sku: Sku, asia_full_cart_sku: Sku, jp_unknown_sku: Sku
) -> None:
    fill_rates = compute_fill_rates([eu_key_card_sku, asia_full_cart_sku, jp_unknown_sku])

    assert fill_rates["source_url"] == 66.7
    assert fill_rates["cart_size_gb"] == 33.3


def test_find_low_fill_fields_includes_fields_at_threshold() -> None:
    fill_rates = {"sku_id": 100.0, "ean": 60.0, "download_size_gb": 59.9}

    assert find_low_fill_fields(fill_rates, 60.0) == ["ean", "download_size_gb"]


def test_find_low_fill_fields_returns_empty_list_when_all_fields_pass() -> None:
    assert find_low_fill_fields({"sku_id": 100.0, "ean": 60.1}, 60.0) == []
