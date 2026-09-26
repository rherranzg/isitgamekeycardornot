from collections import Counter
from collections.abc import Sequence

from pydantic import BaseModel, Field

from switch2db.divergences import find_format_divergences
from switch2db.fill_rate import compute_fill_rates, find_low_fill_fields
from switch2db.models import Sku, Title, TitleStatus


class DataReport(BaseModel):
    """Summary of titles and SKUs to assess the Phase 0 exit criteria."""

    title_count: int = Field(..., description="Number of valid imported titles")
    titles_by_status: dict[str, int] = Field(..., description="Titles by review status")
    pending_review_titles: list[str] = Field(
        ..., description="title_ids imported from IGDB whose data has not been checked by hand yet"
    )
    sku_count: int = Field(..., description="Number of valid SKUs")
    skus_by_region: dict[str, int] = Field(..., description="SKUs by region")
    skus_by_format: dict[str, int] = Field(..., description="SKUs by format")
    skus_by_status: dict[str, int] = Field(..., description="SKUs by review status")
    fill_rates: dict[str, float | None] = Field(
        ..., description="Fill rate per field; conditional ones measured where they apply (null if nowhere)"
    )
    low_fill_fields: list[str] = Field(
        ..., description="Fields below the threshold, excluding those kept by decision"
    )
    format_divergences: dict[str, dict[str, str]] = Field(
        ..., description="Games whose format differs between regions, by region"
    )


def count_by(rows: Sequence[BaseModel], field_name: str) -> dict[str, int]:
    """Count rows by the value of a field."""
    return dict(Counter(str(getattr(row, field_name)) for row in rows))


def list_pending_review_title_ids(titles: list[Title]) -> list[str]:
    """Return the title_ids with status pending, in titles.yaml order."""
    return [title.title_id for title in titles if title.status == TitleStatus.PENDING]


def describe_format_divergences(skus: list[Sku]) -> dict[str, dict[str, str]]:
    """Express the format divergences with readable keys."""
    return {
        f"{title_id} ({edition})": {str(region): str(sku_format) for region, sku_format in formats.items()}
        for (title_id, edition), formats in find_format_divergences(skus).items()
    }


def build_report(titles: list[Title], skus: list[Sku], fill_threshold: float) -> DataReport:
    """Build the report on title review and on SKU counts, fill rates and divergences."""
    fill_rates = compute_fill_rates(skus)
    return DataReport(
        title_count=len(titles),
        titles_by_status=count_by(titles, "status"),
        pending_review_titles=list_pending_review_title_ids(titles),
        sku_count=len(skus),
        skus_by_region=count_by(skus, "region"),
        skus_by_format=count_by(skus, "format"),
        skus_by_status=count_by(skus, "status"),
        fill_rates=fill_rates,
        low_fill_fields=find_low_fill_fields(fill_rates, fill_threshold),
        format_divergences=describe_format_divergences(skus),
    )
