import re

from switch2db.catalog import CatalogEntry
from switch2db.models import TitleSeed
from switch2db.slug import make_unique_slug

NON_ALNUM = re.compile(r"[^a-z0-9]")
EXCLUDED_GAME_TYPES = {"dlcaddon", "bundle", "episode", "season", "mod", "pack", "update", "fork"}


def normalize_game_type(game_type: str) -> str:
    """Normaliza el tipo de juego de IGDB para compararlo sin distinguir formato."""
    return NON_ALNUM.sub("", game_type.lower())


def is_seedable(entry: CatalogEntry) -> bool:
    """True si el juego no es DLC, bundle, contenido episódico ni actualización."""
    if entry.game_type is None:
        return True
    return normalize_game_type(entry.game_type) not in EXCLUDED_GAME_TYPES


def select_new_seeds(
    catalog: list[CatalogEntry], existing_seeds: list[TitleSeed], limit: int | None
) -> list[TitleSeed]:
    """Elige, en el orden del catálogo, hasta `limit` juegos sin semilla todavía (None = todos)."""
    seeded_igdb_ids = {seed.igdb_id for seed in existing_seeds}
    taken_title_ids = {seed.title_id for seed in existing_seeds}
    new_seeds: list[TitleSeed] = []
    for entry in catalog:
        if limit is not None and len(new_seeds) >= limit:
            break
        if entry.igdb_id in seeded_igdb_ids or not is_seedable(entry):
            continue
        title_id = make_unique_slug(entry.name, taken_title_ids)
        taken_title_ids.add(title_id)
        new_seeds.append(TitleSeed(title_id=title_id, igdb_id=entry.igdb_id))
    return new_seeds
