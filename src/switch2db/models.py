from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from switch2db.slug import slugify

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
GTIN_PATTERN = r"^\d{12,13}$"
GTIN13_LENGTH = 13
# Date with whatever precision is known: day (2026-08-20), month (2026-08), quarter (2026-Q3) or year (2026).
RELEASE_DATE_PATTERN = r"^\d{4}(?:-Q[1-4]|-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?)?$"


class Region(StrEnum):
    """Market of a SKU; ASIA covers the Asian release for HK/TW/SEA."""

    EU = "EU"
    NA = "NA"
    JP = "JP"
    KR = "KR"
    ASIA = "ASIA"


class Edition(StrEnum):
    """Commercial edition of a SKU."""

    STANDARD = "standard"
    DELUXE = "deluxe"
    COLLECTORS = "collectors"


class Format(StrEnum):
    """Physical format the game is sold in."""

    FULL_CART = "full_cart"
    GAME_KEY_CARD = "game_key_card"
    CODE_IN_BOX = "code_in_box"
    UNKNOWN = "unknown"


class Evidence(StrEnum):
    """Level of evidence backing a SKU's format."""

    OFFICIAL = "official"
    BOX_PHOTO = "box_photo"
    RETAILER_LISTING = "retailer_listing"
    PRESS_REPORT = "press_report"
    UNCONFIRMED = "unconfirmed"


class SkuStatus(StrEnum):
    """Review status of a SKU. The site publishes every status."""

    NEW = "new"  # draft nobody has searched yet: shown as unknown format
    PENDING = "pending"  # searched without finding a source: shown as unknown format, needs a deeper search
    REVIEWED = "reviewed"  # checked by opening the source: shown with its source
    REFRESH = "refresh"  # has a source, but evidence must be searched for again on the web; still published


class TitleStatus(StrEnum):
    """Research status of a title. The site publishes every status."""

    NEW = "new"  # taken from the IGDB catalog, not researched
    PENDING = "pending"  # researched without confirming the boxed edition or finding a source
    REVIEWED = "reviewed"  # researched: igdb_id is the game's (not an edition's) and the rest checks out


class Title(BaseModel):
    """Switch 2 game with its IGDB metadata and its research status."""

    model_config = ConfigDict(extra="forbid")

    title_id: str = Field(..., pattern=SLUG_PATTERN, description="Stable slug of the game")
    igdb_id: int = Field(..., gt=0, description="Game id on IGDB")
    name: str = Field(..., min_length=1, description="Game name according to IGDB")
    publisher: str | None = Field(
        None, min_length=1, description="Global publisher according to IGDB; null if IGDB marks none"
    )
    release_date: str | None = Field(
        None,
        pattern=RELEASE_DATE_PATTERN,
        description="Switch 2 release according to IGDB, with whatever precision is known; null if unknown",
    )
    status: TitleStatus = Field(..., description="Research status of the title")


class ExcludedTitle(BaseModel):
    """IGDB catalog game that is not cataloged here, with the reason."""

    model_config = ConfigDict(extra="forbid")

    igdb_id: int = Field(..., gt=0, description="Game id on IGDB")
    name: str = Field(..., min_length=1, description="Game name according to IGDB, to make the file readable")
    reason: str = Field(..., min_length=1, description="Why it is not cataloged")
    former_title_id: str | None = Field(
        None, pattern=SLUG_PATTERN, description="title_id it had in titles.yaml, if it was ever published"
    )
    merged_into: str | None = Field(
        None,
        pattern=SLUG_PATTERN,
        description="Title that covers it now; the site redirects its old anchor there",
    )

    @model_validator(mode="after")
    def check_former_title_id_goes_with_merged_into(self) -> Self:
        """Fail if only one of the two is set: without the other the old anchor cannot be redirected."""
        if (self.former_title_id is None) != (self.merged_into is None):
            raise ValueError("former_title_id and merged_into go together: both or neither")
        return self


class PhysicalRelease(BaseModel):
    """Result of researching whether a game ever got a boxed edition in any region."""

    model_config = ConfigDict(extra="forbid")

    title_id: str = Field(..., pattern=SLUG_PATTERN, description="Researched game")
    has_physical_release: bool = Field(
        ..., description="True if a boxed edition exists in some region; False if digital only"
    )
    evidence: Evidence = Field(..., description="Level of evidence of the finding")
    source_url: HttpUrl | None = Field(None, description="Source that backs it")
    checked_at: date = Field(..., description="Date the source was checked")

    @model_validator(mode="after")
    def check_source_url_when_evidence_is_confirmed(self) -> Self:
        """Fail if something is claimed without a source; unconfirmed ('searched, not found') needs none."""
        if self.evidence != Evidence.UNCONFIRMED and self.source_url is None:
            raise ValueError(f"source_url is required when evidence is '{self.evidence}'")
        return self


