import requests

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
REQUEST_TIMEOUT_SECONDS = 10


def get_access_token(client_id: str, client_secret: str) -> str:
    """Request an IGDB app token from Twitch using client_credentials."""
    # Credentials go in the body, not the URL: an HTTPError's message includes the full URL.
    response = requests.post(
        TWITCH_TOKEN_URL,
        data={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["access_token"]
