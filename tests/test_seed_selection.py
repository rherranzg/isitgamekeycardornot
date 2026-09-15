from switch2db.catalog import CatalogEntry
from switch2db.models import TitleSeed
from switch2db.seed_selection import is_seedable, normalize_game_type, select_new_seeds


def make_entry(igdb_id: int, name: str, game_type: str | None = "Main Game") -> CatalogEntry:
    """Construye una entrada de catálogo mínima para las pruebas."""
    return CatalogEntry(igdb_id=igdb_id, name=name, game_type=game_type)


def test_normalize_game_type_ignores_case_and_punctuation() -> None:
    assert normalize_game_type("DLC / Add-on") == normalize_game_type("dlc_addon")


def test_is_seedable_true_when_game_type_is_missing() -> None:
    assert is_seedable(make_entry(1, "Example Game", game_type=None))


def test_is_seedable_true_for_main_game() -> None:
    assert is_seedable(make_entry(1, "Example Game", game_type="Main Game"))


def test_is_seedable_false_for_excluded_game_types() -> None:
    assert not is_seedable(make_entry(1, "Example Game DLC", game_type="DLC / Add-on"))
    assert not is_seedable(make_entry(2, "Example Season", game_type="Season"))


def test_select_new_seeds_skips_already_seeded_igdb_ids() -> None:
    catalog = [make_entry(1, "Game One"), make_entry(2, "Game Two")]
    existing = [TitleSeed(title_id="game-one", igdb_id=1)]

    new_seeds = select_new_seeds(catalog, existing, limit=None)

    assert [seed.igdb_id for seed in new_seeds] == [2]
    assert new_seeds[0].title_id == "game-two"


def test_select_new_seeds_skips_excluded_game_types() -> None:
    catalog = [make_entry(1, "Game DLC", game_type="DLC / Add-on"), make_entry(2, "Game Two")]

    new_seeds = select_new_seeds(catalog, [], limit=None)

    assert [seed.igdb_id for seed in new_seeds] == [2]


def test_select_new_seeds_respects_limit_and_catalog_order() -> None:
    catalog = [make_entry(1, "Game One"), make_entry(2, "Game Two"), make_entry(3, "Game Three")]

    new_seeds = select_new_seeds(catalog, [], limit=2)

    assert [seed.igdb_id for seed in new_seeds] == [1, 2]


def test_select_new_seeds_avoids_title_id_collisions() -> None:
    catalog = [make_entry(1, "Example Game"), make_entry(2, "Example Game")]

    new_seeds = select_new_seeds(catalog, [], limit=None)

    assert [seed.title_id for seed in new_seeds] == ["example-game", "example-game-2"]
