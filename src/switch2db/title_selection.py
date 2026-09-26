from datetime import date

from switch2db.catalog import CatalogEntry, is_catalog_candidate
from switch2db.models import ExcludedTitle, Title, TitleStatus
from switch2db.slug import make_unique_slug


def build_new_title(entry: CatalogEntry, taken_title_ids: set[str]) -> Title:
    """Create the title for a catalog entry, with a free slug and not yet researched."""
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
    """Pick, in catalog order, up to `limit` games that are neither in titles.yaml nor excluded
    (None = all). Skips editions (Deluxe, Gold...) whose base game is also on Switch 2: their box,
    if any, is a SKU of the base game. Bundles are not picked either: those are added by hand."""
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
    """True if the date is an exact day already past: the game is out and the date will not change."""
    if release_date is None or len(release_date) != len("YYYY-MM-DD"):
        return False
    return date.fromisoformat(release_date) <= today


def refresh_release_dates(titles: list[Title], catalog: list[CatalogEntry], today: date) -> list[Title]:
    """Update from the catalog the release date of titles whose date can still change (unknown, without
    an exact day, or in the future). Past dates and titles missing from the catalog are left alone, and a
    catalog entry without a date does not erase one written by hand with a source when IGDB had none."""
    catalog_by_igdb_id = {entry.igdb_id: entry for entry in catalog}
    refreshed: list[Title] = []
    for title in titles:
        entry = catalog_by_igdb_id.get(title.igdb_id)
        if entry is None or entry.release_date is None or is_settled_release_date(title.release_date, today):
            refreshed.append(title)
        else:
            refreshed.append(title.model_copy(update={"release_date": entry.release_date}))
    return refreshed
