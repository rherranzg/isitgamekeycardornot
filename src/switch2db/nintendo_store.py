import re
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import date
from enum import StrEnum

import requests
from pydantic import BaseModel, Field

from switch2db.models import Region, Sku, Title
from switch2db.names import normalize_name
from switch2db.quote import REQUEST_TIMEOUT_SECONDS, USER_AGENT

# Undocumented public APIs of the Nintendo stores (Solr EU, Algolia NA, search.nintendo.jp): fragile sources.
EU_SEARCH_URL = "https://searching.nintendo-europe.com/en/select"
EU_MAX_ROWS = 3000
# From this year on, the EU date is a "to be announced" placeholder (2050-12-31), not a date.
PLACEHOLDER_YEAR = 2050
# EU and NA write "sometime in 2027" as 2027-12-31: it is kept as the year, not as a day.
YEAR_ONLY_SUFFIX = "-12-31"
NA_SEARCH_URL = "https://U3B6GR4UA3-dsn.algolia.net/1/indexes/store_game_en_us/query"
# Search-only key used by the nintendo.com frontend; if it stops working, get it again from the site's JS.
NA_HEADERS = {
    "User-Agent": USER_AGENT,
    "X-Algolia-Application-Id": "U3B6GR4UA3",
    "X-Algolia-API-Key": "a29c6927638bfd8cee23993e51e721c9",
}
# Games only: single DLC, bundles and upgrade packs are left out (the latter by isUpgrade, client side).
NA_FILTER = (
    'corePlatforms:"Nintendo Switch 2" AND NOT dlcType:"Individual" AND NOT dlcType:"Bundle" '
    'AND NOT dlcType:"ROM Bundle"'
)
NA_HITS_PER_PAGE = 500
# Algolia never returns more than 1000 hits for one query: beyond that the filter must be split.
NA_MAX_HITS = 1000
JP_SEARCH_URL = "https://search.nintendo.jp/nintendo_soft/search.json"
JP_PAGE_SIZE = 300
JP_MAX_PAGES = 20
# sform of the JP games and whether it says there is a boxed version (パッケージ版). BEE_GC (GameCube
# classics), DLC, bundles and hardware are left out; a game without sform is an announcement without a page.
JP_PACKAGE_BY_FORM: dict[str | None, bool | None] = {
    "BEE_DL": False,
    "BEE_DOWNLOADABLE": True,
    "BEE_CARD": True,
    None: None,
}
JP_EXACT_DATE = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$")
JP_UNDECIDED = "未定"
EXACT_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COMPARED_REGIONS = (Region.EU, Region.NA)


class StoreEntry(BaseModel):
    """Switch 2 game in a Nintendo store, as kept in the local snapshot."""

    region: Region = Field(..., description="Store region: EU, NA or JP")
    product_id: str = Field(..., description="Product id in that store (fs_id in EU, nsuid in NA and JP)")
    name: str = Field(..., description="Name in the store (in Japanese in JP)")
    release_date: str | None = Field(
        None, description="Release date: ISO day, or the store's own text if it is not a day ('2027.春')"
    )
    has_package: bool | None = Field(
        None, description="JP only: True if the store lists a boxed version (パッケージ版)"
    )


class ChangeKind(StrEnum):
    """What changed in a store since the previous snapshot."""

    NEW = "new"  # product that was not in the store
    RELEASE_DATE = "release_date"
    PACKAGE = "package"  # JP: the store now lists (or no longer lists) a boxed version


class StoreChange(BaseModel):
    """Change of a store product since the previous snapshot."""

    region: Region = Field(..., description="Store region")
    product_id: str = Field(..., description="Product id in that store")
    name: str = Field(..., description="Name in the store")
    kind: ChangeKind = Field(..., description="What changed")
    before: str | bool | None = Field(None, description="Previous value (null for a new product)")
    after: str | bool | None = Field(None, description="Current value")
    title_id: str | None = Field(None, description="Title it matches by name (EU and NA only)")


class DateMismatch(StrEnum):
    """Why a title date does not agree with the stores."""

    MISSING = "missing"  # the title has no date and the store has a day
    LESS_PRECISE = "less_precise"  # the title has month, quarter or year and the store has a day
    STORE_EARLIER = "store_earlier"  # a store gives an earlier day: the title is the first release
    STORE_LATER = "store_later"  # the stores give a later day and the title's has not come yet: a delay?


class TitleDateFinding(BaseModel):
    """Title whose release date does not agree with the EU and NA stores."""

    title_id: str = Field(..., description="Title")
    name: str = Field(..., description="Title name")
    title_date: str | None = Field(None, description="release_date in titles.yaml")
    store_dates: dict[str, str] = Field(..., description="Day in each store that lists it (EU, NA)")
    reason: DateMismatch = Field(..., description="How they disagree")


