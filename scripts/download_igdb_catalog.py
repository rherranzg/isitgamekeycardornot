from aws_lambda_powertools import Logger

from switch2db.catalog import build_catalog
from switch2db.data_store import write_catalog
from switch2db.env import read_required_env
from switch2db.igdb_auth import get_access_token
from switch2db.igdb_client import fetch_platform_games, find_platform_id
from switch2db.paths import DATA_DIR

PLATFORM_NAME_FRAGMENT = "Switch 2"

logger = Logger(service="switch2db-download-igdb-catalog")


def main() -> None:
    """Descarga de IGDB todos los juegos de Switch 2 a data/igdb_catalog.yaml para elegir las semillas."""
    client_id = read_required_env("TWITCH_CLIENT_ID")
    access_token = get_access_token(client_id, read_required_env("TWITCH_CLIENT_SECRET"))
    platform_id = find_platform_id(PLATFORM_NAME_FRAGMENT, access_token, client_id)
    catalog = build_catalog(fetch_platform_games(platform_id, access_token, client_id), platform_id)
    write_catalog(DATA_DIR / "igdb_catalog.yaml", catalog)
    logger.info("Catálogo de IGDB descargado", extra={"platform_id": platform_id, "game_count": len(catalog)})


if __name__ == "__main__":
    main()
