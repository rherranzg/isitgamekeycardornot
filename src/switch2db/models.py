from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
GTIN_PATTERN = r"^\d{12,13}$"


class Region(StrEnum):
    """Mercado de un SKU; ASIA agrupa la versión asiática de HK/TW/SEA."""

    EU = "EU"
    NA = "NA"
    JP = "JP"
    KR = "KR"
    ASIA = "ASIA"


class Edition(StrEnum):
    """Edición comercial de un SKU."""

    STANDARD = "standard"
    DELUXE = "deluxe"
    COLLECTORS = "collectors"


class Format(StrEnum):
    """Formato físico en el que se vende el juego."""

    FULL_CART = "full_cart"
    GAME_KEY_CARD = "game_key_card"
    CODE_IN_BOX = "code_in_box"
    UNKNOWN = "unknown"


class Evidence(StrEnum):
    """Nivel de evidencia que respalda el formato de un SKU."""

    OFFICIAL = "official"
    BOX_PHOTO = "box_photo"
    RETAILER_LISTING = "retailer_listing"
    PRESS_REPORT = "press_report"
    UNCONFIRMED = "unconfirmed"


class TitleStatus(StrEnum):
    """Estado de revisión de los datos de un título importados de IGDB."""

    PENDING = "pending"  # importado de IGDB y aún sin comprobar a mano
    REVIEWED = "reviewed"  # comprobado a mano
    REFRESH = "refresh"  # marcado a mano para volver a importarlo de IGDB


class TitleSeed(BaseModel):
    """Juego a importar de IGDB, con su igdb_id fijado a mano."""

    model_config = ConfigDict(extra="forbid")

    title_id: str = Field(..., pattern=SLUG_PATTERN, description="Slug estable propio del juego")
    igdb_id: int = Field(..., gt=0, description="Id del juego en IGDB, comprobado a mano")


class Title(TitleSeed):
    """Juego con los metadatos genéricos importados de IGDB."""

    name: str = Field(..., min_length=1, description="Nombre del juego según IGDB")
    publisher: str = Field(..., min_length=1, description="Publisher global según IGDB")
    status: TitleStatus = Field(..., description="Estado de revisión de los datos importados de IGDB")


def build_sku_id(region: Region, title_id: str, edition: Edition) -> str:
    """Construye el sku_id canónico a partir de región, título y edición."""
    return f"{region.lower()}-{title_id}-{edition}"


class Sku(BaseModel):
    """SKU regional de un juego: la unidad de la base de datos."""

    model_config = ConfigDict(extra="forbid")

    sku_id: str = Field(..., description="Id canónico: {region}-{title_id}-{edition} en minúsculas")
    title_id: str = Field(..., pattern=SLUG_PATTERN, description="Juego al que pertenece el SKU")
    region: Region = Field(..., description="Mercado del SKU")
    edition: Edition = Field(..., description="Edición del SKU")
    distributor: str | None = Field(None, min_length=1, description="Quién lo distribuye en ese mercado")
    release_date: date | None = Field(None, description="Fecha de lanzamiento en ese mercado")
    format: Format = Field(..., description="Formato físico del SKU")
    cart_size_gb: int | None = Field(None, gt=0, description="Capacidad del cartucho en GB")
    download_size_gb: float | None = Field(
        None, ge=0, description="Descarga necesaria en GB; aproximado, cambia con los parches"
    )
    includes_download_code: bool | None = Field(
        None, description="True si la caja trae además del juego un código de descarga (DLC, pase...)"
    )
    ean: str | None = Field(
        None, pattern=GTIN_PATTERN, description="Código de barras EAN-13 o UPC-A, entre comillas en el YAML"
    )
    evidence: Evidence = Field(..., description="Nivel de evidencia del formato")
    source_url: HttpUrl | None = Field(None, description="Fuente que respalda el formato")
    verified_at: date = Field(..., description="Última fecha en que se comprobó la fuente")

    @model_validator(mode="after")
    def check_sku_id_is_canonical(self) -> Self:
        """Falla si sku_id no coincide con el construido a partir de región, título y edición."""
        expected_sku_id = build_sku_id(self.region, self.title_id, self.edition)
        if self.sku_id != expected_sku_id:
            raise ValueError(f"sku_id '{self.sku_id}' debería ser '{expected_sku_id}'")
        return self

    @model_validator(mode="after")
    def check_source_url_when_format_is_known(self) -> Self:
        """Falla si el formato está afirmado pero no hay source_url que lo respalde."""
        if self.format != Format.UNKNOWN and self.source_url is None:
            raise ValueError(f"source_url es obligatorio cuando format es '{self.format}'")
        return self
