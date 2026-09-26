import re
from datetime import UTC, date, datetime

from pydantic import BaseModel, Field

from switch2db.igdb_models import IgdbGame, IgdbReleaseDate

PUBLISHER_SEPARATOR = " / "
NON_ALNUM = re.compile(r"[^a-z0-9]")
# IGDB types that are not a game with its own box. Names are the ones the API returns
# ("DLC", "Pack / Addon"), normalized without spaces or punctuation.
EXCLUDED_GAME_TYPES = {
    "dlc",
    "dlcaddon",
    "pack",
    "packaddon",
    "bundle",
    "expansion",
    "episode",
    "season",
    "mod",
    "update",
    "fork",
}
# Kept in the catalog even though they are never picked as new titles: compilations and editions that IGDB
# marks as Bundle and are added by hand need add_titles to refresh their date.
CATALOG_ONLY_GAME_TYPES = {"bundle"}
QUARTERS_BY_DATE_FORMAT = {"YYYYQ1": 1, "YYYYQ2": 2, "YYYYQ3": 3, "YYYYQ4": 4}


class CatalogEntry(BaseModel):
    """Switch 2 game on IGDB, a candidate for titles.yaml."""

    igdb_id: int = Field(..., description="Game id on IGDB")
    name: str = Field(..., description="Game name")
    game_type: str | None = Field(None, description="Game type on IGDB (main game, port, remaster...)")
    release_date: str | None = Field(
        None,
        description="Release on the platform with IGDB's precision (2026-08-20, 2026-08, 2026-Q3, 2026); "
        "null if IGDB gives no date or it is TBD",
    )
    publishers: str | None = Field(None, description="Publishers according to IGDB")
    version_parent: int | None = Field(
        None, description="IGDB id of the game this entry is an edition of; null if it is not one"
    )


def normalize_game_type(game_type: str) -> str:
    """Normalize the IGDB game type so it can be compared regardless of formatting."""
    return NON_ALNUM.sub("", game_type.lower())


def is_catalog_candidate(game_type: str | None) -> bool:
    """True if the IGDB type can have its own box: no DLC, packs, bundles or expansions."""
    if game_type is None:
        return True
    return normalize_game_type(game_type) not in EXCLUDED_GAME_TYPES


def is_kept_in_catalog(game_type: str | None) -> bool:
    """True if it is kept in the catalog: title candidates and the types only used for dates."""
    return is_catalog_candidate(game_type) or (
        game_type is not None and normalize_game_type(game_type) in CATALOG_ONLY_GAME_TYPES
    )


def list_publishers(game: IgdbGame) -> list[str]:
    """Return, deduplicated and in order, the companies IGDB marks as publisher."""
    return list(
        dict.fromkeys(involved.company.name for involved in game.involved_companies if involved.publisher)
    )


def convert_unix_timestamp_to_date(timestamp: int) -> date:
    """Convert a Unix timestamp in seconds to a UTC date."""
    return datetime.fromtimestamp(timestamp, tz=UTC).date()


def format_release_date(release: IgdbReleaseDate) -> str | None:
    """Format the date with the precision IGDB gives: day, month, quarter or year; None if TBD or missing."""
    if release.date is None or release.y is None or release.date_format is None:
        return None
    date_format = release.date_format.format
    if date_format == "YYYYMMDD":
        return convert_unix_timestamp_to_date(release.date).isoformat()
    if date_format == "YYYYMM" and release.m is not None:
        return f"{release.y:04d}-{release.m:02d}"
    if date_format in QUARTERS_BY_DATE_FORMAT:
        return f"{release.y:04d}-Q{QUARTERS_BY_DATE_FORMAT[date_format]}"
    if date_format == "YYYY":
        return f"{release.y:04d}"
    return None


def find_platform_release_date(game: IgdbGame, platform_id: int) -> str | None:
    """Return the game's release date on the platform; if there are several (one per region), the
    earliest. IGDB stores year or quarter dates as the last day of the period, so within the same
    period the exact date wins."""
    candidates = [
        (release.date, text)
        for release in game.release_dates
        if release.platform == platform_id
        and release.date is not None
        and (text := format_release_date(release)) is not None
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: candidate[0])[1]


def build_catalog_entry(game: IgdbGame, platform_id: int) -> CatalogEntry:
    """Summarize an IGDB game as a catalog entry, with its release date on the platform."""
    publishers = list_publishers(game)
    return CatalogEntry(
        igdb_id=game.id,
        name=game.name,
        game_type=game.game_type.type if game.game_type else None,
        release_date=find_platform_release_date(game, platform_id),
        publishers=PUBLISHER_SEPARATOR.join(publishers) if publishers else None,
        version_parent=game.version_parent,
    )


def build_catalog(games: list[IgdbGame], platform_id: int) -> list[CatalogEntry]:
    """Build the catalog without the discarded types (Bundles stay, only for dates), sorted
    by name."""
    entries = (build_catalog_entry(game, platform_id) for game in games)
    candidates = (entry for entry in entries if is_kept_in_catalog(entry.game_type))
    return sorted(candidates, key=lambda entry: entry.name.casefold())
