from collections import Counter
from collections.abc import Sequence
from datetime import date

from switch2db.data_store import describe_row
from switch2db.models import (
    DOWNLOAD_FORMATS,
    SKU_SOURCE_LIST_FIELDS,
    Edition,
    ExcludedTitle,
    Format,
    PhysicalRelease,
    Sku,
    Title,
    TitleStatus,
)
from switch2db.worklist import list_missing_regions

# Sku fields a completed title must have filled in every SKU; the ones that only apply to some SKUs
# (edition_name, download_size_gb) are checked apart. cart_size_gb, includes_download_code and ean are kept
# when known, but a title can be completed without them.
COMPLETED_SKU_FIELDS = ("distributor", "release_date")


def find_duplicates(values: list[str]) -> list[str]:
    """Return, sorted, the values that appear more than once."""
    return sorted(value for value, count in Counter(values).items() if count > 1)


def find_id_duplication_errors(titles: list[Title], skus: list[Sku]) -> list[str]:
    """Detect duplicate title_ids and igdb_ids in the titles and duplicate sku_ids in the SKUs."""
    errors = [
        f"titles.yaml: title_id repetido '{title_id}'"
        for title_id in find_duplicates([title.title_id for title in titles])
    ]
    errors += [
        f"titles.yaml: igdb_id repetido {igdb_id}"
        for igdb_id in find_duplicates([str(title.igdb_id) for title in titles])
    ]
    errors += [
        f"skus.yaml: sku_id repetido '{sku_id}'" for sku_id in find_duplicates([sku.sku_id for sku in skus])
    ]
    return errors


def find_orphan_sku_errors(titles: list[Title], skus: list[Sku]) -> list[str]:
    """Detect SKUs whose title_id is not in titles.yaml."""
    known_title_ids = {title.title_id for title in titles}
    return [
        f"skus.yaml: '{sku.sku_id}' references title_id '{sku.title_id}', which is not in titles.yaml"
        for sku in skus
        if sku.title_id not in known_title_ids
    ]


def find_excluded_title_errors(titles: list[Title], excluded: list[ExcludedTitle]) -> list[str]:
    """Detect duplicate igdb_ids in the exclusion list and excluded titles still in titles.yaml."""
    excluded_igdb_ids = {entry.igdb_id for entry in excluded}
    errors = [
        f"excluded_titles.yaml: igdb_id repetido {igdb_id}"
        for igdb_id in find_duplicates([str(entry.igdb_id) for entry in excluded])
    ]
    errors += [
        f"titles.yaml: '{title.title_id}' has igdb_id {title.igdb_id}, which is in excluded_titles.yaml"
        for title in titles
        if title.igdb_id in excluded_igdb_ids
    ]
    return errors + find_merged_title_errors(titles, excluded)


def find_merged_title_errors(titles: list[Title], excluded: list[ExcludedTitle]) -> list[str]:
    """Detect merges that cannot redirect: missing target or an old anchor still in use."""
    known_title_ids = {title.title_id for title in titles}
    merged = [entry for entry in excluded if entry.merged_into is not None]
    errors = [
        f"excluded_titles.yaml: {entry.igdb_id} goes to '{entry.merged_into}', which is not in titles.yaml"
        for entry in merged
        if entry.merged_into not in known_title_ids
    ]
    errors += [
        f"excluded_titles.yaml: former_title_id '{entry.former_title_id}' is still in titles.yaml"
        for entry in merged
        if entry.former_title_id in known_title_ids
    ]
    errors += [
        f"excluded_titles.yaml: former_title_id repetido '{former_title_id}'"
        for former_title_id in find_duplicates([str(entry.former_title_id) for entry in merged])
    ]
    return errors


