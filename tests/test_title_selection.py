from switch2db.catalog import CatalogEntry
from switch2db.models import Title, TitleStatus
from switch2db.title_selection import build_new_title, select_new_titles


def build_entry(igdb_id: int, name: str, publishers: str | None = "Example Publisher") -> CatalogEntry:
    """Entrada del catálogo de IGDB lista para convertirse en título."""
    return CatalogEntry(
        igdb_id=igdb_id, name=name, game_type="Main Game", first_release_date=None, publishers=publishers
    )


def test_build_new_title_slugifies_the_name_and_leaves_it_without_investigar() -> None:
    title = build_new_title(build_entry(1, "Metroid Prime 4: Beyond"), set())

    assert title.title_id == "metroid-prime-4-beyond"
    assert title.status == TitleStatus.NEW
    assert title.publisher == "Example Publisher"


def test_build_new_title_keeps_publisher_null_when_igdb_has_none() -> None:
    assert build_new_title(build_entry(1, "Bare Game", publishers=None), set()).publisher is None


def test_build_new_title_adds_a_suffix_when_the_slug_is_taken() -> None:
    assert build_new_title(build_entry(1, "Example Game"), {"example-game"}).title_id == "example-game-2"


def test_select_new_titles_skips_igdb_ids_already_in_titles(title: Title) -> None:
    catalog = [build_entry(12345, "Example Game"), build_entry(67890, "Other Game")]

    new_titles = select_new_titles(catalog, [title], None)

    assert [new.igdb_id for new in new_titles] == [67890]


def test_select_new_titles_respects_the_limit_in_catalog_order() -> None:
    catalog = [build_entry(1, "Alpha"), build_entry(2, "Beta"), build_entry(3, "Gamma")]

    assert [new.name for new in select_new_titles(catalog, [], 2)] == ["Alpha", "Beta"]


def test_select_new_titles_adds_nothing_when_the_limit_is_zero() -> None:
    assert select_new_titles([build_entry(1, "Alpha")], [], 0) == []


def test_select_new_titles_does_not_repeat_slugs_between_new_titles() -> None:
    catalog = [build_entry(1, "Example Game"), build_entry(2, "Example Game")]

    assert [new.title_id for new in select_new_titles(catalog, [], None)] == [
        "example-game",
        "example-game-2",
    ]
