import time

import requests
from pydantic import TypeAdapter

from switch2db.igdb_models import IgdbGame, IgdbPlatform

IGDB_API_URL = "https://api.igdb.com/v4"
IGDB_GAMES_URL = f"{IGDB_API_URL}/games"
IGDB_PLATFORMS_URL = f"{IGDB_API_URL}/platforms"
IGDB_MAX_LIMIT = 500
REQUEST_TIMEOUT_SECONDS = 10
RATE_LIMIT_PAUSE_SECONDS = 0.25
GAME_FIELDS = (
    "name, first_release_date, game_type.type, involved_companies.company.name, involved_companies.publisher"
)
GAMES_ADAPTER = TypeAdapter(list[IgdbGame])
PLATFORMS_ADAPTER = TypeAdapter(list[IgdbPlatform])


def post_query(url: str, query: str, access_token: str, client_id: str) -> object:
    """Envía una query APICalypse a un endpoint de IGDB y devuelve el JSON de la respuesta."""
    response = requests.post(
        url,
        headers={"Client-ID": client_id, "Authorization": f"Bearer {access_token}"},
        data=query,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def build_games_query(igdb_ids: list[int]) -> str:
    """Construye la query APICalypse que pide los juegos con los ids indicados."""
    if not igdb_ids:
        raise ValueError("No hay igdb_ids que consultar")
    if len(igdb_ids) > IGDB_MAX_LIMIT:
        raise ValueError(f"IGDB admite como máximo {IGDB_MAX_LIMIT} resultados por petición")
    ids = ",".join(str(igdb_id) for igdb_id in igdb_ids)
    return f"fields {GAME_FIELDS}; where id = ({ids}); limit {len(igdb_ids)};"


def build_platform_query(name_fragment: str) -> str:
    """Construye la query que busca plataformas cuyo nombre contiene el texto."""
    return f'fields name; where name ~ *"{name_fragment}"*;'


def build_platform_games_query(platform_id: int, offset: int) -> str:
    """Construye la query de una página de juegos de una plataforma, ordenada por id."""
    return (
        f"fields {GAME_FIELDS}; where platforms = ({platform_id}); "
        f"sort id asc; limit {IGDB_MAX_LIMIT}; offset {offset};"
    )


def fetch_games_by_ids(igdb_ids: list[int], access_token: str, client_id: str) -> list[IgdbGame]:
    """Descarga de IGDB los juegos con los ids dados en una sola petición."""
    payload = post_query(IGDB_GAMES_URL, build_games_query(igdb_ids), access_token, client_id)
    return GAMES_ADAPTER.validate_python(payload)


def find_platform_id(name_fragment: str, access_token: str, client_id: str) -> int:
    """Busca la plataforma cuyo nombre contiene el texto; falla si IGDB no devuelve exactamente una."""
    payload = post_query(IGDB_PLATFORMS_URL, build_platform_query(name_fragment), access_token, client_id)
    platforms = PLATFORMS_ADAPTER.validate_python(payload)
    if len(platforms) != 1:
        names = [platform.name for platform in platforms]
        raise ValueError(f"Se esperaba 1 plataforma para '{name_fragment}' y IGDB devolvió {names}")
    return platforms[0].id


def fetch_platform_games(platform_id: int, access_token: str, client_id: str) -> list[IgdbGame]:
    """Descarga todos los juegos de una plataforma paginando hasta recibir una página incompleta."""
    games: list[IgdbGame] = []
    while True:
        query = build_platform_games_query(platform_id, offset=len(games))
        page = GAMES_ADAPTER.validate_python(post_query(IGDB_GAMES_URL, query, access_token, client_id))
        games.extend(page)
        if len(page) < IGDB_MAX_LIMIT:
            return games
        time.sleep(RATE_LIMIT_PAUSE_SECONDS)
