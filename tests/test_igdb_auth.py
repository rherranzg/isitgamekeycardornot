import pytest
import requests
from pytest_mock import MockerFixture

from switch2db.igdb_auth import REQUEST_TIMEOUT_SECONDS, TWITCH_TOKEN_URL, get_access_token


def test_get_access_token_success(mocker: MockerFixture) -> None:
    mock_post = mocker.patch("switch2db.igdb_auth.requests.post")
    mock_post.return_value.json.return_value = {
        "access_token": "token",
        "expires_in": 5184000,
        "token_type": "bearer",
    }

    assert get_access_token("client-id", "client-secret") == "token"
    mock_post.assert_called_once_with(
        TWITCH_TOKEN_URL,
        data={
            "client_id": "client-id",
            "client_secret": "client-secret",
            "grant_type": "client_credentials",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def test_get_access_token_raises_on_http_error(mocker: MockerFixture) -> None:
    mock_post = mocker.patch("switch2db.igdb_auth.requests.post")
    mock_post.return_value.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")

    with pytest.raises(requests.HTTPError):
        get_access_token("client-id", "wrong-secret")
