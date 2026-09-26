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
    "name, game_type.type, version_parent, involved_companies.company.name, involved_companies.publisher, "
    "release_dates.platform, release_dates.date, release_dates.y, release_dates.m, "
    "release_dates.date_format.format"
)
GAMES_ADAPTER = TypeAdapter(list[IgdbGame])
PLATFORMS_ADAPTER = TypeAdapter(list[IgdbPlatform])


def post_query(url: str, query: str, access_token: str, client_id: str) -> object:
    """Send an APICalypse query to an IGDB endpoint and return the response JSON."""
    response = requests.post(
        url,
        headers={"Client-ID": client_id, "Authorization": f"Bearer {access_token}"},
        data=query,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def build_platform_query(name_fragment: str) -> str:
    """Build the query that searches for platforms whose name contains the text."""
    return f'fields name; where name ~ *"{name_fragment}"*;'


def build_platform_games_query(platform_id: int, offset: int) -> str:
    """Build the query for one page of a platform's games, sorted by id."""
    return (
        f"fields {GAME_FIELDS}; where platforms = ({platform_id}); "
        f"sort id asc; limit {IGDB_MAX_LIMIT}; offset {offset};"
    )


def find_platform_id(name_fragment: str, access_token: str, client_id: str) -> int:
    """Find the platform whose name contains the text; fail if IGDB does not return exactly one."""
    payload = post_query(IGDB_PLATFORMS_URL, build_platform_query(name_fragment), access_token, client_id)
    platforms = PLATFORMS_ADAPTER.validate_python(payload)
    if len(platforms) != 1:
        names = [platform.name for platform in platforms]
        raise ValueError(f"Expected 1 platform for '{name_fragment}' but IGDB returned {names}")
    return platforms[0].id


def fetch_platform_games(platform_id: int, access_token: str, client_id: str) -> list[IgdbGame]:
    """Download all games of a platform, paging until an incomplete page comes back."""
    games: list[IgdbGame] = []
    while True:
        query = build_platform_games_query(platform_id, offset=len(games))
        page = GAMES_ADAPTER.validate_python(post_query(IGDB_GAMES_URL, query, access_token, client_id))
        games.extend(page)
        if len(page) < IGDB_MAX_LIMIT:
            return games
        time.sleep(RATE_LIMIT_PAUSE_SECONDS)
