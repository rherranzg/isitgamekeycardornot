from collections import defaultdict
from collections.abc import Sequence

from pydantic import BaseModel

from switch2db.divergences import find_format_divergences
from switch2db.i18n import (
    EDITION_LABELS,
    EVIDENCE_LABELS,
    FORMAT_LABELS,
    LANGUAGES,
    MONTH_ABBREVIATIONS,
    REGION_LABELS,
    RELEASE_DATE_TEMPLATES,
    UI_STRINGS,
)
from switch2db.models import Edition, ExcludedTitle, Format, PhysicalRelease, Region, Sku, Title
from switch2db.slug import strip_accents

LocalizedText = dict[str, str]

# Value the format filter uses for games that never got a boxed release: not a Format enum
# value, but visitors look for them in the same place as the others.
NO_BOX_FILTER_VALUE = "no_box"

# Same as NO_BOX_FILTER_VALUE, but for titles that have no documented SKU yet
# (status new/pending, not researched).
NO_SKUS_FILTER_VALUE = "no_skus"

# Games per page the visitor can choose: filtering runs over all of them and only the current page is shown.
PAGE_SIZES: tuple[int, ...] = (10, 20, 50)
DEFAULT_PAGE_SIZE = 10

REPO_URL = "https://github.com/rherranzg/isitgamekeycardornot"
DATA_LICENSE_URL = f"{REPO_URL}/blob/main/data/LICENSE"
REPORT_ISSUE_URL = f"{REPO_URL}/issues/new?template=correction.yml"
IGDB_URL = "https://www.igdb.com"

FORMAT_CSS_CLASSES: dict[Format, str] = {
    Format.FULL_CART: "format-full-cart",
    Format.GAME_KEY_CARD: "format-game-key-card",
    Format.CODE_IN_BOX: "format-code-in-box",
    Format.UNKNOWN: "format-unknown",
}

# Filter labels keyed by plain text: the format filter adds a value that is not a Format.
REGION_FILTER_LABELS: dict[str, LocalizedText] = {region.value: REGION_LABELS[region] for region in Region}
EDITION_FILTER_LABELS: dict[str, LocalizedText] = {
    edition.value: EDITION_LABELS[edition] for edition in Edition
}
FORMAT_FILTER_LABELS: dict[str, LocalizedText] = {
    **{format_.value: FORMAT_LABELS[format_] for format_ in Format},
    NO_BOX_FILTER_VALUE: UI_STRINGS["no_box_filter"],
    NO_SKUS_FILTER_VALUE: UI_STRINGS["no_skus_filter"],
}


class SkuView(BaseModel):
    """Regional SKU translated to readable labels, in each supported language."""

    region: Region
    edition: Edition
    format: Format
    format_label: LocalizedText
    format_css_class: str
    edition_label: LocalizedText
    distributor: str | None
    size_text: LocalizedText
    evidence_label: LocalizedText
    source_url: str | None


class NoBoxView(BaseModel):
    """Note for a game that never got a boxed release, with the source that backs it."""

    note: LocalizedText
    evidence_label: LocalizedText
    source_url: str | None


class TitleView(BaseModel):
    """Game with its SKUs grouped and sorted, ready to show on the site."""

    title_id: str
    name: str
    publisher: str | None
    release_date_text: LocalizedText | None
    search_text: str
    skus: list[SkuView]
    has_divergence: bool
    no_box: NoBoxView | None
    former_title_ids: list[str]


def build_size_text(sku: Sku) -> LocalizedText:
    """Build the SKU size text (cartridge or download) in each language."""
    if sku.cart_size_gb is not None:
        return {lang: f"{sku.cart_size_gb} {UI_STRINGS['cart_suffix'][lang]}" for lang in LANGUAGES}
    if sku.download_size_gb is not None:
        return {lang: f"~{sku.download_size_gb} {UI_STRINGS['download_suffix'][lang]}" for lang in LANGUAGES}
    return dict.fromkeys(LANGUAGES, "—")


def build_sku_view(sku: Sku) -> SkuView:
    """Translate a Sku into the labels and text format the template uses."""
    return SkuView(
        region=sku.region,
        edition=sku.edition,
        format=sku.format,
        format_label=FORMAT_LABELS[sku.format],
        format_css_class=FORMAT_CSS_CLASSES[sku.format],
        edition_label=(
            {lang: sku.edition_name for lang in LANGUAGES}
            if sku.edition_name
            else EDITION_LABELS[sku.edition]
        ),
        distributor=sku.distributor,
        size_text=build_size_text(sku),
        evidence_label=EVIDENCE_LABELS[sku.evidence],
        source_url=str(sku.source_url) if sku.source_url else None,
    )


