from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from pytest_mock import MockerFixture

from switch2db.covers import (
    CoverOutcome,
    cover_path,
    ean_matches,
    fetch_cover,
    merge_covers,
    select_cover_skus,
)
from switch2db.mediamarkt import ProductPage
from switch2db.models import Cover, Sku

TODAY = date(2026, 10, 29)


@pytest.fixture
def product() -> ProductPage:
    """MediaMarkt product of the example game, with the EAN of the EU SKU."""
    return ProductPage(
        url="https://www.mediamarkt.es/es/product/_nintendo-switch-2-example-game-3.html",
        name="Nintendo Switch 2 Example Game",
        image_url="https://assets.mmsrg.com/isr/166325/c1/-/ASSET_MMS_178048931",
        ean="0045496123451",
    )


def image_bytes(image: Image.Image) -> bytes:
    """Encode an image as JPEG, as the asset server returns it."""
    buffer = BytesIO()
    image.save(buffer, "JPEG")
    return buffer.getvalue()


def test_cover_path_success(tmp_path: Path) -> None:
    assert cover_path(tmp_path, "eu-example-game-standard") == tmp_path / "eu-example-game-standard.webp"


def test_select_cover_skus_skips_covered_and_other_regions(
    eu_key_card_sku: Sku, asia_full_cart_sku: Sku, cover: Cover
) -> None:
    assert select_cover_skus([eu_key_card_sku, asia_full_cart_sku], [], refresh=False) == [eu_key_card_sku]
    assert select_cover_skus([eu_key_card_sku], [cover], refresh=False) == []


def test_select_cover_skus_with_refresh_keeps_covered(eu_key_card_sku: Sku, cover: Cover) -> None:
    assert select_cover_skus([eu_key_card_sku], [cover], refresh=True) == [eu_key_card_sku]


def test_select_cover_skus_skips_special_editions(sku_row: dict[str, object]) -> None:
    deluxe = Sku.model_validate(
        {**sku_row, "sku_id": "eu-example-game-deluxe", "edition": "deluxe", "edition_name": "Deluxe Edition"}
    )

    assert select_cover_skus([deluxe], [], refresh=False) == []


@pytest.mark.parametrize(
    "product_ean,expected",
    [("0045496123451", True), ("045496123451", True), (None, True), ("4020628538163", False)],
)
def test_ean_matches_success(
    eu_key_card_sku: Sku, product: ProductPage, product_ean: str | None, expected: bool
) -> None:
    assert ean_matches(eu_key_card_sku, product.model_copy(update={"ean": product_ean})) is expected


def test_fetch_cover_success(
    mocker: MockerFixture,
    tmp_path: Path,
    eu_key_card_sku: Sku,
    product: ProductPage,
    switch2_box: Image.Image,
) -> None:
    mocker.patch("switch2db.covers.find_product_page", return_value=product)
    mocker.patch("switch2db.covers.download_image", return_value=image_bytes(switch2_box))

    result, cover = fetch_cover(eu_key_card_sku, "Example Game", tmp_path, TODAY)

    assert result.outcome == CoverOutcome.DOWNLOADED
    assert cover is not None
    assert str(cover.source_url) == product.url
    assert cover.checked_at == TODAY
    assert (tmp_path / "eu-example-game-standard.webp").exists()


def test_fetch_cover_returns_not_found(mocker: MockerFixture, tmp_path: Path, eu_key_card_sku: Sku) -> None:
    mocker.patch("switch2db.covers.find_product_page", return_value=None)

    result, cover = fetch_cover(eu_key_card_sku, "Example Game", tmp_path, TODAY)

    assert result.outcome == CoverOutcome.NOT_FOUND
    assert cover is None


def test_fetch_cover_rejects_another_barcode(
    mocker: MockerFixture, tmp_path: Path, eu_key_card_sku: Sku, product: ProductPage
) -> None:
    mocker.patch(
        "switch2db.covers.find_product_page", return_value=product.model_copy(update={"ean": "4020628538163"})
    )
    download = mocker.patch("switch2db.covers.download_image")

    result, cover = fetch_cover(eu_key_card_sku, "Example Game", tmp_path, TODAY)

    assert result.outcome == CoverOutcome.EAN_MISMATCH
    assert cover is None
    download.assert_not_called()


def test_fetch_cover_rejects_other_platform_box(
    mocker: MockerFixture,
    tmp_path: Path,
    eu_key_card_sku: Sku,
    product: ProductPage,
    other_platform_box: Image.Image,
) -> None:
    mocker.patch("switch2db.covers.find_product_page", return_value=product)
    mocker.patch("switch2db.covers.download_image", return_value=image_bytes(other_platform_box))

    result, cover = fetch_cover(eu_key_card_sku, "Example Game", tmp_path, TODAY)

    assert result.outcome == CoverOutcome.NOT_A_SWITCH2_BOX
    assert cover is None
    assert not list(tmp_path.iterdir())


def test_merge_covers_replaces_refreshed_sku(cover: Cover) -> None:
    refreshed = cover.model_copy(update={"checked_at": date(2026, 11, 5)})
    other = cover.model_copy(update={"sku_id": "eu-other-game-standard"})

    assert merge_covers([cover, other], [refreshed]) == [refreshed, other]
