import argparse
from datetime import date
from pathlib import Path

from aws_lambda_powertools import Logger

from switch2db.catalog import CatalogEntry
from switch2db.data_store import (
    load_excluded_titles,
    load_titles,
    read_yaml_rows,
    require_valid,
    write_titles,
)
from switch2db.paths import DATA_DIR
from switch2db.title_selection import refresh_release_dates, select_new_titles

logger = Logger(service="switch2db-add-titles")


def parse_args() -> argparse.Namespace:
    """Define y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Añade a titles.yaml juegos del catálogo local de IGDB, con status new, y refresca la "
        "fecha de salida de los que ya están."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--count", type=int, help="Número de juegos nuevos a añadir")
    group.add_argument("--all", action="store_true", help="Añade todos los juegos que queden del catálogo")
    group.add_argument(
        "--dates-only", action="store_true", help="No añade juegos: solo refresca las fechas de salida"
    )
    args = parser.parse_args()
    if args.count is not None and args.count <= 0:
        parser.error("--count debe ser mayor que 0")
    return args


def load_catalog(path: Path) -> list[CatalogEntry]:
    """Carga el catálogo local de IGDB descargado por download_igdb_catalog."""
    return [CatalogEntry.model_validate(row) for row in read_yaml_rows(path)]


def resolve_limit(args: argparse.Namespace) -> int | None:
    """Traduce los argumentos a cuántos títulos añadir: None son todos."""
    if args.dates_only:
        return 0
    if args.all:
        return None
    return args.count


def main() -> None:
    """Refresca las fechas de salida y añade títulos nuevos del catálogo local a titles.yaml. No consulta
    IGDB ni ninguna otra red."""
    args = parse_args()
    titles_path = DATA_DIR / "titles.yaml"
    catalog = load_catalog(DATA_DIR / "igdb_catalog.yaml")
    titles = require_valid(load_titles(titles_path), titles_path.name)
    excluded = require_valid(load_excluded_titles(DATA_DIR / "excluded_titles.yaml"), "excluded_titles.yaml")

    refreshed = refresh_release_dates(titles, catalog, date.today())
    changed_dates = sum(
        old.release_date != new.release_date for old, new in zip(titles, refreshed, strict=True)
    )
    new_titles = select_new_titles(catalog, refreshed, excluded, resolve_limit(args))
    write_titles(titles_path, refreshed + new_titles)
    logger.info(
        "titles.yaml actualizado",
        extra={
            "added": len(new_titles),
            "changed_release_dates": changed_dates,
            "total_titles": len(titles) + len(new_titles),
            "catalog_size": len(catalog),
            "excluded": len(excluded),
            "not_added_yet": len(catalog) - len(titles) - len(excluded) - len(new_titles),
        },
    )


if __name__ == "__main__":
    main()
