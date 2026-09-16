from datetime import date

import pytest
from pydantic import ValidationError

from switch2db.models import (
    Edition,
    PhysicalRelease,
    Region,
    Sku,
    SkuStatus,
    Title,
    TitleStatus,
    build_sku_id,
    has_valid_gtin_check_digit,
)


def test_build_sku_id_success() -> None:
    assert build_sku_id(Region.ASIA, "example-game", Edition.DELUXE) == "asia-example-game-deluxe"


@pytest.mark.parametrize(
    "code,expected",
    [
        ("4902370553413", True),
        ("0045496905576", True),
        ("884095225025", True),
        ("4902370553414", False),
        ("884095225026", False),
    ],
)
def test_has_valid_gtin_check_digit_success(code: str, expected: bool) -> None:
    assert has_valid_gtin_check_digit(code) is expected


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
    row = {field: value for field, value in sku_row.items() if field != "includes_download_code"}

    assert Sku.model_validate(row).includes_download_code is None


def test_sku_model_validate_raises_when_ean_check_digit_is_wrong(sku_row: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="dígito de control incorrecto"):
        Sku.model_validate({**sku_row, "ean": "0045496123456"})


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
    "overrides",
    [
        {"title_id": "Example Game"},
        {"igdb_id": 0},
        {"name": ""},
        {"publisher": ""},
    ],
)
def test_title_model_validate_raises_on_invalid_row(
    title_row: dict[str, object], overrides: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        Title.model_validate({**title_row, **overrides})


def test_title_model_validate_accepts_null_publisher(title_row: dict[str, object]) -> None:
    assert Title.model_validate({**title_row, "publisher": None}).publisher is None


@pytest.mark.parametrize("status", ["new", "pending", "reviewed"])
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


@pytest.mark.parametrize("status", ["new", "reviewed", "refresh"])
def test_sku_model_validate_accepts_every_status_with_source(sku_row: dict[str, object], status: str) -> None:
    assert Sku.model_validate({**sku_row, "status": status}).status == SkuStatus(status)


def test_sku_model_validate_accepts_pending_without_source(sku_row: dict[str, object]) -> None:
    """`pending` es haber buscado la fuente y no encontrarla: sin source_url y con formato desconocido."""
    sku = Sku.model_validate(
        {**sku_row, "format": "unknown", "evidence": "unconfirmed", "source_url": None, "status": "pending"}
    )

    assert sku.status == SkuStatus.PENDING
    assert sku.source_url is None


def test_sku_model_validate_raises_when_pending_has_source_url(sku_row: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="status 'pending' es para SKUs sin fuente"):
        Sku.model_validate({**sku_row, "status": "pending"})


def test_sku_model_validate_raises_when_status_is_missing(sku_row: dict[str, object]) -> None:
    row = {field: value for field, value in sku_row.items() if field != "status"}

    with pytest.raises(ValidationError, match="status"):
        Sku.model_validate(row)


def test_physical_release_model_validate_allows_unconfirmed_without_source() -> None:
    release = PhysicalRelease.model_validate(
        {
            "title_id": "example-game",
            "has_physical_release": False,
            "evidence": "unconfirmed",
            "source_url": None,
            "checked_at": "2026-09-16",
        }
    )

    assert release.has_physical_release is False


def test_physical_release_model_validate_raises_when_claim_has_no_source() -> None:
    with pytest.raises(ValidationError, match="source_url es obligatorio"):
        PhysicalRelease.model_validate(
            {
                "title_id": "example-game",
                "has_physical_release": False,
                "evidence": "official",
                "source_url": None,
                "checked_at": "2026-09-16",
            }
        )
