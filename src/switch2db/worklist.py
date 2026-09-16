from pydantic import BaseModel, Field

from switch2db.models import Region, Sku, SkuStatus, Title, TitleStatus


class WorkQueue(BaseModel):
    """Lo que queda por hacer, calculado a partir de los ficheros de datos. Sin IA y sin red."""

    titles_to_review: list[str] = Field(
        ...,
        description="Títulos investigados sin confirmar la edición ni encontrar fuente (status pending)",
    )
    titles_to_research: list[str] = Field(
        ..., description="Títulos del catálogo que nadie ha investigado todavía (status new)"
    )
    titles_missing_regions: dict[str, list[str]] = Field(
        ..., description="Títulos ya empezados y las regiones que les faltan por cubrir"
    )
    new_skus: list[str] = Field(
        ..., description="sku_id recién escritos (status new): no salen en la web hasta buscarles fuente"
    )
    skus_without_source: list[str] = Field(
        ...,
        description="sku_id buscados sin encontrar fuente (status pending): salen como formato desconocido",
    )
    skus_to_refresh: list[str] = Field(
        ..., description="sku_id marcados para volver a comprobar (status refresh)"
    )


def list_titles_by_status(titles: list[Title], status: TitleStatus) -> list[str]:
    """Devuelve los title_id con ese status, en el orden de titles.yaml."""
    return [title.title_id for title in titles if title.status == status]


def list_skus_by_status(skus: list[Sku], status: SkuStatus) -> list[str]:
    """Devuelve los sku_id con ese status, en el orden de skus.yaml."""
    return [sku.sku_id for sku in skus if sku.status == status]


def list_missing_regions(title_id: str, skus: list[Sku]) -> list[str]:
    """Devuelve las regiones sin ningún SKU para ese juego, en el orden del enum."""
    covered = {sku.region for sku in skus if sku.title_id == title_id}
    return [region.value for region in Region if region not in covered]


def find_titles_missing_regions(titles: list[Title], skus: list[Sku]) -> dict[str, list[str]]:
    """Devuelve, por título ya empezado, las regiones que todavía no tienen SKU."""
    title_ids_with_skus = {sku.title_id for sku in skus}
    missing_by_title = {
        title.title_id: list_missing_regions(title.title_id, skus)
        for title in titles
        if title.title_id in title_ids_with_skus
    }
    return {title_id: regions for title_id, regions in missing_by_title.items() if regions}


def build_work_queue(titles: list[Title], skus: list[Sku]) -> WorkQueue:
    """Construye la cola de trabajo pendiente a partir del status de cada título y de cada SKU."""
    return WorkQueue(
        titles_to_review=list_titles_by_status(titles, TitleStatus.PENDING),
        titles_to_research=list_titles_by_status(titles, TitleStatus.NEW),
        titles_missing_regions=find_titles_missing_regions(titles, skus),
        new_skus=list_skus_by_status(skus, SkuStatus.NEW),
        skus_without_source=list_skus_by_status(skus, SkuStatus.PENDING),
        skus_to_refresh=list_skus_by_status(skus, SkuStatus.REFRESH),
    )
