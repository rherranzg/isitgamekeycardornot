from pydantic import BaseModel, Field

from switch2db.models import Region, Sku, SkuStatus, Title, TitleStatus


class WorkQueue(BaseModel):
    """What is left to do, computed from the data files. No network."""

    titles_to_review: list[str] = Field(
        ...,
        description="Titles researched without confirming the edition or finding a source (status pending)",
    )
    titles_to_research: list[str] = Field(
        ..., description="Catalog titles nobody has researched yet (status new)"
    )
    titles_missing_regions: dict[str, list[str]] = Field(
        ..., description="Titles already started and the regions they still lack"
    )
    new_skus: list[str] = Field(
        ..., description="Freshly written sku_ids (status new): no source has been searched for yet"
    )
    skus_without_source: list[str] = Field(
        ...,
        description="sku_ids searched without finding a source (status pending): shown as unknown format",
    )
    skus_to_refresh: list[str] = Field(
        ..., description="sku_ids flagged to be checked again (status refresh)"
    )


def list_titles_by_status(titles: list[Title], status: TitleStatus) -> list[str]:
    """Return the title_ids with that status, in titles.yaml order."""
    return [title.title_id for title in titles if title.status == status]


def list_skus_by_status(skus: list[Sku], status: SkuStatus) -> list[str]:
    """Return the sku_ids with that status, in skus.yaml order."""
    return [sku.sku_id for sku in skus if sku.status == status]


def list_missing_regions(title_id: str, skus: list[Sku]) -> list[str]:
    """Return the regions with no SKU for that game, in enum order."""
    covered = {sku.region for sku in skus if sku.title_id == title_id}
    return [region.value for region in Region if region not in covered]


def find_titles_missing_regions(titles: list[Title], skus: list[Sku]) -> dict[str, list[str]]:
    """Return, for each started title, the regions that still have no SKU."""
    title_ids_with_skus = {sku.title_id for sku in skus}
    missing_by_title = {
        title.title_id: list_missing_regions(title.title_id, skus)
        for title in titles
        if title.title_id in title_ids_with_skus
    }
    return {title_id: regions for title_id, regions in missing_by_title.items() if regions}


def build_work_queue(titles: list[Title], skus: list[Sku]) -> WorkQueue:
    """Build the pending work queue from the status of each title and each SKU."""
    return WorkQueue(
        titles_to_review=list_titles_by_status(titles, TitleStatus.PENDING),
        titles_to_research=list_titles_by_status(titles, TitleStatus.NEW),
        titles_missing_regions=find_titles_missing_regions(titles, skus),
        new_skus=list_skus_by_status(skus, SkuStatus.NEW),
        skus_without_source=list_skus_by_status(skus, SkuStatus.PENDING),
        skus_to_refresh=list_skus_by_status(skus, SkuStatus.REFRESH),
    )