class SkuDateFinding(BaseModel):
    """Dated SKU whose region's store gives a later day than the box: the game may have been delayed."""

    sku_id: str = Field(..., description="SKU")
    title_id: str = Field(..., description="Title of the SKU")
    sku_date: str = Field(..., description="release_date of the SKU")
    store_date: str = Field(..., description="Day in the store of the SKU's region")


def read_store_day(timestamp: object) -> str | None:
    """Turn an EU or NA store timestamp into the date it means: ISO day, the year alone when the store
    uses 31 December for "sometime that year", or None for a "to be announced" placeholder."""
    if not timestamp:
        return None
    day = str(timestamp)[:10]
    if int(day[:4]) >= PLACEHOLDER_YEAR:
        return None
    return day[:4] if day.endswith(YEAR_ONLY_SUFFIX) else day


def parse_eu_doc(doc: dict[str, object]) -> StoreEntry:
    """Turn an EU Solr document into an entry; the first released date is the game's."""
    dates = doc.get("dates_released_dts") or []
    return StoreEntry(
        region=Region.EU,
        product_id=str(doc["fs_id"]),
        name=str(doc["title"]),
        release_date=read_store_day(dates[0]) if isinstance(dates, list) and dates else None,
    )


def fetch_eu_entries() -> list[StoreEntry]:
    """Download the Switch 2 games of the EU store (UK locale)."""
    params = {
        "q": "*",
        "fq": ["type:GAME", "playable_on_txt:BEE"],
        "fl": "fs_id,title,dates_released_dts",
        "rows": EU_MAX_ROWS,
        "wt": "json",
    }
    response = requests.get(
        EU_SEARCH_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    result = response.json()["response"]
    if result["numFound"] > EU_MAX_ROWS:
        raise ValueError(
            f"The EU store has {result['numFound']} games, more than the {EU_MAX_ROWS} requested"
        )
    return [parse_eu_doc(doc) for doc in result["docs"]]


def parse_na_hit(hit: dict[str, object]) -> StoreEntry:
    """Turn an NA Algolia hit into an entry."""
    return StoreEntry(
        region=Region.NA,
        product_id=str(hit.get("nsuid") or hit["objectID"]),
        name=str(hit["title"]),
        release_date=read_store_day(hit.get("releaseDate")),
    )


def fetch_na_entries() -> list[StoreEntry]:
    """Download the Switch 2 games of the NA store, page by page, without upgrade packs."""
    hits: list[dict[str, object]] = []
    page = 0
    while True:
        body = {"query": "", "filters": NA_FILTER, "hitsPerPage": NA_HITS_PER_PAGE, "page": page}
        response = requests.post(
            NA_SEARCH_URL, json=body, headers=NA_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        result = response.json()
        if result["nbHits"] > NA_MAX_HITS:
            raise ValueError(f"The NA store returns {result['nbHits']} games: the filter must be split")
        hits.extend(result["hits"])
        page += 1
        if page >= result["nbPages"]:
            break
    return [parse_na_hit(hit) for hit in hits if not hit.get("isUpgrade")]


def parse_jp_date(sdate: str | None) -> str | None:
    """Turn the JP date ('2026.11.5') into ISO; other texts ('2027.春') are kept and '未定' is None."""
    if not sdate or sdate == JP_UNDECIDED:
        return None
    match = JP_EXACT_DATE.match(sdate)
    if match is None:
        return sdate
    year, month, day = (int(part) for part in match.groups())
    return date(year, month, day).isoformat()


def parse_jp_item(item: dict[str, object]) -> StoreEntry | None:
    """Turn a JP item into an entry; None if it is not a game (DLC, bundle, hardware, GameCube)."""
    form = item.get("sform")
    if form not in JP_PACKAGE_BY_FORM:
        return None
    sdate = item.get("sdate")
    return StoreEntry(
        region=Region.JP,
        product_id=str(item["id"]),
        name=str(item["title"]),
        release_date=parse_jp_date(str(sdate) if sdate else None),
        has_package=JP_PACKAGE_BY_FORM[form if isinstance(form, str) else None],
    )


def fetch_jp_entries() -> list[StoreEntry]:
    """Download the Switch 2 games of the JP store, page by page."""
    items: list[dict[str, object]] = []
    for page in range(1, JP_MAX_PAGES + 1):
        params = {"opt_hard": "05_BEE", "limit": JP_PAGE_SIZE, "page": page}
        response = requests.get(
            JP_SEARCH_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        result = response.json()["result"]
        items.extend(result["items"])
        if not result["items"] or len(items) >= result["total"]:
            return [entry for item in items if (entry := parse_jp_item(item)) is not None]
    raise ValueError(f"The JP store has more than {JP_MAX_PAGES * JP_PAGE_SIZE} products")


def entry_key(entry: StoreEntry) -> tuple[Region, str]:
    """Identify a store product across snapshots."""
    return entry.region, entry.product_id


def match_entries_to_titles(
    entries: Iterable[StoreEntry], titles: Sequence[Title]
) -> dict[tuple[Region, str], str]:
    """Match EU and NA products to titles by normalized name. A name shared by two titles, or by two
    products of the same store, is ambiguous and left out."""
    name_counts = Counter(normalize_name(title.name) for title in titles)
    title_by_name = {
        normalize_name(title.name): title.title_id
        for title in titles
        if name_counts[normalize_name(title.name)] == 1
    }
    compared = [entry for entry in entries if entry.region in COMPARED_REGIONS]
    product_counts = Counter((entry.region, normalize_name(entry.name)) for entry in compared)
    return {
        entry_key(entry): title_by_name[name]
        for entry in compared
        if (name := normalize_name(entry.name)) in title_by_name and product_counts[(entry.region, name)] == 1
    }


def diff_snapshots(
    previous: Sequence[StoreEntry], current: Sequence[StoreEntry], title_ids: dict[tuple[Region, str], str]
) -> list[StoreChange]:
    """Return what changed in the stores between two snapshots: new products, dates and JP boxes.
    Products that disappear are not reported."""
    previous_by_key = {entry_key(entry): entry for entry in previous}
    changes: list[StoreChange] = []
    for entry in current:
        before = previous_by_key.get(entry_key(entry))
        common = {
            "region": entry.region,
            "product_id": entry.product_id,
            "name": entry.name,
            "title_id": title_ids.get(entry_key(entry)),
        }
        if before is None:
            changes.append(StoreChange(**common, kind=ChangeKind.NEW, after=entry.release_date))
            continue
        if before.release_date != entry.release_date:
            changes.append(
                StoreChange(
                    **common,
                    kind=ChangeKind.RELEASE_DATE,
                    before=before.release_date,
                    after=entry.release_date,
                )
            )
        if before.has_package != entry.has_package:
            changes.append(
                StoreChange(
                    **common, kind=ChangeKind.PACKAGE, before=before.has_package, after=entry.has_package
                )
            )
    return sorted(changes, key=lambda change: (change.region, change.kind, change.name.casefold()))


def collect_store_dates(
    entries: Iterable[StoreEntry], title_ids: dict[tuple[Region, str], str]
) -> dict[str, dict[str, str]]:
    """Return, per title, the day each store (EU, NA) gives it; products without a day are left out."""
    dates: dict[str, dict[str, str]] = {}
    for entry in entries:
        title_id = title_ids.get(entry_key(entry))
        if title_id is not None and entry.release_date is not None and EXACT_DATE.match(entry.release_date):
            dates.setdefault(title_id, {})[entry.region.value] = entry.release_date
    return dates


def classify_title_date(
    title_date: str | None, store_dates: dict[str, str], since: date, today: date
) -> DateMismatch | None:
    """Tell how a title date disagrees with the store days, or None if it agrees or is old news. Only
    dates on or after `since` count: a game long released with a different day is not news. A past title
    day earlier than the stores is fine: the game came out first in another region (often Japan)."""
    earliest = min(store_dates.values())
    if title_date is None or not EXACT_DATE.match(title_date):
        if earliest < since.isoformat():
            return None
        return DateMismatch.MISSING if title_date is None else DateMismatch.LESS_PRECISE
    if title_date in store_dates.values() or max(title_date, earliest) < since.isoformat():
        return None
    if earliest < title_date:
        return DateMismatch.STORE_EARLIER
    if title_date >= today.isoformat():
        return DateMismatch.STORE_LATER
    return None


def find_title_date_findings(
    titles: Sequence[Title], store_dates: dict[str, dict[str, str]], since: date, today: date
) -> list[TitleDateFinding]:
    """Return the titles whose date does not agree with the EU and NA stores, from `since` on."""
    findings: list[TitleDateFinding] = []
    for title in titles:
        dates = store_dates.get(title.title_id)
        if not dates:
            continue
        reason = classify_title_date(title.release_date, dates, since, today)
        if reason is not None:
            findings.append(
                TitleDateFinding(
                    title_id=title.title_id,
                    name=title.name,
                    title_date=title.release_date,
                    store_dates=dates,
                    reason=reason,
                )
            )
    return findings


def find_sku_date_findings(
    skus: Sequence[Sku], store_dates: dict[str, dict[str, str]], since: date
) -> list[SkuDateFinding]:
    """Return the dated EU and NA SKUs whose region's store now gives a later day, from `since` on: the
    game may have been delayed. An earlier store day is not reported, since boxes often come out after the
    digital game. It is a lead, not a fix."""
    findings: list[SkuDateFinding] = []
    for sku in skus:
        if sku.release_date is None or sku.region not in COMPARED_REGIONS:
            continue
        store_date = store_dates.get(sku.title_id, {}).get(sku.region.value)
        sku_date = sku.release_date.isoformat()
        if store_date is None or store_date <= sku_date or store_date < since.isoformat():
            continue
        findings.append(
            SkuDateFinding(sku_id=sku.sku_id, title_id=sku.title_id, sku_date=sku_date, store_date=store_date)
        )
    return findings
