from collections.abc import Callable, Mapping

from switch2db.models import Edition, Format, Sku

# Se conservan aunque no superen el umbral. Decisión del 13-09-2026: la distribuidora es dato interno.
FIELDS_KEPT_REGARDLESS_OF_FILL = frozenset({"distributor"})


def is_full_cart(sku: Sku) -> bool:
    """Indica si el SKU es un cartucho completo."""
    return sku.format == Format.FULL_CART


def is_special_edition(sku: Sku) -> bool:
    """Indica si el SKU es una edición distinta de la estándar, la única que lleva nombre comercial."""
    return sku.edition != Edition.STANDARD


# Campos que solo aplican a parte de los SKUs: su relleno se mide únicamente sobre esas filas.
FIELD_APPLICABILITY: dict[str, Callable[[Sku], bool]] = {
    "cart_size_gb": is_full_cart,
    "edition_name": is_special_edition,
}


def select_applicable_skus(skus: list[Sku], field_name: str) -> list[Sku]:
    """Devuelve los SKUs a los que aplica el campo; todos si el campo no es condicional."""
    applies = FIELD_APPLICABILITY.get(field_name)
    if applies is None:
        return skus
    return [sku for sku in skus if applies(sku)]


def compute_field_fill_rate(skus: list[Sku], field_name: str) -> float | None:
    """Calcula el % de SKUs aplicables con valor no nulo; None si el campo no aplica a ninguno."""
    applicable_skus = select_applicable_skus(skus, field_name)
    if not applicable_skus:
        return None
    filled_count = sum(getattr(sku, field_name) is not None for sku in applicable_skus)
    return round(100 * filled_count / len(applicable_skus), 1)


def compute_fill_rates(skus: list[Sku]) -> dict[str, float | None]:
    """Calcula el % de relleno de cada campo de Sku, midiendo los condicionales solo donde aplican."""
    if not skus:
        return {}
    return {field_name: compute_field_fill_rate(skus, field_name) for field_name in Sku.model_fields}


def find_low_fill_fields(fill_rates: Mapping[str, float | None], threshold: float) -> list[str]:
    """Devuelve los campos que no superan el umbral, salvo los que no aplican o se conservan por decisión."""
    return [
        field_name
        for field_name, rate in fill_rates.items()
        if rate is not None and rate <= threshold and field_name not in FIELDS_KEPT_REGARDLESS_OF_FILL
    ]
