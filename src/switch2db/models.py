from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
GTIN_PATTERN = r"^\d{12,13}$"
GTIN13_LENGTH = 13


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


class SkuStatus(StrEnum):
    """Estado de revisión de un SKU. La web publica todos los status."""

    NEW = "new"  # borrador que nadie ha buscado todavía: sale como formato desconocido
    PENDING = "pending"  # buscado sin encontrar fuente: sale como formato desconocido, falta buscar a fondo
    REVIEWED = "reviewed"  # comprobado abriendo la fuente: sale con su fuente
    REFRESH = "refresh"  # tiene fuente, pero hay que volver a buscar evidencias en la web; sigue publicado


class TitleStatus(StrEnum):
    """Estado de investigación de un título. La web publica todos los status."""

    NEW = "new"  # sacado del catálogo de IGDB y sin investigar
    PENDING = "pending"  # investigado sin poder confirmar la edición de la caja ni encontrar fuente
    REVIEWED = "reviewed"  # investigado: el igdb_id es la edición de la caja y el resto está comprobado


class Title(BaseModel):
    """Juego de Switch 2 con sus metadatos de IGDB y el estado de su investigación."""

    model_config = ConfigDict(extra="forbid")

    title_id: str = Field(..., pattern=SLUG_PATTERN, description="Slug estable propio del juego")
    igdb_id: int = Field(..., gt=0, description="Id del juego en IGDB")
    name: str = Field(..., min_length=1, description="Nombre del juego según IGDB")
    publisher: str | None = Field(
        None, min_length=1, description="Publisher global según IGDB; null si IGDB no marca ninguno"
    )
    status: TitleStatus = Field(..., description="Estado de investigación del título")


class PhysicalRelease(BaseModel):
    """Resultado de investigar si un juego llegó a tener edición en caja en alguna región."""

    model_config = ConfigDict(extra="forbid")

    title_id: str = Field(..., pattern=SLUG_PATTERN, description="Juego investigado")
    has_physical_release: bool = Field(
        ..., description="True si existe edición en caja en alguna región; False si es solo digital"
    )
    evidence: Evidence = Field(..., description="Nivel de evidencia de lo encontrado")
    source_url: HttpUrl | None = Field(None, description="Fuente que lo respalda")
    checked_at: date = Field(..., description="Fecha en que se comprobó la fuente")

    @model_validator(mode="after")
    def check_source_url_when_evidence_is_confirmed(self) -> Self:
        """Falla si se afirma algo sin fuente; unconfirmed es 'buscado y no encontrado', y no la necesita."""
        if self.evidence != Evidence.UNCONFIRMED and self.source_url is None:
            raise ValueError(f"source_url es obligatorio cuando evidence es '{self.evidence}'")
        return self


def build_sku_id(region: Region, title_id: str, edition: Edition) -> str:
    """Construye el sku_id canónico a partir de región, título y edición."""
    return f"{region.lower()}-{title_id}-{edition}"


def has_valid_gtin_check_digit(code: str) -> bool:
    """Comprueba el dígito de control de un EAN-13 o UPC-A (este, como EAN-13 con un 0 delante)."""
    digits = [int(digit) for digit in code.zfill(GTIN13_LENGTH)]
    weighted_sum = sum(digit * (3 if position % 2 else 1) for position, digit in enumerate(digits[:-1]))
    return (10 - weighted_sum % 10) % 10 == digits[-1]


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
    verified_at: date = Field(
        ..., description="Última fecha en que se comprobó la fuente; en los `pending`, la de la búsqueda"
    )
    status: SkuStatus = Field(..., description="Estado de revisión del SKU; la web publica todos")

    @field_validator("ean")
    @classmethod
    def check_ean_check_digit(cls, ean: str | None) -> str | None:
        """Falla si el código de barras no cuadra con su dígito de control (suele ser una errata)."""
        if ean is not None and not has_valid_gtin_check_digit(ean):
            raise ValueError(f"ean '{ean}' tiene un dígito de control incorrecto")
        return ean

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

    @model_validator(mode="after")
    def check_pending_has_no_source(self) -> Self:
        """Falla si un SKU `pending` trae fuente: `pending` es haberla buscado sin encontrarla."""
        if self.status == SkuStatus.PENDING and self.source_url is not None:
            raise ValueError("status 'pending' es para SKUs sin fuente; con source_url va 'reviewed'")
        return self
