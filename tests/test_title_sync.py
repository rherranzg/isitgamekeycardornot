import pytest

from switch2db.models import Title, TitleSeed, TitleStatus
from switch2db.title_sync import (
    chunk_seeds,
    find_title_ids_to_refresh,
    has_same_igdb_data,
    merge_titles,
    resolve_fetched_title,
    select_seeds_to_fetch,
)


def make_seed(title_id: str, igdb_id: int) -> TitleSeed:
    """Semilla mínima para las pruebas."""
    return TitleSeed(title_id=title_id, igdb_id=igdb_id)


def make_title(title_id: str, igdb_id: int, status: TitleStatus = TitleStatus.PENDING) -> Title:
    """Título mínimo para las pruebas."""
    return Title(
        title_id=title_id, igdb_id=igdb_id, name=title_id, publisher="Example Publisher", status=status
    )


def test_chunk_seeds_splits_into_blocks_of_size() -> None:
    seeds = [make_seed(f"game-{i}", i + 1) for i in range(5)]

    chunks = chunk_seeds(seeds, size=2)

    assert [len(chunk) for chunk in chunks] == [2, 2, 1]


def test_chunk_seeds_returns_empty_list_when_no_seeds() -> None:
    assert chunk_seeds([], size=2) == []


def test_find_title_ids_to_refresh_success() -> None:
    titles = [
        make_title("game-one", 1, TitleStatus.REFRESH),
        make_title("game-two", 2, TitleStatus.REVIEWED),
        make_title("game-three", 3),
    ]

    assert find_title_ids_to_refresh(titles) == {"game-one"}


def test_find_title_ids_to_refresh_returns_empty_set_when_none_is_marked() -> None:
    assert find_title_ids_to_refresh([make_title("game-one", 1)]) == set()


def test_select_seeds_to_fetch_skips_already_imported() -> None:
    seeds = [make_seed("game-one", 1), make_seed("game-two", 2)]

    pending = select_seeds_to_fetch(seeds, {"game-one"}, refresh_ids=set(), refresh_all=False, limit=None)

    assert [seed.title_id for seed in pending] == ["game-two"]


def test_select_seeds_to_fetch_includes_refresh_ids_even_if_imported() -> None:
    seeds = [make_seed("game-one", 1), make_seed("game-two", 2)]

    pending = select_seeds_to_fetch(
        seeds, {"game-one", "game-two"}, refresh_ids={"game-one"}, refresh_all=False, limit=None
    )

    assert [seed.title_id for seed in pending] == ["game-one"]


def test_select_seeds_to_fetch_refresh_all_ignores_existing() -> None:
    seeds = [make_seed("game-one", 1), make_seed("game-two", 2)]

    pending = select_seeds_to_fetch(
        seeds, {"game-one", "game-two"}, refresh_ids=set(), refresh_all=True, limit=None
    )

    assert [seed.title_id for seed in pending] == ["game-one", "game-two"]


def test_select_seeds_to_fetch_respects_limit() -> None:
    seeds = [make_seed("game-one", 1), make_seed("game-two", 2)]

    pending = select_seeds_to_fetch(seeds, set(), refresh_ids=set(), refresh_all=False, limit=1)

    assert [seed.title_id for seed in pending] == ["game-one"]


def test_has_same_igdb_data_ignores_status() -> None:
    assert has_same_igdb_data(make_title("game-one", 1, TitleStatus.REVIEWED), make_title("game-one", 1))


@pytest.mark.parametrize("changes", [{"name": "Updated Name"}, {"publisher": "New Publisher"}])
def test_has_same_igdb_data_detects_changed_field(changes: dict[str, object]) -> None:
    fetched = make_title("game-one", 1).model_copy(update=changes)

    assert not has_same_igdb_data(make_title("game-one", 1, TitleStatus.REVIEWED), fetched)


@pytest.mark.parametrize("existing_status", [None, TitleStatus.PENDING, TitleStatus.REFRESH])
def test_resolve_fetched_title_returns_fetched_when_title_was_not_reviewed(
    existing_status: TitleStatus | None,
) -> None:
    existing = None if existing_status is None else make_title("game-one", 1, existing_status)
    fetched = make_title("game-one", 1)

    assert resolve_fetched_title(existing, fetched) is fetched


def test_resolve_fetched_title_keeps_reviewed_title_when_igdb_data_is_unchanged() -> None:
    existing = make_title("game-one", 1, TitleStatus.REVIEWED)

    assert resolve_fetched_title(existing, make_title("game-one", 1)) is existing


def test_resolve_fetched_title_returns_pending_title_when_reviewed_data_changed() -> None:
    fetched = make_title("game-one", 1).model_copy(update={"publisher": "New Publisher"})

    resolved = resolve_fetched_title(make_title("game-one", 1, TitleStatus.REVIEWED), fetched)

    assert resolved is fetched
    assert resolved.status == TitleStatus.PENDING


def test_merge_titles_adds_new_titles_in_seed_order() -> None:
    existing = [make_title("game-one", 1)]
    fetched = [make_title("game-two", 2)]

    merged = merge_titles(existing, fetched, seed_order=["game-two", "game-one"])

    assert [title.title_id for title in merged] == ["game-two", "game-one"]


def test_merge_titles_overwrites_refreshed_titles() -> None:
    existing = [make_title("game-one", 1, TitleStatus.REFRESH)]
    refreshed = make_title("game-one", 1).model_copy(update={"name": "Updated Name"})

    merged = merge_titles(existing, [refreshed], seed_order=["game-one"])

    assert merged == [refreshed]


def test_merge_titles_keeps_reviewed_titles_that_did_not_change() -> None:
    reviewed = make_title("game-one", 1, TitleStatus.REVIEWED)

    merged = merge_titles([reviewed], [make_title("game-one", 1)], seed_order=["game-one"])

    assert merged == [reviewed]


def test_merge_titles_drops_titles_no_longer_in_seed_order() -> None:
    existing = [make_title("game-one", 1), make_title("removed-game", 99)]

    merged = merge_titles(existing, [], seed_order=["game-one"])

    assert [title.title_id for title in merged] == ["game-one"]
