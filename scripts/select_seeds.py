import argparse
from datetime import UTC, datetime
from pathlib import Path

from aws_lambda_powertools import Logger

from switch2db.catalog import CatalogEntry
from switch2db.data_store import append_title_seeds, load_title_seeds, read_yaml_rows
from switch2db.seed_selection import select_new_seeds

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

logger = Logger(service="switch2db-select-seeds")


def parse_args() -> argparse.Namespace:
    """Define y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Añade a title_seeds.yaml juegos de Switch 2 del catálogo de IGDB sin semilla todavía."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--count", type=int, help="Número de juegos nuevos a añadir")
    group.add_argument("--all", action="store_true", help="Añade todos los juegos nuevos del catálogo")
    args = parser.parse_args()
    if args.count is not None and args.count <= 0:
        parser.error("--count debe ser mayor que 0")
    return args


def load_catalog(path: Path) -> list[CatalogEntry]:
    """Carga el catálogo local de IGDB descargado por download_igdb_catalog."""
    return [CatalogEntry.model_validate(row) for row in read_yaml_rows(path)]


def main() -> None:
    """Añade a title_seeds.yaml hasta N juegos del catálogo de IGDB que todavía no tengan semilla."""
    args = parse_args()
    seeds_path = DATA_DIR / "title_seeds.yaml"
    catalog = load_catalog(DATA_DIR / "igdb_catalog.yaml")
    seeds, seed_errors = load_title_seeds(seeds_path)
    if seed_errors:
        logger.error("title_seeds.yaml no es válido", extra={"errors": seed_errors})
        raise ValueError(f"title_seeds.yaml tiene {len(seed_errors)} errores; ejecuta scripts.validate_data")

    limit = None if args.all else args.count
    new_seeds = select_new_seeds(catalog, seeds, limit)
    today = datetime.now(UTC).date().isoformat()
    comment = f"Añadido automáticamente el {today} por scripts.select_seeds; igdb_id sin revisar a mano"
    append_title_seeds(seeds_path, new_seeds, comment)
    logger.info(
        "title_seeds.yaml actualizado",
        extra={
            "added": len(new_seeds),
            "total_seeds": len(seeds) + len(new_seeds),
            "catalog_size": len(catalog),
        },
    )


if __name__ == "__main__":
    main()
