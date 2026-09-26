from collections import Counter
from collections.abc import Sequence

from switch2db.data_store import describe_row
from switch2db.models import ExcludedTitle, Format, PhysicalRelease, Sku, SkuStatus, Title, TitleStatus

# A title in these states has been researched: it must have left SKUs or a physical_release.yaml
# entry saying there is no box.
RESEARCHED_TITLE_STATUSES = {TitleStatus.PENDING, TitleStatus.REVIEWED}


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
    """Detect duplicate or unknown title_ids and digital-only games that have SKUs."""
    known_title_ids = {title.title_id for title in titles}
    title_ids_with_skus = {sku.title_id for sku in skus}
    errors = [
        f"physical_release.yaml: title_id repetido '{title_id}'"
        for title_id in find_duplicates([release.title_id for release in releases])
    ]
    errors += [
        f"physical_release.yaml: '{release.title_id}' is not in titles.yaml"
        for release in releases
        if release.title_id not in known_title_ids
    ]
    errors += [
        f"physical_release.yaml: '{release.title_id}' says there is no physical edition, but it has SKUs"
        for release in releases
        if not release.has_physical_release and release.title_id in title_ids_with_skus
    ]
    return errors


def find_missing_sku_warnings(releases: list[PhysicalRelease], skus: list[Sku]) -> list[str]:
    """Warn about games with a confirmed physical edition that have no SKU written yet."""
    title_ids_with_skus = {sku.title_id for sku in skus}
    return [
        f"physical_release.yaml: '{release.title_id}' has a physical edition but no SKU yet"
        for release in releases
        if release.has_physical_release and release.title_id not in title_ids_with_skus
    ]


def find_unresearched_title_warnings(
    titles: list[Title], skus: list[Sku], releases: list[PhysicalRelease]
) -> list[str]:
    """Warn about titles marked as researched that left neither SKUs nor a physical-release entry."""
    title_ids_with_skus = {sku.title_id for sku in skus}
    researched_title_ids = {release.title_id for release in releases}
    return [
        f"titles.yaml: '{title.title_id}' is {title.status} but has no SKU nor a physical_release.yaml entry"
        for title in titles
        if title.status in RESEARCHED_TITLE_STATUSES
        and title.title_id not in title_ids_with_skus
        and title.title_id not in researched_title_ids
    ]


def find_cart_size_warnings(skus: list[Sku]) -> list[str]:
    """Warn about SKUs that set cart_size_gb without being full_cart."""
    return [
        f"skus.yaml: '{sku.sku_id}' has cart_size_gb with format '{sku.format}'"
        for sku in skus
        if sku.cart_size_gb is not None and sku.format != Format.FULL_CART
    ]


def find_download_size_warnings(skus: list[Sku]) -> list[str]:
    """Warn about full_cart SKUs with download_size_gb: the game is on the cartridge, there is no download."""
    return [
        f"skus.yaml: '{sku.sku_id}' has download_size_gb with format '{sku.format}'"
        for sku in skus
        if sku.download_size_gb is not None and sku.format == Format.FULL_CART
    ]


def find_sku_status_warnings(skus: list[Sku]) -> list[str]:
    """Warn about SKUs awaiting work: not searched, searched without a source, and flagged for refresh."""
    new_counts = Counter(sku.title_id for sku in skus if sku.status == SkuStatus.NEW)
    pending_counts = Counter(sku.title_id for sku in skus if sku.status == SkuStatus.PENDING)
    refresh_counts = Counter(sku.title_id for sku in skus if sku.status == SkuStatus.REFRESH)
    warnings = [
        f"skus.yaml: '{title_id}' has {count} SKU(s) with status new, not shown on the site"
        for title_id, count in new_counts.items()
    ]
    warnings += [
        f"skus.yaml: '{title_id}' has {count} SKU(s) with no source found (status pending): "
        "shown as unknown format, they need a deeper search"
        for title_id, count in pending_counts.items()
    ]
    warnings += [
        f"skus.yaml: '{title_id}' has {count} SKU(s) flagged to be checked again (status refresh)"
        for title_id, count in refresh_counts.items()
    ]
    return warnings


def find_unpublished_sku_warnings(titles: list[Title], skus: list[Sku]) -> list[str]:
    """Warn about games with SKUs that are not on the site because their title is not reviewed."""
    reviewed_title_ids = {title.title_id for title in titles if title.status == TitleStatus.REVIEWED}
    unpublished_counts = Counter(sku.title_id for sku in skus if sku.title_id not in reviewed_title_ids)
    return [
        f"skus.yaml: '{title_id}' has {count} unpublished SKU(s) because its title is not reviewed"
        for title_id, count in unpublished_counts.items()
    ]


def list_omitted_optional_sku_fields(row: object) -> list[str]:
    """Return the optional Sku fields missing as keys from a raw YAML row."""
    if not isinstance(row, dict):
        return []
    return [
        field_name
        for field_name, field in Sku.model_fields.items()
        if not field.is_required() and field_name not in row
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
    ]


def collect_integrity_warnings(
    titles: list[Title],
    skus: list[Sku],
    releases: list[PhysicalRelease],
    sku_rows: Sequence[object],
) -> list[str]:
    """Collect the warnings that do not invalidate the data; sku_rows are the raw skus.yaml rows."""
    return [
        *find_unresearched_title_warnings(titles, skus, releases),
        *find_cart_size_warnings(skus),
        *find_download_size_warnings(skus),
        *find_unpublished_sku_warnings(titles, skus),
        *find_missing_sku_warnings(releases, skus),
        *find_sku_status_warnings(skus),
        *find_omitted_sku_field_warnings(sku_rows),
    ]
