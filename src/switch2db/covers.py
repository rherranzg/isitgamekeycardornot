from collections.abc import Iterable, Sequence
from datetime import date
from enum import StrEnum
from pathlib import Path

import requests
from pydantic import BaseModel, Field

from switch2db.cover_image import is_switch2_box, open_image, save_thumbnail, trim_white_margin
from switch2db.mediamarkt import ProductPage, find_product_page
from switch2db.models import GTIN13_LENGTH, Cover, Edition, Region, Sku
from switch2db.quote import REQUEST_TIMEOUT_SECONDS, USER_AGENT

# Only the European box has an automatic source for now (MediaMarkt Spain).
COVER_REGION = Region.EU


class CoverOutcome(StrEnum):
    """What happened when looking for the box of a SKU."""

    DOWNLOADED = "downloaded"
    NOT_FOUND = "not_found"  # no Switch 2 product page with the game's name
    EAN_MISMATCH = "ean_mismatch"  # the page is another product than the SKU (different barcode)
    NOT_A_SWITCH2_BOX = "not_a_switch2_box"  # the image lacks the red header (another platform, artwork)


class CoverResult(BaseModel):
    """Result of looking for the box of a SKU."""

    sku_id: str = Field(..., description="SKU looked for")
    outcome: CoverOutcome = Field(..., description="What happened")
    product_url: str | None = Field(None, description="Product page used, if one was found")


def cover_path(covers_dir: Path, sku_id: str) -> Path:
    """File where the box of a SKU is stored."""
    return covers_dir / f"{sku_id}.webp"


def select_cover_skus(skus: Iterable[Sku], covers: Iterable[Cover], refresh: bool) -> list[Sku]:
    """Standard SKUs of the cover region; without a cover yet, or all of them with refresh."""
    covered = {cover.sku_id for cover in covers}
    return [
        sku
        for sku in skus
        if sku.region == COVER_REGION
        and sku.edition == Edition.STANDARD
        and (refresh or sku.sku_id not in covered)
    ]


def ean_matches(sku: Sku, product: ProductPage) -> bool:
    """False only if both have a barcode and they differ (a UPC-A is compared as its EAN-13)."""
    if sku.ean is None or product.ean is None:
        return True
    return sku.ean.zfill(GTIN13_LENGTH) == product.ean.zfill(GTIN13_LENGTH)


def download_image(url: str) -> bytes:
    """Download an image with the project's User-Agent."""
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.content


def fetch_cover(sku: Sku, game_name: str, covers_dir: Path, today: date) -> tuple[CoverResult, Cover | None]:
    """Look for the SKU's box, check it is a Switch 2 box and store it; the Cover only if it was stored."""
    product = find_product_page(game_name)
    if product is None:
        return CoverResult(sku_id=sku.sku_id, outcome=CoverOutcome.NOT_FOUND), None
    if not ean_matches(sku, product):
        return CoverResult(
            sku_id=sku.sku_id, outcome=CoverOutcome.EAN_MISMATCH, product_url=product.url
        ), None
    box = trim_white_margin(open_image(download_image(product.image_url)))
    if not is_switch2_box(box):
        result = CoverResult(
            sku_id=sku.sku_id, outcome=CoverOutcome.NOT_A_SWITCH2_BOX, product_url=product.url
        )
        return result, None
    save_thumbnail(box, cover_path(covers_dir, sku.sku_id))
    cover = Cover.model_validate(
        {"sku_id": sku.sku_id, "source_url": product.url, "image_url": product.image_url, "checked_at": today}
    )
    return CoverResult(sku_id=sku.sku_id, outcome=CoverOutcome.DOWNLOADED, product_url=product.url), cover


def merge_covers(existing: Sequence[Cover], new: Sequence[Cover]) -> list[Cover]:
    """Existing covers with the new ones on top (a refreshed SKU keeps only its new cover)."""
    by_sku = {cover.sku_id: cover for cover in existing}
    by_sku.update({cover.sku_id: cover for cover in new})
    return list(by_sku.values())
