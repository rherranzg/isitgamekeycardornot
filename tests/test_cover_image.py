from io import BytesIO
from pathlib import Path

from PIL import Image

from switch2db.cover_image import (
    COVER_WIDTH,
    is_header_red,
    is_switch2_box,
    open_image,
    red_band_ratio,
    save_thumbnail,
    trim_white_margin,
)


def test_open_image_success(switch2_box: Image.Image) -> None:
    buffer = BytesIO()
    switch2_box.convert("RGBA").save(buffer, "PNG")

    image = open_image(buffer.getvalue())

    assert image.mode == "RGB"
    assert image.size == switch2_box.size


def test_trim_white_margin_success(switch2_box: Image.Image) -> None:
    assert trim_white_margin(switch2_box).size == (300, 600)


def test_trim_white_margin_keeps_image_without_margin() -> None:
    white = Image.new("RGB", (10, 10), (255, 255, 255))

    assert trim_white_margin(white).size == (10, 10)


def test_is_header_red_success() -> None:
    assert is_header_red((230, 0, 18))
    assert not is_header_red((0, 60, 200))


def test_red_band_ratio_success(switch2_box: Image.Image) -> None:
    assert red_band_ratio(trim_white_margin(switch2_box)) == 1.0


def test_is_switch2_box_success(switch2_box: Image.Image) -> None:
    assert is_switch2_box(trim_white_margin(switch2_box))


def test_is_switch2_box_rejects_other_platform(other_platform_box: Image.Image) -> None:
    assert not is_switch2_box(trim_white_margin(other_platform_box))


def test_save_thumbnail_success(tmp_path: Path, switch2_box: Image.Image) -> None:
    path = tmp_path / "covers" / "eu-example-game-standard.webp"

    save_thumbnail(trim_white_margin(switch2_box), path)

    with Image.open(path) as saved:
        assert saved.format == "WEBP"
        assert saved.size == (COVER_WIDTH, 600)
