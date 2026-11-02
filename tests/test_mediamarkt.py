import pytest
from pytest_mock import MockerFixture

from switch2db.mediamarkt import (
    ProductPage,
    build_search_url,
    clean_product_name,
    find_product_page,
    find_product_paths,
    name_matches,
    parse_product_page,
    slug_matches,
)

PRODUCT_URL = "https://www.mediamarkt.es/es/product/_nintendo-switch-2-example-game-game-key-card-3.html"


def test_build_search_url_success() -> None:
    assert (
        build_search_url("Tropico 7")
        == "https://www.mediamarkt.es/es/search.html?query=Tropico%207%20switch%202"
    )


def test_find_product_paths_skips_consoles_and_other_platforms(mediamarkt_search_page: str) -> None:
    assert find_product_paths(mediamarkt_search_page) == [
        "/es/product/_nintendo-switch-2-example-game-game-key-card-3.html"
    ]


def test_find_product_paths_returns_empty_list_without_products() -> None:
    assert find_product_paths("<html></html>") == []


@pytest.mark.parametrize(
    "product_name,expected",
    [
        ("Nintendo Switch 2 Danganronpa 2x2", "danganronpa 2x2"),
        ("Nintendo Switch 2 EA SPORTS FC™ 27 (Game Key Card)", "ea sports fc 27"),
        ("Juego Nintendo Switch 2  - SWITCH 2 RATATAN, Acción", "ratatan"),
        ("Juego Nintendo Switch 2  - SWITCH 2 NBA 2K26 ED ESTANDAR, Deportes", "nba 2k26"),
        ("Nintendo Switch 2 Tropico 7 Special Edition (Game Key Card)", "tropico 7 special edition"),
    ],
)
def test_clean_product_name_success(product_name: str, expected: str) -> None:
    assert clean_product_name(product_name) == expected


@pytest.mark.parametrize(
    "game_name,product_name,expected",
    [
        (
            "Final Fantasy VII Revelation",
            "Nintendo Switch 2 Final Fantasy VII Revelation (Magic Card Edition)",
            True,
        ),
        ("Nintendo Switch Sports Resort", "Nintendo Switch 2 Sports Resort", True),
        (
            "Xenoblade Chronicles 2: Nintendo Switch 2 Edition",
            "Nintendo Switch 2 Xenoblade Chronicles 2",
            True,
        ),
        ("Tropico 7", "Nintendo Switch 2 Tropico 7 Special Edition (Game Key Card)", False),
        (
            "Xenoblade Chronicles 2: Nintendo Switch 2 Edition",
            "Nintendo Switch 2 Xenoblade Chronicles: Definitive Edition",
            False,
        ),
        (
            "Xenoblade Chronicles: Definitive Edition",
            "Nintendo Switch 2 Xenoblade Chronicles X: Definitive Edition",
            False,
        ),
    ],
)
def test_name_matches_success(game_name: str, product_name: str, expected: bool) -> None:
    assert name_matches(game_name, product_name) is expected


@pytest.mark.parametrize(
    "game_name,path,expected",
    [
        ("EA Sports FC 27", "/es/product/_nintendo-switch-2-ea-sports-fctm-27-1671140.html", True),
        ("Nintendo Switch Sports Resort", "/es/product/_nintendo-switch-2-sports-resort-1668365.html", True),
        ("Ratatan", "/es/product/_nintendo-switch-2-hot-wheels-1668229.html", False),
    ],
)
def test_slug_matches_success(game_name: str, path: str, expected: bool) -> None:
    assert slug_matches(game_name, path) is expected


def test_parse_product_page_success(mediamarkt_product_page: str) -> None:
    assert parse_product_page(PRODUCT_URL, mediamarkt_product_page) == ProductPage(
        url=PRODUCT_URL,
        name="Nintendo Switch 2 Example Game™ (Game Key Card)",
        image_url="https://assets.mmsrg.com/isr/166325/c1/-/ASSET_MMS_178048931?x=1000&y=1000&format=jpg&quality=90",
        ean="0045496123451",
    )


def test_parse_product_page_returns_none_for_marketplace_images(mediamarkt_product_page: str) -> None:
    page = mediamarkt_product_page.replace("ASSET_MMS_178048931", "ASSET_MP_159463352")

    assert parse_product_page(PRODUCT_URL, page) is None


def test_parse_product_page_returns_none_without_product_data() -> None:
    assert parse_product_page(PRODUCT_URL, '<script type="application/ld+json">not json</script>') is None


def test_find_product_page_success(
    mocker: MockerFixture, mediamarkt_search_page: str, mediamarkt_product_page: str
) -> None:
    fetch = mocker.patch(
        "switch2db.mediamarkt.fetch_text", side_effect=[mediamarkt_search_page, mediamarkt_product_page]
    )

    product = find_product_page("Example Game")

    assert product is not None
    assert product.url == PRODUCT_URL
    assert fetch.call_count == 2


def test_find_product_page_returns_none_when_name_differs(
    mocker: MockerFixture, mediamarkt_search_page: str, mediamarkt_product_page: str
) -> None:
    mocker.patch(
        "switch2db.mediamarkt.fetch_text",
        side_effect=[
            mediamarkt_search_page,
            mediamarkt_product_page.replace("Example Game", "Example Game 2"),
        ],
    )

    assert find_product_page("Example Game") is None
