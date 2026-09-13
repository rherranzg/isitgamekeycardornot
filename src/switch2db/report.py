from collections import Counter

from pydantic import BaseModel, Field

from switch2db.divergences import find_format_divergences
from switch2db.fill_rate import compute_fill_rates, find_low_fill_fields
from switch2db.models import Sku


class DataReport(BaseModel):
    """Resumen de los SKUs para evaluar el criterio de salida de la Fase 0."""

    sku_count: int = Field(..., description="Número de SKUs válidos")
    skus_by_region: dict[str, int] = Field(..., description="SKUs por región")
    skus_by_format: dict[str, int] = Field(..., description="SKUs por formato")
    fill_rates: dict[str, float | None] = Field(
        ..., description="% de relleno por campo; condicionales medidos donde aplican (null si en ninguno)"
    )
    low_fill_fields: list[str] = Field(
        ..., description="Campos que no superan el umbral, sin contar los que se conservan por decisión"
    )
    format_divergences: dict[str, dict[str, str]] = Field(
        ..., description="Juegos cuyo formato cambia entre regiones, por región"
    )


def count_skus_by(skus: list[Sku], field_name: str) -> dict[str, int]:
    """Cuenta los SKUs según el valor de un campo."""
    return dict(Counter(str(getattr(sku, field_name)) for sku in skus))


def describe_format_divergences(skus: list[Sku]) -> dict[str, dict[str, str]]:
    """Expresa las divergencias de formato con claves legibles."""
    return {
        f"{title_id} ({edition})": {str(region): str(sku_format) for region, sku_format in formats.items()}
        for (title_id, edition), formats in find_format_divergences(skus).items()
    }


def build_report(skus: list[Sku], fill_threshold: float) -> DataReport:
    """Construye el informe de recuentos, relleno y divergencias de los SKUs."""
    fill_rates = compute_fill_rates(skus)
    return DataReport(
        sku_count=len(skus),
        skus_by_region=count_skus_by(skus, "region"),
        skus_by_format=count_skus_by(skus, "format"),
        fill_rates=fill_rates,
        low_fill_fields=find_low_fill_fields(fill_rates, fill_threshold),
        format_divergences=describe_format_divergences(skus),
    )
