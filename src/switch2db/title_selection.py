from datetime import date

from switch2db.catalog import CatalogEntry, is_catalog_candidate
from switch2db.models import ExcludedTitle, Title, TitleStatus
from switch2db.slug import make_unique_slug


def build_new_title(entry: CatalogEntry, taken_title_ids: set[str]) -> Title:
    """Crea el título de una entrada del catálogo, con un slug libre y sin investigar todavía."""
    return Title(
        title_id=make_unique_slug(entry.name, taken_title_ids),
        igdb_id=entry.igdb_id,
        name=entry.name,
        publisher=entry.publishers,
        release_date=entry.release_date,
        status=TitleStatus.NEW,
    )


def select_new_titles(
    catalog: list[CatalogEntry], existing: list[Title], excluded: list[ExcludedTitle], limit: int | None
) -> list[Title]:
    """Elige, en el orden del catálogo, hasta `limit` juegos que no estén ya en titles.yaml ni excluidos
    (None = todos). Se salta las ediciones (Deluxe, Gold...) cuyo juego base también está en Switch 2:
    su caja, si la tiene, es un SKU del juego base. Tampoco elige los Bundle: esos se añaden a mano."""
    known_igdb_ids = {title.igdb_id for title in existing} | {entry.igdb_id for entry in excluded}
    switch2_igdb_ids = {entry.igdb_id for entry in catalog} | {title.igdb_id for title in existing}
    taken_title_ids = {title.title_id for title in existing}
    new_titles: list[Title] = []
    for entry in catalog:
        if limit is not None and len(new_titles) >= limit:
            break
        if (
            entry.igdb_id in known_igdb_ids
            or entry.version_parent in switch2_igdb_ids
            or not is_catalog_candidate(entry.game_type)
        ):
            continue
        title = build_new_title(entry, taken_title_ids)
        taken_title_ids.add(title.title_id)
        new_titles.append(title)
    return new_titles


def is_settled_release_date(release_date: str | None, today: date) -> bool:
    """True si la fecha es un día exacto que ya ha pasado: el juego salió y la fecha ya no cambia."""
    if release_date is None or len(release_date) != len("YYYY-MM-DD"):
        return False
    return date.fromisoformat(release_date) <= today


def refresh_release_dates(titles: list[Title], catalog: list[CatalogEntry], today: date) -> list[Title]:
    """Actualiza desde el catálogo la fecha de los títulos que aún puede cambiar (desconocida, sin día
    exacto o futura). Las fechas ya pasadas y los títulos que no están en el catálogo no se tocan, y un
    catálogo sin fecha no borra la que se escribió a mano con fuente cuando IGDB no la tenía."""
    catalog_by_igdb_id = {entry.igdb_id: entry for entry in catalog}
    refreshed: list[Title] = []
    for title in titles:
        entry = catalog_by_igdb_id.get(title.igdb_id)
        if entry is None or entry.release_date is None or is_settled_release_date(title.release_date, today):
            refreshed.append(title)
        else:
            refreshed.append(title.model_copy(update={"release_date": entry.release_date}))
    return refreshed