def format_release_date(release_date: str, lang: str) -> str:
    """Write a release date (2026-08-20, 2026-08, 2026-Q3 or 2026) readably in the language."""
    year, _, rest = release_date.partition("-")
    if rest.startswith("Q"):
        return RELEASE_DATE_TEMPLATES["quarter"][lang].format(quarter=rest[1:], year=year)
    if not rest:
        return RELEASE_DATE_TEMPLATES["year"][lang].format(year=year)
    month_number, _, day = rest.partition("-")
    month = MONTH_ABBREVIATIONS[lang][int(month_number) - 1]
    if not day:
        return RELEASE_DATE_TEMPLATES["month"][lang].format(month=month, year=year)
    return RELEASE_DATE_TEMPLATES["day"][lang].format(day=int(day), month=month, year=year)


def build_release_date_text(release_date: str | None) -> LocalizedText | None:
    """Build a title's release date in each language; None if unknown."""
    if release_date is None:
        return None
    return {lang: format_release_date(release_date, lang) for lang in LANGUAGES}


def build_search_text(title: Title, other_names: Sequence[str] = ()) -> str:
    """Text a title is searched by: name, publisher and other names it is known by (its editions
    and the games merged into it), without accents and lowercased, as in the JS."""
    names = dict.fromkeys(filter(None, [title.name, title.publisher, *other_names]))
    return strip_accents(" ".join(names)).lower()


def sku_sort_key(sku: Sku) -> tuple[str, str]:
    """Sort a title's SKUs by region and then by edition."""
    return (sku.region.value, sku.edition.value)


def group_skus_by_title(skus: list[Sku]) -> dict[str, list[Sku]]:
    """Group the SKUs by title_id, in the order they arrive."""
    groups: defaultdict[str, list[Sku]] = defaultdict(list)
    for sku in skus:
        groups[sku.title_id].append(sku)
    return dict(groups)


def build_no_box_view(release: PhysicalRelease) -> NoBoxView:
    """Translate into the view what was found about a game that never got a box."""
    note_key = "no_box_note" if release.source_url else "no_box_unconfirmed_note"
    return NoBoxView(
        note=UI_STRINGS[note_key],
        evidence_label=EVIDENCE_LABELS[release.evidence],
        source_url=str(release.source_url) if release.source_url else None,
    )


def find_digital_only_releases(releases: list[PhysicalRelease]) -> dict[str, PhysicalRelease]:
    """Index by title_id the researched games that got no boxed release in any region."""
    return {release.title_id: release for release in releases if not release.has_physical_release}


def group_merged_titles(excluded: Sequence[ExcludedTitle]) -> dict[str, list[ExcludedTitle]]:
    """Group merged games by their target title, to keep their anchors and names."""
    groups: defaultdict[str, list[ExcludedTitle]] = defaultdict(list)
    for entry in excluded:
        if entry.merged_into is not None and entry.former_title_id is not None:
            groups[entry.merged_into].append(entry)
    return dict(groups)


def build_title_view(
    title: Title,
    skus_by_title: dict[str, list[Sku]],
    diverging_title_ids: set[str],
    digital_only: dict[str, PhysicalRelease],
    merged_titles: dict[str, list[ExcludedTitle]],
) -> TitleView:
    """Build a title's view with its sorted SKUs, or with its "no boxed release" note."""
    title_skus = sorted(skus_by_title.get(title.title_id, []), key=sku_sort_key)
    release = digital_only.get(title.title_id)
    merged = merged_titles.get(title.title_id, [])
    other_names = [entry.name for entry in merged] + [
        sku.edition_name for sku in title_skus if sku.edition_name
    ]
    return TitleView(
        title_id=title.title_id,
        name=title.name,
        publisher=title.publisher,
        release_date_text=build_release_date_text(title.release_date),
        search_text=build_search_text(title, other_names),
        skus=[build_sku_view(sku) for sku in title_skus],
        has_divergence=title.title_id in diverging_title_ids,
        no_box=build_no_box_view(release) if release is not None and not title_skus else None,
        former_title_ids=sorted(str(entry.former_title_id) for entry in merged),
    )


def build_title_views(
    titles: list[Title],
    skus: list[Sku],
    releases: list[PhysicalRelease],
    excluded: Sequence[ExcludedTitle] = (),
) -> list[TitleView]:
    """Group the SKUs by title and return the views sorted by name, for every title. Of the excluded
    games only the merges are used, so their old anchors lead to the new title."""
    skus_by_title = group_skus_by_title(skus)
    diverging_title_ids = {title_id for title_id, _ in find_format_divergences(skus)}
    digital_only = find_digital_only_releases(releases)
    merged_titles = group_merged_titles(excluded)
    views = [
        build_title_view(title, skus_by_title, diverging_title_ids, digital_only, merged_titles)
        for title in titles
    ]
    return sorted(views, key=lambda view: view.name.casefold())


def build_footer_text(generated_at: str) -> LocalizedText:
    """Build the footer text with the generation date, in each language."""
    return {lang: text.format(date=generated_at) for lang, text in UI_STRINGS["footer"].items()}
