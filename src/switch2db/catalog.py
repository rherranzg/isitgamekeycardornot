import re
from datetime import UTC, date, datetime

from pydantic import BaseModel, Field

from switch2db.igdb_models import IgdbGame

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


class CatalogEntry(BaseModel):
    """Juego de Switch 2 en IGDB, candidato a entrar en titles.yaml."""

    igdb_id: int = Field(..., description="Id del juego en IGDB")
    name: str = Field(..., description="Nombre del juego")
    game_type: str | None = Field(None, description="Tipo de juego en IGDB (main game, port, remaster...)")
    first_release_date: date | None = Field(
        None, description="Primer lanzamiento en cualquier plataforma, no necesariamente en Switch 2"
    )
    publishers: str | None = Field(None, description="Publishers según IGDB")


def normalize_game_type(game_type: str) -> str:
    """Normaliza el tipo de juego de IGDB para compararlo sin distinguir formato."""
    return NON_ALNUM.sub("", game_type.lower())


def is_catalog_candidate(game_type: str | None) -> bool:
    """True si el tipo de IGDB puede tener caja propia: fuera DLC, packs, bundles y expansiones."""
    if game_type is None:
        return True
    return normalize_game_type(game_type) not in EXCLUDED_GAME_TYPES


def list_publishers(game: IgdbGame) -> list[str]:
    """Devuelve, sin repetir y en orden, las compañías que IGDB marca como publisher."""
    return list(
        dict.fromkeys(involved.company.name for involved in game.involved_companies if involved.publisher)
    )


def convert_unix_timestamp_to_date(timestamp: int | None) -> date | None:
    """Convierte un timestamp Unix en segundos a fecha UTC; None si no hay timestamp."""
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC).date()


def build_catalog_entry(game: IgdbGame) -> CatalogEntry:
    """Resume un juego de IGDB en una entrada de catálogo."""
    publishers = list_publishers(game)
    return CatalogEntry(
        igdb_id=game.id,
        name=game.name,
        game_type=game.game_type.type if game.game_type else None,
        first_release_date=convert_unix_timestamp_to_date(game.first_release_date),
        publishers=PUBLISHER_SEPARATOR.join(publishers) if publishers else None,
    )


def build_catalog(games: list[IgdbGame]) -> list[CatalogEntry]:
    """Construye el catálogo de candidatos, sin los tipos descartados y ordenado por nombre."""
    entries = (build_catalog_entry(game) for game in games)
    candidates = (entry for entry in entries if is_catalog_candidate(entry.game_type))
    return sorted(candidates, key=lambda entry: entry.name.casefold())