def find_physical_release_errors(
    titles: list[Title], releases: list[PhysicalRelease], skus: list[Sku]
) -> list[str]:
    """Detect repeated entries, unknown title_ids, and no-box entries contradicted by a SKU or by the
    whole-game entry."""
    known_title_ids = {title.title_id for title in titles}
    title_ids_with_skus = {sku.title_id for sku in skus}
    sku_regions = {(sku.title_id, sku.region) for sku in skus}
    whole_game_title_ids = {release.title_id for release in releases if release.region is None}
    errors = [
        f"physical_release.yaml: entrada repetida '{key}'"
        for key in find_duplicates(
            [f"{release.title_id} {release.region or ''}".strip() for release in releases]
        )
    ]
    errors += [
        f"physical_release.yaml: '{release.title_id}' is not in titles.yaml"
        for release in releases
        if release.title_id not in known_title_ids
    ]
    errors += [
        f"physical_release.yaml: '{release.title_id}' says there is no physical edition, but it has SKUs"
        for release in releases
        if release.region is None
        and not release.has_physical_release
        and release.title_id in title_ids_with_skus
    ]
    errors += [
        f"physical_release.yaml: '{release.title_id}' says there is no box in {release.region}, "
        "but it has a SKU there"
        for release in releases
        if (release.title_id, release.region) in sku_regions
    ]
    errors += [
        f"physical_release.yaml: '{release.title_id}' has an entry for {release.region} "
        "and one for the whole game"
        for release in releases
        if release.region is not None and release.title_id in whole_game_title_ids
    ]
    return errors


def find_new_title_errors(titles: list[Title], skus: list[Sku], releases: list[PhysicalRelease]) -> list[str]:
    """Detect titles marked new that already have SKUs or physical_release entries: new means empty."""
    researched_title_ids = {sku.title_id for sku in skus} | {release.title_id for release in releases}
    return [
        f"titles.yaml: '{title.title_id}' is new but has SKUs or physical_release.yaml entries; use refresh"
        for title in titles
        if title.status == TitleStatus.NEW and title.title_id in researched_title_ids
    ]


def latest_check_dates(
    titles: list[Title], skus: list[Sku], releases: list[PhysicalRelease]
) -> dict[str, date]:
    """Latest date each title had a source checked: its own update dates, verified_at and update dates of
    its SKUs, and the checked_at of its physical_release entry."""
    latest: dict[str, date] = {}
    checks = [(title.title_id, update.checked_at) for title in titles for update in title.updates]
    checks += [(sku.title_id, sku.verified_at) for sku in skus]
    checks += [(sku.title_id, update.checked_at) for sku in skus for update in sku.updates]
    checks += [(release.title_id, release.checked_at) for release in releases]
    for title_id, checked_at in checks:
        latest[title_id] = max(checked_at, latest.get(title_id, checked_at))
    return latest


def find_last_checked_errors(
    titles: list[Title], skus: list[Sku], releases: list[PhysicalRelease]
) -> list[str]:
    """Detect researched titles whose last_checked_at is missing or older than a source checked for them."""
    latest = latest_check_dates(titles, skus, releases)
    errors = []
    for title in titles:
        checked_at = latest.get(title.title_id)
        if title.status == TitleStatus.NEW or checked_at is None:
            continue
        if title.last_checked_at is None:
            errors.append(
                f"titles.yaml: '{title.title_id}' has sources checked on {checked_at}, but no last_checked_at"
            )
        elif title.last_checked_day is not None and title.last_checked_day < checked_at:
            errors.append(
                f"titles.yaml: '{title.title_id}' last_checked_at {title.last_checked_at} is earlier than a "
                f"source checked on {checked_at}"
            )
    return errors


def list_missing_sku_data(sku: Sku) -> list[str]:
    """Return what a SKU still lacks to count as complete: its source, its format if unknown, and every
    field that applies to it but is null."""
    missing = ["source_url"] if sku.source_url is None else []
    if sku.format == Format.UNKNOWN:
        missing.append("format")
    missing += [field_name for field_name in COMPLETED_SKU_FIELDS if getattr(sku, field_name) is None]
    if sku.edition != Edition.STANDARD and sku.edition_name is None:
        missing.append("edition_name")
    if sku.format in DOWNLOAD_FORMATS and sku.download_size_gb is None:
        missing.append("download_size_gb")
    return missing


def list_completed_title_gaps(title_id: str, skus: list[Sku], releases: list[PhysicalRelease]) -> list[str]:
    """Return what keeps a title from being complete. A digital-only game is complete with its sourced
    physical_release entry; a boxed one needs every region answered (a SKU, or a sourced "no box in that
    region" entry) and every SKU complete."""
    whole_game = next(
        (release for release in releases if release.title_id == title_id and release.region is None), None
    )
    if whole_game is not None and not whole_game.has_physical_release:
        return [] if whole_game.source_url is not None else ["physical_release.yaml entry without source_url"]
    title_skus = [sku for sku in skus if sku.title_id == title_id]
    missing_regions = list_missing_regions(title_id, skus, releases)
    gaps = [f"no SKU nor sourced no-box entry in {', '.join(missing_regions)}"] if missing_regions else []
    for sku in title_skus:
        missing = list_missing_sku_data(sku)
        if missing:
            gaps.append(f"'{sku.sku_id}' lacks {', '.join(missing)}")
    return gaps


