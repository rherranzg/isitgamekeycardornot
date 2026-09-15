from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
import yaml

from switch2db.igdb_models import IgdbGame
from switch2db.models import Sku, Title, TitleSeed


@pytest.fixture
def title_seed() -> TitleSeed:
    """Semilla válida de un juego ficticio."""
    return TitleSeed(title_id="example-game", igdb_id=12345)


@pytest.fixture
def title_row() -> dict[str, object]:
    """Fila válida de titles.yaml que corresponde a title_seed, recién importada."""
    return {
        "title_id": "example-game",
        "igdb_id": 12345,
        "name": "Example Game",
        "publisher": "Example Publisher",
        "status": "pending",
    }


@pytest.fixture
def title(title_row: dict[str, object]) -> Title:
    """Título importado que corresponde a title_seed, pendiente de revisar."""
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
        "ean": "0045496123456",
        "evidence": "box_photo",
        "source_url": "https://example.com/eu",
        "verified_at": "2026-09-13",
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