def build_sku_id(region: Region, title_id: str, edition: Edition) -> str:
    """Build the canonical sku_id from region, title and edition."""
    return f"{region.lower()}-{title_id}-{edition}"


def has_valid_gtin_check_digit(code: str) -> bool:
    """Check the check digit of an EAN-13 or UPC-A (the latter as an EAN-13 with a leading 0)."""
    digits = [int(digit) for digit in code.zfill(GTIN13_LENGTH)]
    weighted_sum = sum(digit * (3 if position % 2 else 1) for position, digit in enumerate(digits[:-1]))
    return (10 - weighted_sum % 10) % 10 == digits[-1]


class Sku(BaseModel):
    """Regional SKU of a game: the unit of the database."""

    model_config = ConfigDict(extra="forbid")

    sku_id: str = Field(
        ...,
        description="Canonical id: {region}-{title_id}-{edition} in lowercase; if two SKUs clash, followed "
        "by the edition_name slug",
    )
    title_id: str = Field(..., pattern=SLUG_PATTERN, description="Game the SKU belongs to")
    region: Region = Field(..., description="Market of the SKU")
    edition: Edition = Field(..., description="Edition of the SKU")
    edition_name: str | None = Field(
        None,
        min_length=1,
        description='Commercial name of the edition ("Gold Edition"); null for the standard one',
    )
    distributor: str | None = Field(None, min_length=1, description="Who distributes it in that market")
    release_date: date | None = Field(None, description="Release date in that market")
    format: Format = Field(..., description="Physical format of the SKU")
    cart_size_gb: int | None = Field(None, gt=0, description="Cartridge capacity in GB")
    download_size_gb: float | None = Field(
        None, ge=0, description="Required download in GB; approximate, changes with patches"
    )
    includes_download_code: bool | None = Field(
        None, description="True if the box also includes a download code besides the game (DLC, pass...)"
    )
    ean: str | None = Field(
        None, pattern=GTIN_PATTERN, description="EAN-13 or UPC-A barcode, quoted in the YAML"
    )
    evidence: Evidence = Field(..., description="Level of evidence for the format")
    source_url: HttpUrl | None = Field(None, description="Source that backs the format")
    verified_at: date = Field(
        ..., description="Last date the source was checked; for `pending`, the date of the search"
    )
    status: SkuStatus = Field(..., description="Review status of the SKU; the site publishes all of them")

    @field_validator("ean")
    @classmethod
    def check_ean_check_digit(cls, ean: str | None) -> str | None:
        """Fail if the barcode does not match its check digit (usually a typo)."""
        if ean is not None and not has_valid_gtin_check_digit(ean):
            raise ValueError(f"ean '{ean}' has a wrong check digit")
        return ean

    @model_validator(mode="after")
    def check_sku_id_is_canonical(self) -> Self:
        """Fail if sku_id is not the one built from region, title and edition. To tell apart two editions
        of the same type in one region, the edition_name slug is also allowed as a suffix."""
        expected_sku_id = build_sku_id(self.region, self.title_id, self.edition)
        allowed = {expected_sku_id}
        if self.edition_name is not None:
            allowed.add(f"{expected_sku_id}-{slugify(self.edition_name)}")
        if self.sku_id not in allowed:
            raise ValueError(f"sku_id '{self.sku_id}' should be '{expected_sku_id}'")
        return self

    @model_validator(mode="after")
    def check_source_url_when_format_is_known(self) -> Self:
        """Fail if the format is claimed but there is no source_url backing it."""
        if self.format != Format.UNKNOWN and self.source_url is None:
            raise ValueError(f"source_url is required when format is '{self.format}'")
        return self

    @model_validator(mode="after")
    def check_pending_has_no_source(self) -> Self:
        """Fail if a `pending` SKU has a source: `pending` means it was searched for and not found."""
        if self.status == SkuStatus.PENDING and self.source_url is not None:
            raise ValueError("status 'pending' is for SKUs without a source; with source_url use 'reviewed'")
        return self
