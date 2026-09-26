from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
import yaml

from switch2db.catalog import CatalogEntry
from switch2db.igdb_models import IgdbGame
from switch2db.models import PhysicalRelease, Sku, Title


@pytest.fixture
def catalog_entry() -> CatalogEntry:
    """IGDB catalog entry that title_row comes from."""
    return CatalogEntry(
        igdb_id=12345,
        name="Example Game",
        game_type="Main Game",
        release_date=None,
        publishers="Example Publisher",
    )


@pytest.fixture
def title_row() -> dict[str, object]:
    """Valid titles.yaml row, researched without confirming the edition."""
    return {
        "title_id": "example-game",
        "igdb_id": 12345,
        "name": "Example Game",
        "publisher": "Example Publisher",
        "release_date": None,
        "status": "pending",
    }


@pytest.fixture
def title(title_row: dict[str, object]) -> Title:
    """Title with status pending: researched without being able to confirm the edition."""
    return Title.model_validate(title_row)


@pytest.fixture
def sku_row() -> dict[str, object]:
    """Valid skus.yaml row as it comes from the YAML: game-key card in EU."""
    return {
        "sku_id": "eu-example-game-standard",
        "title_id": "example-game",
        "region": "EU",
        "edition": "standard",
        "edition_name": None,
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
    """EU SKU as a game-key card."""
    return Sku.model_validate(sku_row)


@pytest.fixture
def asia_full_cart_sku(sku_row: dict[str, object]) -> Sku:
    """SKU of the same game in ASIA as a full cartridge."""
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
    """SKU of the same game in JP with a still unknown format."""
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
    """Freshly written, unreviewed SKU: shown on the site as unknown format."""
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
    """SKU searched without finding a source: shown on the site as unknown format."""
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
    """physical_release.yaml row: the game got no boxed release in any region."""
    return {
        "title_id": "example-game",
        "has_physical_release": False,
        "evidence": "official",
        "source_url": "https://example.com/digital-only",
        "checked_at": "2026-09-16",
    }


@pytest.fixture
def digital_only(digital_only_row: dict[str, object]) -> PhysicalRelease:
    """Game researched and confirmed as digital only."""
    return PhysicalRelease.model_validate(digital_only_row)


@pytest.fixture
def igdb_game_payload() -> dict[str, object]:
    """IGDB response for a game with a developer and a publisher."""
    return {
        "id": 12345,
        "name": "Example Game",
        "release_dates": [
            {
                "id": 1,
                "platform": 6,
                "date": 1715212800,
                "y": 2024,
                "m": 5,
                "date_format": {"id": 0, "format": "YYYYMMDD"},
            },
            {
                "id": 2,
                "platform": 508,
                "date": 1749081600,
                "y": 2025,
                "m": 6,
                "date_format": {"id": 0, "format": "YYYYMMDD"},
            },
        ],
        "game_type": {"id": 0, "type": "Main Game"},
        "involved_companies": [
            {"id": 1, "company": {"id": 10, "name": "Example Developer"}, "publisher": False},
            {"id": 2, "company": {"id": 20, "name": "Example Publisher"}, "publisher": True},
        ],
    }


@pytest.fixture
def igdb_game(igdb_game_payload: dict[str, object]) -> IgdbGame:
    """IGDB game parsed from igdb_game_payload."""
    return IgdbGame.model_validate(igdb_game_payload)


@pytest.fixture
def write_yaml(tmp_path: Path) -> Callable[[str, Sequence[object]], Path]:
    """Return a function that writes a list as YAML inside tmp_path."""

    def _write_yaml(file_name: str, rows: Sequence[object]) -> Path:
        """Write the rows to tmp_path/file_name and return the path."""
        path = tmp_path / file_name
        path.write_text(yaml.safe_dump(list(rows), sort_keys=False, allow_unicode=True), encoding="utf-8")
        return path

    return _write_yaml
