from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops

# Thumbnail stored for the site: enough to recognize the box and read the PEGI and key card notice.
COVER_WIDTH = 300
WEBP_QUALITY = 80
# Pixels closer than this to white are margin, not box (shop photos have a white background).
MARGIN_TOLERANCE = 20
# Band where the red Nintendo Switch 2 header sits: top 0.5-6% of the box, central 80% of the width.
BAND_TOP = 0.005
BAND_BOTTOM = 0.06
BAND_SIDE = 0.1
BAND_SAMPLE_SIZE = (80, 10)
# Red of the header (Nintendo red, #E60012) with margin for compression and lighting.
MIN_RED = 170
MAX_GREEN = 70
MAX_BLUE = 80
# Real Switch 2 boxes give 0.89-0.97; other platforms and promotional art, 0.00-0.03.
MIN_RED_RATIO = 0.6


def open_image(content: bytes) -> Image.Image:
    """Decode downloaded image bytes as RGB."""
    return Image.open(BytesIO(content)).convert("RGB")


def trim_white_margin(image: Image.Image) -> Image.Image:
    """Crop the white background around the box; the image as it is if it has none."""
    white = Image.new("RGB", image.size, (255, 255, 255))
    difference = ImageChops.difference(image, white).convert("L")
    box = difference.point(lambda value: 255 if value > MARGIN_TOLERANCE else 0).getbbox()
    return image.crop(box) if box else image


def is_header_red(pixel: tuple[int, ...]) -> bool:
    """True if the RGB pixel has the red of the Switch 2 header."""
    red, green, blue = pixel[:3]
    return red > MIN_RED and green < MAX_GREEN and blue < MAX_BLUE


def red_band_ratio(image: Image.Image) -> float:
    """Share of header-red pixels in the top band of a box already cropped to its edges."""
    width, height = image.size
    band = image.crop(
        (
            int(width * BAND_SIDE),
            int(height * BAND_TOP),
            int(width * (1 - BAND_SIDE)),
            int(height * BAND_BOTTOM),
        )
    ).resize(BAND_SAMPLE_SIZE)
    pixels = [band.getpixel((x, y)) for y in range(band.height) for x in range(band.width)]
    return sum(1 for pixel in pixels if isinstance(pixel, tuple) and is_header_red(pixel)) / len(pixels)


def is_switch2_box(image: Image.Image) -> bool:
    """True if the cropped image has the red Nintendo Switch 2 header across its top."""
    return red_band_ratio(image) >= MIN_RED_RATIO


def save_thumbnail(image: Image.Image, path: Path) -> None:
    """Save the box as a COVER_WIDTH-wide WebP, keeping its proportions."""
    height = round(image.height * COVER_WIDTH / image.width)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.resize((COVER_WIDTH, height), Image.Resampling.LANCZOS).save(path, "WEBP", quality=WEBP_QUALITY)
