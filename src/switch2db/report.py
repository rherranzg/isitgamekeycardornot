from collections import Counter
from collections.abc import Sequence

from pydantic import BaseModel, Field

from switch2db.divergences import find_format_divergences
from switch2db.fill_rate import compute_fill_rates, find_low_fill_fields
from switch2db.models import Sku, Title, TitleStatus


class DataReport(BaseModel):
    """Resumen de títulos y SKUs para evaluar el criterio de salida de la Fase 0."""

    title_count: int = Field(..., description="Número de títulos importados válidos")
    titles_by_status: dict[str, int] = Field(..., description="Títulos por status de revisión")
    pending_review_titles: list[str] = Field(
        ..., description="title_id importados de IGDB cuyos datos aún no se han comprobado a mano"
    )
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


def count_by(rows: Sequence[BaseModel], field_name: str) -> dict[str, int]:
    """Cuenta las filas según el valor de un campo."""
    return dict(Counter(str(getattr(row, field_name)) for row in rows))


def list_pending_review_title_ids(titles: list[Title]) -> list[str]:
    """Devuelve los title_id con status pending, en el orden de titles.yaml."""
    return [title.title_id for title in titles if title.status == TitleStatus.PENDING]


def describe_format_divergences(skus: list[Sku]) -> dict[str, dict[str, str]]:
    """Expresa las divergencias de formato con claves legibles."""
    return {
        f"{title_id} ({edition})": {str(region): str(sku_format) for region, sku_format in formats.items()}
        for (title_id, edition), formats in find_format_divergences(skus).items()
    }


def build_report(titles: list[Title], skus: list[Sku], fill_threshold: float) -> DataReport:
    """Construye el informe de revisión de títulos y de recuentos, relleno y divergencias de los SKUs."""
    fill_rates = compute_fill_rates(skus)
    return DataReport(
        title_count=len(titles),
        titles_by_status=count_by(titles, "status"),
        pending_review_titles=list_pending_review_title_ids(titles),
        sku_count=len(skus),
        skus_by_region=count_by(skus, "region"),
        skus_by_format=count_by(skus, "format"),
        fill_rates=fill_rates,
        low_fill_fields=find_low_fill_fields(fill_rates, fill_threshold),
        format_divergences=describe_format_divergences(skus),
    )
