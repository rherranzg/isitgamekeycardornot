import re
from datetime import UTC, date, datetime

from pydantic import BaseModel, Field

from switch2db.igdb_models import IgdbGame, IgdbReleaseDate

PUBLISHER_SEPARATOR = " / "
NON_ALNUM = re.compile(r"[^a-z0-9]")
# Tipos de IGDB que no son un juego con caja propia. Los nombres son los que devuelve la API
# ("DLC", "Pack / Addon"), normalizados sin espacios ni signos.
EXCLUDED_GAME_TYPES = {
    "dlc",
    "dlcaddon",
    "pack",
    "packaddon",
    "bundle",
    "expansion",
    "episode",
    "season",
    "mod",
    "update",
    "fork",
}
# Se guardan en el catálogo aunque no se elijan como títulos nuevos: las recopilaciones y ediciones que IGDB
# marca como Bundle y se añaden a mano necesitan que add_titles les refresque la fecha.
CATALOG_ONLY_GAME_TYPES = {"bundle"}
QUARTERS_BY_DATE_FORMAT = {"YYYYQ1": 1, "YYYYQ2": 2, "YYYYQ3": 3, "YYYYQ4": 4}


class CatalogEntry(BaseModel):
    """Juego de Switch 2 en IGDB, candidato a entrar en titles.yaml."""

    igdb_id: int = Field(..., description="Id del juego en IGDB")
    name: str = Field(..., description="Nombre del juego")
    game_type: str | None = Field(None, description="Tipo de juego en IGDB (main game, port, remaster...)")
    release_date: str | None = Field(
        None,
        description="Salida en la plataforma con la precisión de IGDB (2026-08-20, 2026-08, 2026-Q3, 2026); "
        "null si IGDB no da fecha o es TBD",
    )
    publishers: str | None = Field(None, description="Publishers según IGDB")
    version_parent: int | None = Field(
        None, description="Id de IGDB del juego del que esta entrada es una edición; null si no lo es"
    )


def normalize_game_type(game_type: str) -> str:
    """Normaliza el tipo de juego de IGDB para compararlo sin distinguir formato."""
    return NON_ALNUM.sub("", game_type.lower())


def is_catalog_candidate(game_type: str | None) -> bool:
    """True si el tipo de IGDB puede tener caja propia: fuera DLC, packs, bundles y expansiones."""
    if game_type is None:
        return True
    return normalize_game_type(game_type) not in EXCLUDED_GAME_TYPES


def is_kept_in_catalog(game_type: str | None) -> bool:
    """True si se guarda en el catálogo: los candidatos a título y los tipos que solo sirven para fechas."""
    return is_catalog_candidate(game_type) or (
        game_type is not None and normalize_game_type(game_type) in CATALOG_ONLY_GAME_TYPES
    )


def list_publishers(game: IgdbGame) -> list[str]:
    """Devuelve, sin repetir y en orden, las compañías que IGDB marca como publisher."""
    return list(
        dict.fromkeys(involved.company.name for involved in game.involved_companies if involved.publisher)
    )


def convert_unix_timestamp_to_date(timestamp: int) -> date:
    """Convierte un timestamp Unix en segundos a fecha UTC."""
    return datetime.fromtimestamp(timestamp, tz=UTC).date()


def format_release_date(release: IgdbReleaseDate) -> str | None:
    """Escribe la fecha con la precisión que da IGDB: día, mes, trimestre o año; None si es TBD o falta."""
    if release.date is None or release.y is None or release.date_format is None:
        return None
    date_format = release.date_format.format
    if date_format == "YYYYMMDD":
        return convert_unix_timestamp_to_date(release.date).isoformat()
    if date_format == "YYYYMM" and release.m is not None:
        return f"{release.y:04d}-{release.m:02d}"
    if date_format in QUARTERS_BY_DATE_FORMAT:
        return f"{release.y:04d}-Q{QUARTERS_BY_DATE_FORMAT[date_format]}"
    if date_format == "YYYY":
        return f"{release.y:04d}"
    return None


def find_platform_release_date(game: IgdbGame, platform_id: int) -> str | None:
    """Devuelve la fecha de salida del juego en la plataforma; si hay varias (una por región), la más
    temprana. IGDB pone el último día del periodo en las fechas de año o trimestre, así que a igualdad
    de periodo gana la fecha exacta."""
    candidates = [
        (release.date, text)
        for release in game.release_dates
        if release.platform == platform_id
        and release.date is not None
        and (text := format_release_date(release)) is not None
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: candidate[0])[1]


def build_catalog_entry(game: IgdbGame, platform_id: int) -> CatalogEntry:
    """Resume un juego de IGDB en una entrada de catálogo, con su fecha de salida en la plataforma."""
    publishers = list_publishers(game)
    return CatalogEntry(
        igdb_id=game.id,
        name=game.name,
        game_type=game.game_type.type if game.game_type else None,
        release_date=find_platform_release_date(game, platform_id),
        publishers=PUBLISHER_SEPARATOR.join(publishers) if publishers else None,
        version_parent=game.version_parent,
    )


def build_catalog(games: list[IgdbGame], platform_id: int) -> list[CatalogEntry]:
    """Construye el catálogo sin los tipos descartados (los Bundle se quedan, solo para fechas), ordenado
    por nombre."""
    entries = (build_catalog_entry(game, platform_id) for game in games)
    candidates = (entry for entry in entries if is_kept_in_catalog(entry.game_type))
    return sorted(candidates, key=lambda entry: entry.name.casefold())
