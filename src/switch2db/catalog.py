from datetime import UTC, date, datetime

from pydantic import BaseModel, Field

from switch2db.igdb_models import IgdbGame
from switch2db.title_mapper import PUBLISHER_SEPARATOR, list_publishers


class CatalogEntry(BaseModel):
    """Juego de Switch 2 en IGDB, candidato a entrar en title_seeds.yaml."""

    igdb_id: int = Field(..., description="Id del juego en IGDB")
    name: str = Field(..., description="Nombre del juego")
    game_type: str | None = Field(None, description="Tipo de juego en IGDB (main game, port, bundle...)")
    first_release_date: date | None = Field(
        None, description="Primer lanzamiento en cualquier plataforma, no necesariamente en Switch 2"
    )
    publishers: str | None = Field(None, description="Publishers según IGDB")


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
    """Construye el catálogo ordenado por nombre sin distinguir mayúsculas."""
    return sorted((build_catalog_entry(game) for game in games), key=lambda entry: entry.name.casefold())
