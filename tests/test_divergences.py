from switch2db.divergences import find_format_divergences, group_known_formats
from switch2db.models import Edition, Format, Region, Sku


def test_group_known_formats_ignores_unknown_formats(eu_key_card_sku: Sku, jp_unknown_sku: Sku) -> None:
    assert group_known_formats([eu_key_card_sku, jp_unknown_sku]) == {
        ("example-game", Edition.STANDARD): {Region.EU: Format.GAME_KEY_CARD}
    }


def test_group_known_formats_returns_empty_dict_without_skus() -> None:
    assert group_known_formats([]) == {}


def test_find_format_divergences_success(eu_key_card_sku: Sku, asia_full_cart_sku: Sku) -> None:
    assert find_format_divergences([eu_key_card_sku, asia_full_cart_sku]) == {
        ("example-game", Edition.STANDARD): {Region.EU: Format.GAME_KEY_CARD, Region.ASIA: Format.FULL_CART}
    }


def test_find_format_divergences_returns_empty_dict_when_formats_match(eu_key_card_sku: Sku) -> None:
    na_sku = eu_key_card_sku.model_copy(update={"region": Region.NA, "sku_id": "na-example-game-standard"})

    assert find_format_divergences([eu_key_card_sku, na_sku]) == {}


def test_find_format_divergences_does_not_count_unknown_as_divergence(
    eu_key_card_sku: Sku, jp_unknown_sku: Sku
) -> None:
    assert find_format_divergences([eu_key_card_sku, jp_unknown_sku]) == {}


def test_find_format_divergences_compares_within_the_same_edition(
    eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    deluxe_sku = asia_full_cart_sku.model_copy(
        update={"edition": Edition.DELUXE, "sku_id": "asia-example-game-deluxe"}
    )

    assert find_format_divergences([eu_key_card_sku, deluxe_sku]) == {}
