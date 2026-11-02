import html
import json
import re
from urllib.parse import quote

import requests
from pydantic import BaseModel, Field

from switch2db.names import normalize_name
from switch2db.quote import REQUEST_TIMEOUT_SECONDS, USER_AGENT

# MediaMarkt Spain: its product pages carry the European box (PEGI) with the image as structured data.
MEDIAMARKT_SITE = "https://www.mediamarkt.es"
SEARCH_URL = f"{MEDIAMARKT_SITE}/es/search.html?query={{query}}"
PRODUCT_PATH = re.compile(r"/es/product/_[a-z0-9-]+\.html")
# Search results mix consoles and packs with the game: their slugs are left out. Editions are told apart by
# the product name (see clean_product_name).
EXCLUDED_SLUG_WORDS = ("consola", "pack", "bundle")
# Product pages fetched per game at most: the right one is among the first results when it exists.
MAX_CANDIDATES = 3
PLATFORM_SLUG = re.compile(r"(nintendo-)?switch-2")
PARENTHESES = re.compile(r"\([^)]*\)")
# "Juego Nintendo Switch 2 - SWITCH 2 RATATAN, Acción": the platform goes first and the genre after a comma.
GENRE_SUFFIX = re.compile(r",[^,]*$")
PLATFORM_PREFIX = re.compile(r"^(juego )?((nintendo )?switch 2 )+")
# Nintendo's own "Nintendo Switch Sports Resort" is listed as "Nintendo Switch 2 Sports Resort".
GAME_PLATFORM_PREFIX = "nintendo switch "
STANDARD_EDITION = re.compile(r"\b(ed|edicion) estandar\b")
JSON_LD = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)
# The page wraps the product in a BuyAction; the ProductGroup is the product of the page itself (hasVariant
# lists the other platforms).
PRODUCT_TYPES = ("Product", "ProductGroup")
# Only MediaMarkt's own images (ASSET_MMS_): those of marketplace sellers (ASSET_MP_) can be another
# region's box (NBA 2K26: the US one, with ESRB, on a listing with a European EAN).
ASSET_ID = re.compile(r"/(ASSET_MMS_\d+)")
# The asset server resizes on the fly; 1000 px is enough to check the box and make the thumbnail.
ASSET_URL = "https://assets.mmsrg.com/isr/166325/c1/-/{asset_id}?x=1000&y=1000&format=jpg&quality=90"


class ProductPage(BaseModel):
    """What a MediaMarkt product page says about the product."""

    url: str = Field(..., description="Product page, for a person to read")
    name: str = Field(..., description="Product name in the store")
    image_url: str = Field(..., description="First product image, from the asset server")
    ean: str | None = Field(None, description="gtin13 of the page, if it has one")


def fetch_text(url: str) -> str:
    """Download a page with the project's User-Agent and return its text."""
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text


def build_search_url(name: str) -> str:
    """Search URL for the Switch 2 box of a game."""
    return SEARCH_URL.format(query=quote(f"{name} switch 2"))


def find_product_paths(search_page: str) -> list[str]:
    """Switch 2 product paths in a search page, in order, without consoles or packs."""
    paths = list(dict.fromkeys(PRODUCT_PATH.findall(search_page)))
    return [
        path for path in paths if "switch-2" in path and not any(word in path for word in EXCLUDED_SLUG_WORDS)
    ]


def clean_product_name(product_name: str) -> str:
    """Normalized game name inside a product name: without the platform, the genre, what goes in
    parentheses (format, shop bonus) or the standard edition label; any other edition stays."""
    without_extras = PARENTHESES.sub(" ", product_name)
    if without_extras.lower().startswith("juego "):
        without_extras = GENRE_SUFFIX.sub("", without_extras)
    normalized = PLATFORM_PREFIX.sub("", normalize_name(without_extras))
    return normalize_name(STANDARD_EDITION.sub(" ", normalized))


def name_matches(game_name: str, product_name: str) -> bool:
    """True if the product is the standard box of exactly that game (both names normalized)."""
    game = normalize_name(game_name)
    return clean_product_name(product_name) in {game, game.removeprefix(GAME_PLATFORM_PREFIX)}


def slug_matches(game_name: str, path: str) -> bool:
    """True if every word of the game name appears in the slug without the platform ("fctm" contains
    "fc"): a cheap filter before opening the page."""
    without_platform = PLATFORM_SLUG.sub("", path)
    game_words = normalize_name(game_name).removeprefix(GAME_PLATFORM_PREFIX).split()
    return all(word in without_platform for word in game_words)


def unwrap_product(data: object) -> dict[str, object] | None:
    """Product of a JSON-LD block, itself or inside a BuyAction's object; None if it is something else."""
    if not isinstance(data, dict):
        return None
    candidate = data.get("object", data)
    if isinstance(candidate, dict) and candidate.get("@type") in PRODUCT_TYPES:
        return candidate
    return None


def find_product_object(page: str) -> dict[str, object] | None:
    """Product object of the page's structured data (JSON-LD), or None if it has none."""
    for block in JSON_LD.findall(page):
        try:
            product = unwrap_product(json.loads(block))
        except json.JSONDecodeError:
            continue
        if product is not None:
            return product
    return None


def read_first_image(product: dict[str, object]) -> str | None:
    """Asset URL of the first product image, resized for download."""
    images = product.get("image")
    first = images[0] if isinstance(images, list) and images else images
    match = ASSET_ID.search(first) if isinstance(first, str) else None
    return ASSET_URL.format(asset_id=match.group(1)) if match else None


def parse_product_page(url: str, page: str) -> ProductPage | None:
    """Name, first image and EAN of a product page; None if it has no product data or image."""
    product = find_product_object(page)
    if product is None:
        return None
    image_url = read_first_image(product)
    name = product.get("name")
    if image_url is None or not isinstance(name, str):
        return None
    ean = product.get("gtin13")
    return ProductPage(
        url=url, name=html.unescape(name), image_url=image_url, ean=ean if isinstance(ean, str) else None
    )


def find_product_page(game_name: str) -> ProductPage | None:
    """Search the game and return the first Switch 2 product page whose name matches it."""
    paths = find_product_paths(fetch_text(build_search_url(game_name)))
    for path in [path for path in paths if slug_matches(game_name, path)][:MAX_CANDIDATES]:
        url = f"{MEDIAMARKT_SITE}{path}"
        product = parse_product_page(url, fetch_text(url))
        if product is not None and name_matches(game_name, product.name):
            return product
    return None
