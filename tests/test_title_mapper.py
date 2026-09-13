import pytest

from switch2db.igdb_models import IgdbGame
from switch2db.models import Title, TitleSeed
from switch2db.title_mapper import (
    extract_publisher,
    list_publishers,
    map_game_to_title,
    map_games_to_titles,
)


def test_list_publishers_success(igdb_game: IgdbGame) -> None:
    assert list_publishers(igdb_game) == ["Example Publisher"]


def test_list_publishers_returns_distinct_publishers_in_order(igdb_game_payload: dict[str, object]) -> None:
    game = IgdbGame.model_validate(
        {
            **igdb_game_payload,
            "involved_companies": [
                {"company": {"name": "Publisher A"}, "publisher": True},
                {"company": {"name": "Publisher B"}, "publisher": True},
                {"company": {"name": "Publisher A"}, "publisher": True},
            ],
        }
    )

    assert list_publishers(game) == ["Publisher A", "Publisher B"]


def test_list_publishers_returns_empty_list_without_publishers(igdb_game: IgdbGame) -> None:
    assert list_publishers(igdb_game.model_copy(update={"involved_companies": []})) == []


def test_extract_publisher_success(igdb_game: IgdbGame) -> None:
    assert extract_publisher(igdb_game) == "Example Publisher"


def test_extract_publisher_joins_distinct_publishers_in_order(igdb_game_payload: dict[str, object]) -> None:
    game = IgdbGame.model_validate(
        {
            **igdb_game_payload,
            "involved_companies": [
                {"company": {"name": "Publisher A"}, "publisher": True},
                {"company": {"name": "Publisher B"}, "publisher": True},
            ],
        }
    )

    assert extract_publisher(game) == "Publisher A / Publisher B"


def test_extract_publisher_raises_when_no_publisher_is_marked(igdb_game: IgdbGame) -> None:
    game = igdb_game.model_copy(update={"involved_companies": []})

    with pytest.raises(ValueError, match="no tiene ningún publisher"):
        extract_publisher(game)


def test_map_game_to_title_success(title_seed: TitleSeed, igdb_game: IgdbGame, title: Title) -> None:
    assert map_game_to_title(title_seed, igdb_game) == title


def test_map_games_to_titles_follows_seed_order(title_seed: TitleSeed, igdb_game: IgdbGame) -> None:
    other_seed = TitleSeed(title_id="other-game", igdb_id=67890)
    other_game = igdb_game.model_copy(update={"id": 67890, "name": "Other Game"})

    titles = map_games_to_titles([other_seed, title_seed], [igdb_game, other_game])

    assert [title.title_id for title in titles] == ["other-game", "example-game"]


def test_map_games_to_titles_raises_when_igdb_misses_an_id(title_seed: TitleSeed) -> None:
    with pytest.raises(ValueError, match=r"IGDB no devolvió los ids \[12345\]"):
        map_games_to_titles([title_seed], [])
