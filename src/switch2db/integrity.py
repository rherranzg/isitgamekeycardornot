from collections import Counter
from collections.abc import Sequence

from switch2db.data_store import describe_row
from switch2db.models import ExcludedTitle, Format, PhysicalRelease, Sku, SkuStatus, Title, TitleStatus

# Un título en estos estados ya se ha investigado: tiene que haber dejado SKUs o una entrada
# en physical_release.yaml diciendo que no hay caja.
RESEARCHED_TITLE_STATUSES = {TitleStatus.PENDING, TitleStatus.REVIEWED}


def find_duplicates(values: list[str]) -> list[str]:
    """Devuelve, ordenados, los valores que aparecen más de una vez."""
    return sorted(value for value, count in Counter(values).items() if count > 1)


def find_id_duplication_errors(titles: list[Title], skus: list[Sku]) -> list[str]:
    """Detecta title_id e igdb_id repetidos en los títulos y sku_id repetidos en los SKUs."""
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
    """Detecta SKUs cuyo title_id no está en titles.yaml."""
    known_title_ids = {title.title_id for title in titles}
    return [
        f"skus.yaml: '{sku.sku_id}' referencia title_id '{sku.title_id}', que no está en titles.yaml"
        for sku in skus
        if sku.title_id not in known_title_ids
    ]


def find_excluded_title_errors(titles: list[Title], excluded: list[ExcludedTitle]) -> list[str]:
    """Detecta igdb_id repetidos en la lista de excluidos y títulos excluidos que siguen en titles.yaml."""
    excluded_igdb_ids = {entry.igdb_id for entry in excluded}
    errors = [
        f"excluded_titles.yaml: igdb_id repetido {igdb_id}"
        for igdb_id in find_duplicates([str(entry.igdb_id) for entry in excluded])
    ]
    errors += [
        f"titles.yaml: '{title.title_id}' tiene el igdb_id {title.igdb_id}, que está en excluded_titles.yaml"
        for title in titles
        if title.igdb_id in excluded_igdb_ids
    ]
    return errors + find_merged_title_errors(titles, excluded)


