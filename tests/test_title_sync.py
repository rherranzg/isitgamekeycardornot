from switch2db.models import Title, TitleSeed
from switch2db.title_sync import chunk_seeds, merge_titles, select_seeds_to_fetch


def make_seed(title_id: str, igdb_id: int) -> TitleSeed:
    """Semilla mínima para las pruebas."""
    return TitleSeed(title_id=title_id, igdb_id=igdb_id)


def make_title(title_id: str, igdb_id: int) -> Title:
    """Título mínimo para las pruebas."""
    return Title(title_id=title_id, igdb_id=igdb_id, name=title_id, publisher="Example Publisher")


def test_chunk_seeds_splits_into_blocks_of_size() -> None:
    seeds = [make_seed(f"game-{i}", i + 1) for i in range(5)]

    chunks = chunk_seeds(seeds, size=2)

    assert [len(chunk) for chunk in chunks] == [2, 2, 1]


def test_chunk_seeds_returns_empty_list_when_no_seeds() -> None:
    assert chunk_seeds([], size=2) == []


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


def test_merge_titles_adds_new_titles_in_seed_order() -> None:
    existing = [make_title("game-one", 1)]
    fetched = [make_title("game-two", 2)]

    merged = merge_titles(existing, fetched, seed_order=["game-two", "game-one"])

    assert [title.title_id for title in merged] == ["game-two", "game-one"]


def test_merge_titles_overwrites_refreshed_titles() -> None:
    existing = [make_title("game-one", 1)]
    refreshed = Title(title_id="game-one", igdb_id=1, name="Updated Name", publisher="New Publisher")

    merged = merge_titles(existing, [refreshed], seed_order=["game-one"])

    assert merged == [refreshed]


def test_merge_titles_drops_titles_no_longer_in_seed_order() -> None:
    existing = [make_title("game-one", 1), make_title("removed-game", 99)]

    merged = merge_titles(existing, [], seed_order=["game-one"])

    assert [title.title_id for title in merged] == ["game-one"]
