from switch2db.igdb_client import IGDB_MAX_LIMIT
from switch2db.models import Title, TitleSeed


def chunk_seeds(seeds: list[TitleSeed], size: int = IGDB_MAX_LIMIT) -> list[list[TitleSeed]]:
    """Divide las semillas en bloques de como mucho `size`, para respetar el límite de IGDB por petición."""
    return [seeds[start : start + size] for start in range(0, len(seeds), size)]


def select_seeds_to_fetch(
    seeds: list[TitleSeed],
    existing_title_ids: set[str],
    refresh_ids: set[str],
    refresh_all: bool,
    limit: int | None,
) -> list[TitleSeed]:
    """Elige qué semillas hace falta descargar: las pendientes de importar y las marcadas para refrescar."""
    pending = [
        seed
        for seed in seeds
        if refresh_all or seed.title_id in refresh_ids or seed.title_id not in existing_title_ids
    ]
    return pending if limit is None else pending[:limit]


def merge_titles(existing: list[Title], fetched: list[Title], seed_order: list[str]) -> list[Title]:
    """Sustituye o añade los títulos descargados; devuelve el resultado en el orden de las semillas."""
    by_id = {title.title_id: title for title in existing}
    for title in fetched:
        by_id[title.title_id] = title
    return [by_id[title_id] for title_id in seed_order if title_id in by_id]
