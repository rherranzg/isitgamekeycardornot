from switch2db.fill_rate import (
    FIELDS_KEPT_REGARDLESS_OF_FILL,
    compute_field_fill_rate,
    compute_fill_rates,
    find_low_fill_fields,
    is_full_cart,
    select_applicable_skus,
)
from switch2db.models import Sku


def test_is_full_cart_success(asia_full_cart_sku: Sku) -> None:
    assert is_full_cart(asia_full_cart_sku) is True


def test_is_full_cart_returns_false_for_game_key_card(eu_key_card_sku: Sku) -> None:
    assert is_full_cart(eu_key_card_sku) is False


def test_select_applicable_skus_filters_conditional_field(
    eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    assert select_applicable_skus([eu_key_card_sku, asia_full_cart_sku], "cart_size_gb") == [
        asia_full_cart_sku
    ]


def test_select_applicable_skus_returns_all_for_unconditional_field(
    eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    skus = [eu_key_card_sku, asia_full_cart_sku]

    assert select_applicable_skus(skus, "ean") == skus


def test_compute_field_fill_rate_success(eu_key_card_sku: Sku, jp_unknown_sku: Sku) -> None:
    assert compute_field_fill_rate([eu_key_card_sku, jp_unknown_sku], "source_url") == 50.0


def test_compute_field_fill_rate_measures_conditional_field_only_where_it_applies(
    eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    assert compute_field_fill_rate([eu_key_card_sku, asia_full_cart_sku], "cart_size_gb") == 100.0


def test_compute_field_fill_rate_returns_none_when_field_applies_to_no_sku(eu_key_card_sku: Sku) -> None:
    assert compute_field_fill_rate([eu_key_card_sku], "cart_size_gb") is None


def test_compute_fill_rates_returns_empty_dict_without_skus() -> None:
    assert compute_fill_rates([]) == {}


def test_compute_fill_rates_success(
    eu_key_card_sku: Sku, asia_full_cart_sku: Sku, jp_unknown_sku: Sku
) -> None:
    fill_rates = compute_fill_rates([eu_key_card_sku, asia_full_cart_sku, jp_unknown_sku])

    assert list(fill_rates) == list(Sku.model_fields)
    assert fill_rates["sku_id"] == 100.0
    assert fill_rates["source_url"] == 66.7
    assert fill_rates["cart_size_gb"] == 100.0
    assert fill_rates["includes_download_code"] == 0.0


def test_find_low_fill_fields_includes_fields_at_threshold() -> None:
    fill_rates = {"sku_id": 100.0, "ean": 60.0, "download_size_gb": 59.9}

    assert find_low_fill_fields(fill_rates, 60.0) == ["ean", "download_size_gb"]


def test_find_low_fill_fields_skips_fields_that_apply_to_no_sku() -> None:
    assert find_low_fill_fields({"cart_size_gb": None, "ean": 10.0}, 60.0) == ["ean"]


def test_find_low_fill_fields_skips_fields_kept_by_decision() -> None:
    assert "distributor" in FIELDS_KEPT_REGARDLESS_OF_FILL
    assert find_low_fill_fields({"distributor": 6.7, "ean": 13.3}, 60.0) == ["ean"]
