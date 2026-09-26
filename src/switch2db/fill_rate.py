from collections.abc import Callable, Mapping

from switch2db.models import Edition, Format, Sku

# Kept even when below the threshold. Decided on 2026-09-13: the distributor is internal data.
FIELDS_KEPT_REGARDLESS_OF_FILL = frozenset({"distributor"})


def is_full_cart(sku: Sku) -> bool:
    """Tell whether the SKU is a full cartridge."""
    return sku.format == Format.FULL_CART


def is_special_edition(sku: Sku) -> bool:
    """Tell whether the SKU is a non-standard edition, the only kind that has a commercial name."""
    return sku.edition != Edition.STANDARD


# Fields that only apply to some SKUs: their fill rate is measured only over those rows.
FIELD_APPLICABILITY: dict[str, Callable[[Sku], bool]] = {
    "cart_size_gb": is_full_cart,
    "edition_name": is_special_edition,
}


def select_applicable_skus(skus: list[Sku], field_name: str) -> list[Sku]:
    """Return the SKUs the field applies to; all of them if the field is not conditional."""
    applies = FIELD_APPLICABILITY.get(field_name)
    if applies is None:
        return skus
    return [sku for sku in skus if applies(sku)]


def compute_field_fill_rate(skus: list[Sku], field_name: str) -> float | None:
    """Compute the % of applicable SKUs with a non-null value; None if the field applies to none."""
    applicable_skus = select_applicable_skus(skus, field_name)
    if not applicable_skus:
        return None
    filled_count = sum(getattr(sku, field_name) is not None for sku in applicable_skus)
    return round(100 * filled_count / len(applicable_skus), 1)


def compute_fill_rates(skus: list[Sku]) -> dict[str, float | None]:
    """Compute the fill rate of each Sku field, measuring conditional fields only where they apply."""
    if not skus:
        return {}
    return {field_name: compute_field_fill_rate(skus, field_name) for field_name in Sku.model_fields}


def find_low_fill_fields(fill_rates: Mapping[str, float | None], threshold: float) -> list[str]:
    """Return the fields below the threshold, except those that apply to no SKU or are kept by decision."""
    return [
        field_name
        for field_name, rate in fill_rates.items()
        if rate is not None and rate <= threshold and field_name not in FIELDS_KEPT_REGARDLESS_OF_FILL
    ]
