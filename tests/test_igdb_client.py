import pytest
import requests
from pytest_mock import MockerFixture

from switch2db.igdb_client import (
    GAME_FIELDS,
    IGDB_GAMES_URL,
    IGDB_MAX_LIMIT,
    IGDB_PLATFORMS_URL,
    REQUEST_TIMEOUT_SECONDS,
    build_platform_games_query,
    build_platform_query,
    fetch_platform_games,
    find_platform_id,
    post_query,
)


def test_build_platform_query_success() -> None:
    assert build_platform_query("Switch 2") == 'fields name; where name ~ *"Switch 2"*;'


def test_build_platform_games_query_success() -> None:
    assert build_platform_games_query(99, 500) == (
        f"fields {GAME_FIELDS}; where platforms = (99); sort id asc; limit {IGDB_MAX_LIMIT}; offset 500;"
    )


def test_post_query_success(mocker: MockerFixture) -> None:
    mock_post = mocker.patch("switch2db.igdb_client.requests.post")
    mock_post.return_value.json.return_value = [{"id": 1}]

    result = post_query(IGDB_GAMES_URL, "fields name;", "token", "client-id")

    assert result == [{"id": 1}]
    mock_post.assert_called_once_with(
        IGDB_GAMES_URL,
        headers={"Client-ID": "client-id", "Authorization": "Bearer token"},
        data="fields name;",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def test_post_query_raises_on_http_error(mocker: MockerFixture) -> None:
    mock_post = mocker.patch("switch2db.igdb_client.requests.post")
    mock_post.return_value.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")

    with pytest.raises(requests.HTTPError):
        post_query(IGDB_GAMES_URL, "fields name;", "token", "client-id")


def test_find_platform_id_success(mocker: MockerFixture) -> None:
    mock_post_query = mocker.patch(
        "switch2db.igdb_client.post_query", return_value=[{"id": 99, "name": "Nintendo Switch 2"}]
    )

    assert find_platform_id("Switch 2", "token", "client-id") == 99
    mock_post_query.assert_called_once_with(
        IGDB_PLATFORMS_URL, build_platform_query("Switch 2"), "token", "client-id"
    )


@pytest.mark.parametrize(
    "platforms",
    [
        [],
        [{"id": 99, "name": "Nintendo Switch 2"}, {"id": 100, "name": "Switch 2 Dev Kit"}],
    ],
)
def test_find_platform_id_raises_when_not_exactly_one_match(
    mocker: MockerFixture, platforms: list[dict[str, object]]
) -> None:
    mocker.patch("switch2db.igdb_client.post_query", return_value=platforms)

    with pytest.raises(ValueError, match="Se esperaba 1 plataforma"):
        find_platform_id("Switch 2", "token", "client-id")


def test_fetch_platform_games_paginates_until_short_page(
    mocker: MockerFixture, igdb_game_payload: dict[str, object]
) -> None:
    mocker.patch("switch2db.igdb_client.IGDB_MAX_LIMIT", 2)
    mock_sleep = mocker.patch("switch2db.igdb_client.time.sleep")
    pages = [
        [{**igdb_game_payload, "id": 1}, {**igdb_game_payload, "id": 2}],
        [{**igdb_game_payload, "id": 3}],
    ]
    mock_post_query = mocker.patch("switch2db.igdb_client.post_query", side_effect=pages)

    games = fetch_platform_games(99, "token", "client-id")

    assert [game.id for game in games] == [1, 2, 3]
    assert mock_post_query.call_count == 2
    assert mock_post_query.call_args_list[1].args[1].endswith("offset 2;")
    mock_sleep.assert_called_once()


def test_fetch_platform_games_stops_after_single_short_page(
    mocker: MockerFixture, igdb_game_payload: dict[str, object]
) -> None:
    mock_sleep = mocker.patch("switch2db.igdb_client.time.sleep")
    mock_post_query = mocker.patch("switch2db.igdb_client.post_query", return_value=[igdb_game_payload])

    games = fetch_platform_games(99, "token", "client-id")

    assert len(games) == 1
    mock_post_query.assert_called_once()
    mock_sleep.assert_not_called()
