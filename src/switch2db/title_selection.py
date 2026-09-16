from switch2db.catalog import CatalogEntry
from switch2db.models import Title, TitleStatus
from switch2db.slug import make_unique_slug


def build_new_title(entry: CatalogEntry, taken_title_ids: set[str]) -> Title:
    """Crea el título de una entrada del catálogo, con un slug libre y sin investigar todavía."""
    return Title(
        title_id=make_unique_slug(entry.name, taken_title_ids),
        igdb_id=entry.igdb_id,
        name=entry.name,
        publisher=entry.publishers,
        status=TitleStatus.NEW,
    )


def select_new_titles(catalog: list[CatalogEntry], existing: list[Title], limit: int | None) -> list[Title]:
    """Elige, en el orden del catálogo, hasta `limit` juegos que no estén ya en titles.yaml (None = todos)."""
    known_igdb_ids = {title.igdb_id for title in existing}
    taken_title_ids = {title.title_id for title in existing}
    new_titles: list[Title] = []
    for entry in catalog:
        if limit is not None and len(new_titles) >= limit:
            break
        if entry.igdb_id in known_igdb_ids:
            continue
        title = build_new_title(entry, taken_title_ids)
        taken_title_ids.add(title.title_id)
        new_titles.append(title)
    return new_titles