def find_merged_title_errors(titles: list[Title], excluded: list[ExcludedTitle]) -> list[str]:
    """Detecta fusiones que no se pueden redirigir: destino que no existe o ancla vieja que sigue en uso."""
    known_title_ids = {title.title_id for title in titles}
    merged = [entry for entry in excluded if entry.merged_into is not None]
    errors = [
        f"excluded_titles.yaml: {entry.igdb_id} va a '{entry.merged_into}', que no está en titles.yaml"
        for entry in merged
        if entry.merged_into not in known_title_ids
    ]
    errors += [
        f"excluded_titles.yaml: el former_title_id '{entry.former_title_id}' sigue en titles.yaml"
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
    """Detecta title_id repetidos o desconocidos y juegos marcados solo digital que tienen SKUs."""
    known_title_ids = {title.title_id for title in titles}
    title_ids_with_skus = {sku.title_id for sku in skus}
    errors = [
        f"physical_release.yaml: title_id repetido '{title_id}'"
        for title_id in find_duplicates([release.title_id for release in releases])
    ]
    errors += [
        f"physical_release.yaml: '{release.title_id}' no está en titles.yaml"
        for release in releases
        if release.title_id not in known_title_ids
    ]
    errors += [
        f"physical_release.yaml: '{release.title_id}' dice que no hay edición física, pero tiene SKUs"
        for release in releases
        if not release.has_physical_release and release.title_id in title_ids_with_skus
    ]
    return errors


def find_missing_sku_warnings(releases: list[PhysicalRelease], skus: list[Sku]) -> list[str]:
    """Avisa de los juegos con edición física confirmada a los que aún no se les ha escrito ningún SKU."""
    title_ids_with_skus = {sku.title_id for sku in skus}
    return [
        f"physical_release.yaml: '{release.title_id}' tiene edición física y todavía no tiene ningún SKU"
        for release in releases
        if release.has_physical_release and release.title_id not in title_ids_with_skus
    ]


def find_unresearched_title_warnings(
    titles: list[Title], skus: list[Sku], releases: list[PhysicalRelease]
) -> list[str]:
    """Avisa de los títulos que dicen estar investigados pero no dejaron ni SKUs ni edición física."""
    title_ids_with_skus = {sku.title_id for sku in skus}
    researched_title_ids = {release.title_id for release in releases}
    return [
        f"titles.yaml: '{title.title_id}' está {title.status} pero no tiene ningún SKU "
        "ni entrada en physical_release.yaml"
        for title in titles
        if title.status in RESEARCHED_TITLE_STATUSES
        and title.title_id not in title_ids_with_skus
        and title.title_id not in researched_title_ids
    ]


def find_cart_size_warnings(skus: list[Sku]) -> list[str]:
    """Avisa de los SKUs que indican cart_size_gb sin ser full_cart."""
    return [
        f"skus.yaml: '{sku.sku_id}' tiene cart_size_gb con format '{sku.format}'"
        for sku in skus
        if sku.cart_size_gb is not None and sku.format != Format.FULL_CART
    ]


def find_download_size_warnings(skus: list[Sku]) -> list[str]:
    """Avisa de los SKUs full_cart con download_size_gb: el juego va en el cartucho y no hay descarga."""
    return [
        f"skus.yaml: '{sku.sku_id}' tiene download_size_gb con format '{sku.format}'"
        for sku in skus
        if sku.download_size_gb is not None and sku.format == Format.FULL_CART
    ]


def find_sku_status_warnings(skus: list[Sku]) -> list[str]:
    """Avisa de los SKUs que esperan trabajo: sin buscar, buscados sin fuente y marcados para refrescar."""
    new_counts = Counter(sku.title_id for sku in skus if sku.status == SkuStatus.NEW)
    pending_counts = Counter(sku.title_id for sku in skus if sku.status == SkuStatus.PENDING)
    refresh_counts = Counter(sku.title_id for sku in skus if sku.status == SkuStatus.REFRESH)
    warnings = [
        f"skus.yaml: '{title_id}' tiene {count} SKU(s) con status new, que no salen en la web"
        for title_id, count in new_counts.items()
    ]
    warnings += [
        f"skus.yaml: '{title_id}' tiene {count} SKU(s) sin fuente encontrada (status pending): "
        "salen como formato desconocido y hay que buscarlos a fondo"
        for title_id, count in pending_counts.items()
    ]
    warnings += [
        f"skus.yaml: '{title_id}' tiene {count} SKU(s) marcados para volver a comprobar (status refresh)"
        for title_id, count in refresh_counts.items()
    ]
    return warnings


def find_unpublished_sku_warnings(titles: list[Title], skus: list[Sku]) -> list[str]:
    """Avisa de los juegos con SKUs que no salen en la web porque su título no está reviewed."""
    reviewed_title_ids = {title.title_id for title in titles if title.status == TitleStatus.REVIEWED}
    unpublished_counts = Counter(sku.title_id for sku in skus if sku.title_id not in reviewed_title_ids)
    return [
        f"skus.yaml: '{title_id}' tiene {count} SKU(s) sin publicar porque su título no está reviewed"
        for title_id, count in unpublished_counts.items()
    ]


def list_omitted_optional_sku_fields(row: object) -> list[str]:
    """Devuelve los campos opcionales de Sku que no aparecen como clave en una fila cruda del YAML."""
    if not isinstance(row, dict):
        return []
    return [
        field_name
        for field_name, field in Sku.model_fields.items()
        if not field.is_required() and field_name not in row
    ]


def find_omitted_sku_field_warnings(sku_rows: Sequence[object]) -> list[str]:
    """Avisa de las filas de skus.yaml que omiten un campo opcional en vez de escribirlo como null."""
    warnings = []
    for index, row in enumerate(sku_rows):
        omitted = list_omitted_optional_sku_fields(row)
        if omitted:
            warnings.append(
                f"skus.yaml {describe_row(row, index)}: faltan las claves {omitted} (null si no se sabe)"
            )
    return warnings


def collect_integrity_errors(
    titles: list[Title],
    skus: list[Sku],
    releases: list[PhysicalRelease],
    excluded: list[ExcludedTitle],
) -> list[str]:
    """Reúne los errores de integridad entre ficheros."""
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
    """Reúne los avisos que no invalidan los datos; sku_rows son las filas crudas de skus.yaml."""
    return [
        *find_unresearched_title_warnings(titles, skus, releases),
        *find_cart_size_warnings(skus),
        *find_download_size_warnings(skus),
        *find_unpublished_sku_warnings(titles, skus),
        *find_missing_sku_warnings(releases, skus),
        *find_sku_status_warnings(skus),
        *find_omitted_sku_field_warnings(sku_rows),
    ]
