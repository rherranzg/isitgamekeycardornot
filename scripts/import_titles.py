import argparse
from pathlib import Path

from aws_lambda_powertools import Logger

from switch2db.data_store import load_title_seeds, load_titles, write_titles
from switch2db.env import read_required_env
from switch2db.igdb_auth import get_access_token
from switch2db.igdb_client import fetch_games_by_ids
from switch2db.models import Title, TitleSeed
from switch2db.title_mapper import map_games_to_titles
from switch2db.title_sync import chunk_seeds, find_title_ids_to_refresh, merge_titles, select_seeds_to_fetch

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

logger = Logger(service="switch2db-import-titles")


def parse_args() -> argparse.Namespace:
    """Define y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Importa de IGDB los metadatos de title_seeds.yaml y actualiza titles.yaml."
    )
    limit_group = parser.add_mutually_exclusive_group()
    limit_group.add_argument(
        "--count", type=int, help="Máximo de juegos pendientes a importar en esta ejecución"
    )
    limit_group.add_argument(
        "--all", action="store_true", help="Importa todos los juegos pendientes (comportamiento por defecto)"
    )
    refresh_group = parser.add_mutually_exclusive_group()
    refresh_group.add_argument(
        "--refresh",
        nargs="+",
        metavar="TITLE_ID",
        help="Vuelve a descargar estos juegos aunque ya estén al día",
    )
    refresh_group.add_argument(
        "--refresh-all", action="store_true", help="Vuelve a descargar todos los juegos de title_seeds.yaml"
    )
    args = parser.parse_args()
    if args.count is not None and args.count <= 0:
        parser.error("--count debe ser mayor que 0")
    return args


def load_valid_seeds(path: Path) -> list[TitleSeed]:
    """Carga title_seeds.yaml y falla si tiene errores de esquema o integridad."""
    seeds, errors = load_title_seeds(path)
    if errors:
        logger.error("title_seeds.yaml no es válido", extra={"errors": errors})
        raise ValueError(f"title_seeds.yaml tiene {len(errors)} errores; ejecuta scripts.validate_data")
    return seeds


def load_valid_titles(path: Path) -> list[Title]:
    """Carga titles.yaml y falla si tiene errores de esquema."""
    titles, errors = load_titles(path)
    if errors:
        logger.error("titles.yaml no es válido", extra={"errors": errors})
        raise ValueError(f"titles.yaml tiene {len(errors)} errores; ejecuta scripts.validate_data")
    return titles


def check_refresh_ids_exist(refresh_ids: set[str], seeds: list[TitleSeed]) -> None:
    """Falla si --refresh nombra un title_id que no está en title_seeds.yaml."""
    unknown = refresh_ids - {seed.title_id for seed in seeds}
    if unknown:
        raise ValueError(f"--refresh: title_id desconocido en title_seeds.yaml: {sorted(unknown)}")


def main() -> None:
    """Importa de IGDB los juegos pendientes o marcados para refrescar y actualiza titles.yaml."""
    args = parse_args()
    seeds_path = DATA_DIR / "title_seeds.yaml"
    titles_path = DATA_DIR / "titles.yaml"

    seeds = load_valid_seeds(seeds_path)
    existing_titles = load_valid_titles(titles_path)

    refresh_ids = set(args.refresh or [])
    check_refresh_ids_exist(refresh_ids, seeds)
    refresh_ids |= find_title_ids_to_refresh(existing_titles)

    limit = None if args.all else args.count
    to_fetch = select_seeds_to_fetch(
        seeds, {title.title_id for title in existing_titles}, refresh_ids, args.refresh_all, limit
    )
    if not to_fetch:
        logger.info("Nada que importar: todos los juegos ya están al día")
        return

    client_id = read_required_env("TWITCH_CLIENT_ID")
    access_token = get_access_token(client_id, read_required_env("TWITCH_CLIENT_SECRET"))

    seed_order = [seed.title_id for seed in seeds]
    imported = 0
    for batch in chunk_seeds(to_fetch):
        games = fetch_games_by_ids([seed.igdb_id for seed in batch], access_token, client_id)
        fetched = map_games_to_titles(batch, games)
        existing_titles = merge_titles(existing_titles, fetched, seed_order)
        write_titles(titles_path, existing_titles)
        imported += len(fetched)
        logger.info("Bloque importado", extra={"batch_size": len(fetched), "imported_so_far": imported})

    logger.info(
        "titles.yaml actualizado",
        extra={
            "imported": imported,
            "total": len(existing_titles),
            "not_imported": len(seeds) - len(existing_titles),
        },
    )


if __name__ == "__main__":
    main()
