from datetime import date

import pytest
from pydantic import ValidationError

from switch2db.models import Edition, Region, Sku, Title, TitleSeed, TitleStatus, build_sku_id


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


def test_sku_model_validate_accepts_includes_download_code(sku_row: dict[str, object]) -> None:
    sku = Sku.model_validate({**sku_row, "includes_download_code": True})

    assert sku.includes_download_code is True


def test_sku_model_validate_defaults_includes_download_code_to_unknown(sku_row: dict[str, object]) -> None:
    assert Sku.model_validate(sku_row).includes_download_code is None


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
        {"includes_download_code": "maybe"},
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


@pytest.mark.parametrize("status", ["pending", "reviewed", "refresh"])
def test_title_model_validate_success(title_row: dict[str, object], status: str) -> None:
    assert Title.model_validate({**title_row, "status": status}).status == TitleStatus(status)


@pytest.mark.parametrize("status", ["done", "PENDING", None])
def test_title_model_validate_raises_on_invalid_status(title_row: dict[str, object], status: object) -> None:
    with pytest.raises(ValidationError):
        Title.model_validate({**title_row, "status": status})


def test_title_model_validate_raises_when_status_is_missing(title_row: dict[str, object]) -> None:
    row = {field: value for field, value in title_row.items() if field != "status"}

    with pytest.raises(ValidationError, match="status"):
        Title.model_validate(row)
