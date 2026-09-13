from pathlib import Path

from aws_lambda_powertools import Logger

from switch2db.data_store import load_title_seeds, write_titles
from switch2db.env import read_required_env
from switch2db.igdb_auth import get_access_token
from switch2db.igdb_client import fetch_games_by_ids
from switch2db.title_mapper import map_games_to_titles

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

logger = Logger(service="switch2db-import-titles")


def main() -> None:
    """Importa de IGDB los juegos de title_seeds.yaml y reescribe titles.yaml."""
    seeds, seed_errors = load_title_seeds(DATA_DIR / "title_seeds.yaml")
    if seed_errors:
        logger.error("title_seeds.yaml no es válido", extra={"errors": seed_errors})
        raise ValueError(f"title_seeds.yaml tiene {len(seed_errors)} errores; ejecuta scripts.validate_data")

    client_id = read_required_env("TWITCH_CLIENT_ID")
    access_token = get_access_token(client_id, read_required_env("TWITCH_CLIENT_SECRET"))
    games = fetch_games_by_ids([seed.igdb_id for seed in seeds], access_token, client_id)
    titles = map_games_to_titles(seeds, games)
    write_titles(DATA_DIR / "titles.yaml", titles)
    logger.info("titles.yaml actualizado", extra={"title_count": len(titles)})


if __name__ == "__main__":
    main()
