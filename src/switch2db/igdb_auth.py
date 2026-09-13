import requests

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
REQUEST_TIMEOUT_SECONDS = 10


def get_access_token(client_id: str, client_secret: str) -> str:
    """Pide a Twitch un token de aplicación para IGDB mediante client_credentials."""
    # Credenciales en el cuerpo, no en la URL: el mensaje de un HTTPError incluye la URL completa.
    response = requests.post(
        TWITCH_TOKEN_URL,
        data={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["access_token"]