def find_completed_title_errors(
    titles: list[Title], skus: list[Sku], releases: list[PhysicalRelease]
) -> list[str]:
    """Detect titles marked completed that still lack a region, a SKU field or a sourced answer."""
    errors = []
    for title in titles:
        if title.status != TitleStatus.COMPLETED:
            continue
        gaps = list_completed_title_gaps(title.title_id, skus, releases)
        errors += [f"titles.yaml: '{title.title_id}' is completed but {gap}" for gap in gaps]
    return errors


def find_missing_sku_warnings(releases: list[PhysicalRelease], skus: list[Sku]) -> list[str]:
    """Warn about games with a confirmed physical edition that have no SKU written yet."""
    title_ids_with_skus = {sku.title_id for sku in skus}
    return [
        f"physical_release.yaml: '{release.title_id}' has a physical edition but no SKU yet"
        for release in releases
        if release.has_physical_release and release.title_id not in title_ids_with_skus
    ]


def find_cart_size_warnings(skus: list[Sku]) -> list[str]:
    """Warn about SKUs that set cart_size_gb without being full_cart."""
    return [
        f"skus.yaml: '{sku.sku_id}' has cart_size_gb with format '{sku.format}'"
        for sku in skus
        if sku.cart_size_gb is not None and sku.format != Format.FULL_CART
    ]


def find_download_size_warnings(skus: list[Sku]) -> list[str]:
    """Warn about download_size_gb on a SKU whose box is not a game-key card or code in box.

    A full_cart needs no download; on an unknown format the eShop size is the digital one's, not the box's.
    """
    return [
        f"skus.yaml: '{sku.sku_id}' has download_size_gb with format '{sku.format}'"
        for sku in skus
        if sku.download_size_gb is not None and sku.format not in DOWNLOAD_FORMATS
    ]


def find_sourceless_sku_warnings(skus: list[Sku]) -> list[str]:
    """Warn about SKUs searched without finding a source: they need a deeper search."""
    counts = Counter(sku.title_id for sku in skus if sku.source_url is None)
    return [
        f"skus.yaml: '{title_id}' has {count} SKU(s) with no source: shown as unknown format, "
        "they need a deeper search"
        for title_id, count in counts.items()
    ]


def list_omitted_optional_sku_fields(row: object) -> list[str]:
    """Return the optional Sku fields missing as keys from a raw YAML row."""
    if not isinstance(row, dict):
        return []
    return [
        field_name
        for field_name, field in Sku.model_fields.items()
        if not field.is_required() and field_name not in row and field_name not in SKU_SOURCE_LIST_FIELDS
    ]


def find_omitted_sku_field_warnings(sku_rows: Sequence[object]) -> list[str]:
    """Warn about skus.yaml rows that omit an optional field instead of writing it as null."""
    warnings = []
    for index, row in enumerate(sku_rows):
        omitted = list_omitted_optional_sku_fields(row)
        if omitted:
            warnings.append(f"skus.yaml {describe_row(row, index)}: missing keys {omitted} (null if unknown)")
    return warnings


def collect_integrity_errors(
    titles: list[Title],
    skus: list[Sku],
    releases: list[PhysicalRelease],
    excluded: list[ExcludedTitle],
) -> list[str]:
    """Collect the cross-file integrity errors."""
    return [
        *find_id_duplication_errors(titles, skus),
        *find_excluded_title_errors(titles, excluded),
        *find_orphan_sku_errors(titles, skus),
        *find_physical_release_errors(titles, releases, skus),
        *find_new_title_errors(titles, skus, releases),
        *find_last_checked_errors(titles, skus, releases),
        *find_completed_title_errors(titles, skus, releases),
    ]


def collect_integrity_warnings(
    titles: list[Title],
    skus: list[Sku],
    releases: list[PhysicalRelease],
    sku_rows: Sequence[object],
) -> list[str]:
    """Collect the warnings that do not invalidate the data; sku_rows are the raw skus.yaml rows."""
    return [
        *find_cart_size_warnings(skus),
        *find_download_size_warnings(skus),
        *find_missing_sku_warnings(releases, skus),
        *find_sourceless_sku_warnings(skus),
        *find_omitted_sku_field_warnings(sku_rows),
    ]
