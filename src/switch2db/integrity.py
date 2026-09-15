from collections import Counter

from switch2db.models import Format, Sku, Title, TitleSeed, TitleStatus


def find_duplicates(values: list[str]) -> list[str]:
    """Devuelve, ordenados, los valores que aparecen más de una vez."""
    return sorted(value for value, count in Counter(values).items() if count > 1)


def find_id_duplication_errors(seeds: list[TitleSeed], skus: list[Sku]) -> list[str]:
    """Detecta title_id, igdb_id y sku_id repetidos."""
    errors = [
        f"title_seeds.yaml: title_id repetido '{title_id}'"
        for title_id in find_duplicates([seed.title_id for seed in seeds])
    ]
    errors += [
        f"title_seeds.yaml: igdb_id repetido {igdb_id}"
        for igdb_id in find_duplicates([str(seed.igdb_id) for seed in seeds])
    ]
    errors += [
        f"skus.yaml: sku_id repetido '{sku_id}'" for sku_id in find_duplicates([sku.sku_id for sku in skus])
    ]
    return errors


def find_orphan_sku_errors(seeds: list[TitleSeed], skus: list[Sku]) -> list[str]:
    """Detecta SKUs cuyo title_id no está declarado en las semillas."""
    known_title_ids = {seed.title_id for seed in seeds}
    return [
        f"skus.yaml: '{sku.sku_id}' referencia title_id '{sku.title_id}', que no está en title_seeds.yaml"
        for sku in skus
        if sku.title_id not in known_title_ids
    ]


def find_title_sync_errors(seeds: list[TitleSeed], titles: list[Title]) -> list[str]:
    """Detecta títulos importados que no están en las semillas o cuyo igdb_id no coincide."""
    igdb_ids_by_title = {seed.title_id: seed.igdb_id for seed in seeds}
    errors = []
    for title in titles:
        if title.title_id not in igdb_ids_by_title:
            errors.append(f"titles.yaml: '{title.title_id}' no está en title_seeds.yaml")
        elif title.igdb_id != igdb_ids_by_title[title.title_id]:
            errors.append(f"titles.yaml: '{title.title_id}' tiene un igdb_id distinto al de title_seeds.yaml")
    return errors


def find_unimported_seed_warnings(seeds: list[TitleSeed], titles: list[Title]) -> list[str]:
    """Avisa de las semillas que todavía no tienen título importado de IGDB."""
    imported_title_ids = {title.title_id for title in titles}
    return [
        f"title_seeds.yaml: '{seed.title_id}' aún no está importado de IGDB (scripts.import_titles)"
        for seed in seeds
        if seed.title_id not in imported_title_ids
    ]


def find_refresh_warnings(titles: list[Title]) -> list[str]:
    """Avisa de los títulos marcados con status refresh que aún no se han vuelto a importar."""
    return [
        f"titles.yaml: '{title.title_id}' está marcado para refrescar (scripts.import_titles)"
        for title in titles
        if title.status == TitleStatus.REFRESH
    ]


def find_cart_size_warnings(skus: list[Sku]) -> list[str]:
    """Avisa de los SKUs que indican cart_size_gb sin ser full_cart."""
    return [
        f"skus.yaml: '{sku.sku_id}' tiene cart_size_gb con format '{sku.format}'"
        for sku in skus
        if sku.cart_size_gb is not None and sku.format != Format.FULL_CART
    ]


def collect_integrity_errors(seeds: list[TitleSeed], titles: list[Title], skus: list[Sku]) -> list[str]:
    """Reúne los errores de integridad entre ficheros."""
    return [
        *find_id_duplication_errors(seeds, skus),
        *find_orphan_sku_errors(seeds, skus),
        *find_title_sync_errors(seeds, titles),
    ]


def collect_integrity_warnings(seeds: list[TitleSeed], titles: list[Title], skus: list[Sku]) -> list[str]:
    """Reúne los avisos que no invalidan los datos."""
    return [
        *find_unimported_seed_warnings(seeds, titles),
        *find_refresh_warnings(titles),
        *find_cart_size_warnings(skus),
    ]
