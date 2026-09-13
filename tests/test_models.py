from datetime import date

import pytest
from pydantic import ValidationError

from switch2db.models import Edition, Region, Sku, TitleSeed, build_sku_id


def test_build_sku_id_success() -> None:
    assert build_sku_id(Region.ASIA, "example-game", Edition.DELUXE) == "asia-example-game-deluxe"


def test_sku_model_validate_success(sku_row: dict[str, object]) -> None:
    sku = Sku.model_validate(sku_row)

    assert sku.region == Region.EU
    assert sku.release_date == date(2026, 3, 12)
    assert str(sku.source_url) == "https://example.com/eu"


def test_sku_model_validate_raises_when_sku_id_is_not_canonical(sku_row: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="debería ser 'eu-example-game-standard'"):
        Sku.model_validate({**sku_row, "sku_id": "eu-sf6-std"})


@pytest.mark.parametrize("sku_format", ["full_cart", "game_key_card", "code_in_box"])
def test_sku_model_validate_raises_when_known_format_has_no_source_url(
    sku_row: dict[str, object], sku_format: str
) -> None:
    with pytest.raises(ValidationError, match="source_url es obligatorio"):
        Sku.model_validate({**sku_row, "format": sku_format, "source_url": None})


def test_sku_model_validate_allows_missing_source_url_when_format_is_unknown(
    sku_row: dict[str, object],
) -> None:
    sku = Sku.model_validate({**sku_row, "format": "unknown", "source_url": None})

    assert sku.source_url is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"title_id": "Example Game"},
        {"region": "HK"},
        {"edition": "limited"},
        {"format": "digital"},
        {"evidence": "rumor"},
        {"ean": "12345"},
        {"ean": 45496123456},
        {"cart_size_gb": 0},
        {"unexpected_field": "x"},
    ],
)
def test_sku_model_validate_raises_on_invalid_field(
    sku_row: dict[str, object], overrides: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        Sku.model_validate({**sku_row, **overrides})


@pytest.mark.parametrize(
    "row",
    [
        {"title_id": "Example Game", "igdb_id": 1},
        {"title_id": "example-game", "igdb_id": 0},
        {"title_id": "example-game"},
    ],
)
def test_title_seed_model_validate_raises_on_invalid_row(row: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TitleSeed.model_validate(row)
