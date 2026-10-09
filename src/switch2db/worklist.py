from datetime import date

from pydantic import BaseModel, Field

from switch2db.models import PhysicalRelease, Region, Sku, Title, TitleStatus


class WorkQueue(BaseModel):
    """What is left to do, computed from the data files. No network."""

    titles_to_research: list[str] = Field(
        ..., description="Catalog titles nobody has researched yet (status new): research every region"
    )
    titles_to_refresh: list[str] = Field(
        ...,
        description="Titles to research again from scratch (status refresh); their data is a starting point",
    )
    titles_to_complete: list[str] = Field(
        ...,
        description="Titles whose data is trusted and only the missing part is left (status pending), "
        "least recently checked first",
    )
    titles_missing_regions: dict[str, list[str]] = Field(
        ...,
        description="Titles already started and the regions with neither a SKU nor a sourced no-box entry",
    )
    skus_without_source: list[str] = Field(
        ..., description="sku_ids searched without finding a source: shown as unknown format"
    )


def list_titles_by_status(titles: list[Title], status: TitleStatus) -> list[str]:
    """Return the title_ids with that status, in titles.yaml order."""
    return [title.title_id for title in titles if title.status == status]


def list_titles_to_complete(titles: list[Title]) -> list[str]:
    """Return the pending title_ids, least recently checked first (never checked before any date)."""
    pending = [title for title in titles if title.status == TitleStatus.PENDING]
    return [title.title_id for title in sorted(pending, key=lambda title: title.last_checked_at or date.min)]


def list_skus_without_source(skus: list[Sku]) -> list[str]:
    """Return the sku_ids with no source_url, in skus.yaml order."""
    return [sku.sku_id for sku in skus if sku.source_url is None]


def list_missing_regions(title_id: str, skus: list[Sku], releases: list[PhysicalRelease]) -> list[str]:
    """Return the regions with neither a SKU nor a sourced "no box in that region" entry, in enum order."""
    answered = {sku.region for sku in skus if sku.title_id == title_id}
    answered |= {
        release.region
        for release in releases
        if release.title_id == title_id and release.region is not None and release.source_url is not None
    }
    return [region.value for region in Region if region not in answered]


def find_titles_missing_regions(
    titles: list[Title], skus: list[Sku], releases: list[PhysicalRelease]
) -> dict[str, list[str]]:
    """Return, for each started title, the regions that are still unanswered."""
    title_ids_with_skus = {sku.title_id for sku in skus}
    missing_by_title = {
        title.title_id: list_missing_regions(title.title_id, skus, releases)
        for title in titles
        if title.title_id in title_ids_with_skus
    }
    return {title_id: regions for title_id, regions in missing_by_title.items() if regions}


def build_work_queue(titles: list[Title], skus: list[Sku], releases: list[PhysicalRelease]) -> WorkQueue:
    """Build the pending work queue from the status of each title and the source of each SKU."""
    return WorkQueue(
        titles_to_research=list_titles_by_status(titles, TitleStatus.NEW),
        titles_to_refresh=list_titles_by_status(titles, TitleStatus.REFRESH),
        titles_to_complete=list_titles_to_complete(titles),
        titles_missing_regions=find_titles_missing_regions(titles, skus, releases),
        skus_without_source=list_skus_without_source(skus),
    )
