from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
import yaml

from switch2db.catalog import CatalogEntry
from switch2db.igdb_models import IgdbGame
from switch2db.models import PhysicalRelease, Sku, Title


@pytest.fixture
def catalog_entry() -> CatalogEntry:
    """Entrada del catálogo de IGDB de la que sale title_row."""
    return CatalogEntry(
        igdb_id=12345,
        name="Example Game",
        game_type="Main Game",
        first_release_date=None,
        publishers="Example Publisher",
    )


@pytest.fixture
def title_row() -> dict[str, object]:
    """Fila válida de titles.yaml, ya investigada sin confirmar la edición."""
    return {
        "title_id": "example-game",
        "igdb_id": 12345,
        "name": "Example Game",
        "publisher": "Example Publisher",
        "status": "pending",
    }


@pytest.fixture
def title(title_row: dict[str, object]) -> Title:
    """Título con status pending: investigado sin poder confirmar la edición."""
    return Title.model_validate(title_row)


@pytest.fixture
def sku_row() -> dict[str, object]:
    """Fila válida de skus.yaml tal como llega del YAML: game-key card en EU."""
    return {
        "sku_id": "eu-example-game-standard",
        "title_id": "example-game",
        "region": "EU",
        "edition": "standard",
        "distributor": "Example Distributor",
        "release_date": "2026-03-12",
        "format": "game_key_card",
        "cart_size_gb": None,
        "download_size_gb": 20.5,
        "includes_download_code": None,
        "ean": "0045496123451",
        "evidence": "box_photo",
        "source_url": "https://example.com/eu",
        "verified_at": "2026-09-13",
        "status": "reviewed",
    }


@pytest.fixture
def eu_key_card_sku(sku_row: dict[str, object]) -> Sku:
    """SKU de EU en game-key card."""
    return Sku.model_validate(sku_row)


@pytest.fixture
def asia_full_cart_sku(sku_row: dict[str, object]) -> Sku:
    """SKU del mismo juego en ASIA en cartucho completo."""
    return Sku.model_validate(
        {
            **sku_row,
            "sku_id": "asia-example-game-standard",
            "region": "ASIA",
            "format": "full_cart",
            "cart_size_gb": 64,
            "source_url": "https://example.com/asia",
        }
    )


@pytest.fixture
def jp_unknown_sku(sku_row: dict[str, object]) -> Sku:
    """SKU del mismo juego en JP con formato aún desconocido."""
    return Sku.model_validate(
        {
            **sku_row,
            "sku_id": "jp-example-game-standard",
            "region": "JP",
            "format": "unknown",
            "evidence": "unconfirmed",
            "source_url": None,
        }
    )


@pytest.fixture
def new_sku(sku_row: dict[str, object]) -> Sku:
    """SKU recién escrito y sin revisar: sale en la web como formato desconocido."""
    return Sku.model_validate(
        {
            **sku_row,
            "sku_id": "na-example-game-standard",
            "region": "NA",
            "format": "unknown",
            "download_size_gb": None,
            "evidence": "unconfirmed",
            "source_url": None,
            "status": "new",
        }
    )


@pytest.fixture
def pending_sku(sku_row: dict[str, object]) -> Sku:
    """SKU buscado sin encontrar fuente: sale en la web como formato desconocido."""
    return Sku.model_validate(
        {
            **sku_row,
            "sku_id": "kr-example-game-standard",
            "region": "KR",
            "format": "unknown",
            "download_size_gb": None,
            "evidence": "unconfirmed",
            "source_url": None,
            "status": "pending",
        }
    )


@pytest.fixture
def digital_only_row() -> dict[str, object]:
    """Fila de physical_release.yaml: el juego no salió en caja en ninguna región."""
    return {
        "title_id": "example-game",
        "has_physical_release": False,
        "evidence": "official",
        "source_url": "https://example.com/digital-only",
        "checked_at": "2026-09-16",
    }


@pytest.fixture
def digital_only(digital_only_row: dict[str, object]) -> PhysicalRelease:
    """Juego investigado y confirmado como solo digital."""
    return PhysicalRelease.model_validate(digital_only_row)


@pytest.fixture
def igdb_game_payload() -> dict[str, object]:
    """Respuesta de IGDB para un juego con desarrolladora y publisher."""
    return {
        "id": 12345,
        "name": "Example Game",
        "first_release_date": 1749081600,
        "game_type": {"id": 0, "type": "Main Game"},
        "involved_companies": [
            {"id": 1, "company": {"id": 10, "name": "Example Developer"}, "publisher": False},
            {"id": 2, "company": {"id": 20, "name": "Example Publisher"}, "publisher": True},
        ],
    }


@pytest.fixture
def igdb_game(igdb_game_payload: dict[str, object]) -> IgdbGame:
    """Juego de IGDB parseado a partir de igdb_game_payload."""
    return IgdbGame.model_validate(igdb_game_payload)


@pytest.fixture
def write_yaml(tmp_path: Path) -> Callable[[str, Sequence[object]], Path]:
    """Devuelve una función que escribe una lista como YAML dentro de tmp_path."""

    def _write_yaml(file_name: str, rows: Sequence[object]) -> Path:
        """Escribe las filas en tmp_path/file_name y devuelve la ruta."""
        path = tmp_path / file_name
        path.write_text(yaml.safe_dump(list(rows), sort_keys=False, allow_unicode=True), encoding="utf-8")
        return path

    return _write_yaml
