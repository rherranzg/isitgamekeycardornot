import pytest

from switch2db.integrity import (
    collect_integrity_errors,
    collect_integrity_warnings,
    find_cart_size_warnings,
    find_duplicates,
    find_id_duplication_errors,
    find_orphan_sku_errors,
    find_title_sync_errors,
    find_unimported_seed_warnings,
)
from switch2db.models import Sku, Title, TitleSeed


@pytest.mark.parametrize(
    "values,expected",
    [
        (["b", "a", "b", "a"], ["a", "b"]),
        (["a", "b"], []),
        ([], []),
    ],
)
def test_find_duplicates_success(values: list[str], expected: list[str]) -> None:
    assert find_duplicates(values) == expected


def test_find_id_duplication_errors_reports_every_duplicated_id(
    title_seed: TitleSeed, eu_key_card_sku: Sku
) -> None:
    errors = find_id_duplication_errors([title_seed, title_seed], [eu_key_card_sku, eu_key_card_sku])

    assert errors == [
        "title_seeds.yaml: title_id repetido 'example-game'",
        "title_seeds.yaml: igdb_id repetido 12345",
        "skus.yaml: sku_id repetido 'eu-example-game-standard'",
    ]


def test_find_id_duplication_errors_returns_empty_list_when_ids_are_unique(
    title_seed: TitleSeed, eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    assert find_id_duplication_errors([title_seed], [eu_key_card_sku, asia_full_cart_sku]) == []


def test_find_orphan_sku_errors_reports_unknown_title_id(eu_key_card_sku: Sku) -> None:
    errors = find_orphan_sku_errors([], [eu_key_card_sku])

    assert len(errors) == 1
    assert "'eu-example-game-standard' referencia title_id 'example-game'" in errors[0]


def test_find_orphan_sku_errors_returns_empty_list_when_title_is_seeded(
    title_seed: TitleSeed, eu_key_card_sku: Sku
) -> None:
    assert find_orphan_sku_errors([title_seed], [eu_key_card_sku]) == []


def test_find_title_sync_errors_reports_title_missing_from_seeds(title: Title) -> None:
    assert find_title_sync_errors([], [title]) == ["titles.yaml: 'example-game' no está en title_seeds.yaml"]


def test_find_title_sync_errors_reports_igdb_id_mismatch(title_seed: TitleSeed, title: Title) -> None:
    errors = find_title_sync_errors([title_seed], [title.model_copy(update={"igdb_id": 99})])

    assert len(errors) == 1
    assert "igdb_id distinto" in errors[0]


def test_find_title_sync_errors_returns_empty_list_when_in_sync(title_seed: TitleSeed, title: Title) -> None:
    assert find_title_sync_errors([title_seed], [title]) == []


def test_find_unimported_seed_warnings_reports_seed_without_title(title_seed: TitleSeed) -> None:
    warnings = find_unimported_seed_warnings([title_seed], [])

    assert len(warnings) == 1
    assert "'example-game' aún no está importado" in warnings[0]


def test_find_unimported_seed_warnings_returns_empty_list_when_imported(
    title_seed: TitleSeed, title: Title
) -> None:
    assert find_unimported_seed_warnings([title_seed], [title]) == []


def test_find_cart_size_warnings_reports_cart_size_on_non_full_cart(eu_key_card_sku: Sku) -> None:
    sku = eu_key_card_sku.model_copy(update={"cart_size_gb": 16})

    assert find_cart_size_warnings([sku]) == [
        "skus.yaml: 'eu-example-game-standard' tiene cart_size_gb con format 'game_key_card'"
    ]


def test_find_cart_size_warnings_returns_empty_list_for_full_cart(asia_full_cart_sku: Sku) -> None:
    assert find_cart_size_warnings([asia_full_cart_sku]) == []


def test_collect_integrity_errors_returns_empty_list_for_consistent_data(
    title_seed: TitleSeed, title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    assert collect_integrity_errors([title_seed], [title], [eu_key_card_sku, asia_full_cart_sku]) == []


def test_collect_integrity_errors_combines_every_check(title: Title, eu_key_card_sku: Sku) -> None:
    errors = collect_integrity_errors([], [title], [eu_key_card_sku, eu_key_card_sku])

    # 1 sku_id repetido + 2 SKUs huérfanos + 1 título sin semilla
    assert len(errors) == 4


def test_collect_integrity_warnings_combines_every_check(title_seed: TitleSeed, eu_key_card_sku: Sku) -> None:
    sku = eu_key_card_sku.model_copy(update={"cart_size_gb": 16})

    assert len(collect_integrity_warnings([title_seed], [], [sku])) == 2
