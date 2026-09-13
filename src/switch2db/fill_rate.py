from switch2db.models import Sku


def compute_fill_rates(skus: list[Sku]) -> dict[str, float]:
    """Calcula, para cada campo de Sku, el % de SKUs con valor no nulo."""
    if not skus:
        return {}
    return {
        field_name: round(100 * sum(getattr(sku, field_name) is not None for sku in skus) / len(skus), 1)
        for field_name in Sku.model_fields
    }


def find_low_fill_fields(fill_rates: dict[str, float], threshold: float) -> list[str]:
    """Devuelve los campos cuyo % de relleno no supera el umbral."""
    return [field_name for field_name, rate in fill_rates.items() if rate <= threshold]
