import pytest

from switch2db.integrity import (
    collect_integrity_errors,
    collect_integrity_warnings,
    find_cart_size_warnings,
    find_download_size_warnings,
    find_duplicates,
    find_excluded_title_errors,
    find_id_duplication_errors,
    find_merged_title_errors,
    find_missing_sku_warnings,
    find_omitted_sku_field_warnings,
    find_orphan_sku_errors,
    find_physical_release_errors,
    find_sku_status_warnings,
    find_unpublished_sku_warnings,
    find_unresearched_title_warnings,
    list_omitted_optional_sku_fields,
)
from switch2db.models import ExcludedTitle, PhysicalRelease, Sku, SkuStatus, Title, TitleStatus


def build_release(title_id: str, has_physical_release: bool) -> PhysicalRelease:
    """Entrada de physical_release.yaml para el juego indicado."""
    return PhysicalRelease.model_validate(
        {
            "title_id": title_id,
            "has_physical_release": has_physical_release,
            "evidence": "unconfirmed",
            "source_url": None,
            "checked_at": "2026-09-16",
        }
    )


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


def test_find_id_duplication_errors_reports_every_duplicated_id(title: Title, eu_key_card_sku: Sku) -> None:
    errors = find_id_duplication_errors([title, title], [eu_key_card_sku, eu_key_card_sku])

    assert errors == [
        "titles.yaml: title_id repetido 'example-game'",
        "titles.yaml: igdb_id repetido 12345",
        "skus.yaml: sku_id repetido 'eu-example-game-standard'",
    ]


def test_find_id_duplication_errors_returns_empty_list_when_ids_are_unique(
    title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    assert find_id_duplication_errors([title], [eu_key_card_sku, asia_full_cart_sku]) == []


def test_find_orphan_sku_errors_reports_unknown_title_id(eu_key_card_sku: Sku) -> None:
    errors = find_orphan_sku_errors([], [eu_key_card_sku])

    assert errors == [
        "skus.yaml: 'eu-example-game-standard' referencia title_id 'example-game', que no está en titles.yaml"
    ]


def test_find_orphan_sku_errors_returns_empty_list_when_title_is_known(
    title: Title, eu_key_card_sku: Sku
) -> None:
    assert find_orphan_sku_errors([title], [eu_key_card_sku]) == []


def test_find_unresearched_title_warnings_reports_researched_title_without_any_result(
    title: Title,
) -> None:
    warnings = find_unresearched_title_warnings([title], [], [])

    assert warnings == [
        "titles.yaml: 'example-game' está pending pero no tiene ningún SKU "
        "ni entrada en physical_release.yaml"
    ]


def test_find_unresearched_title_warnings_accepts_skus_or_a_physical_release(
    title: Title, eu_key_card_sku: Sku
) -> None:
    digital_only = title.model_copy(update={"title_id": "digital-game", "status": TitleStatus.REVIEWED})

    warnings = find_unresearched_title_warnings(
        [title, digital_only], [eu_key_card_sku], [build_release("digital-game", False)]
    )

    assert warnings == []


def test_find_unresearched_title_warnings_ignores_titles_nobody_has_researched(title: Title) -> None:
    untouched = title.model_copy(update={"status": TitleStatus.NEW})

    assert find_unresearched_title_warnings([untouched], [], []) == []


def test_find_cart_size_warnings_reports_cart_size_on_non_full_cart(eu_key_card_sku: Sku) -> None:
    sku = eu_key_card_sku.model_copy(update={"cart_size_gb": 16})

    assert find_cart_size_warnings([sku]) == [
        "skus.yaml: 'eu-example-game-standard' tiene cart_size_gb con format 'game_key_card'"
    ]


def test_find_cart_size_warnings_returns_empty_list_for_full_cart(asia_full_cart_sku: Sku) -> None:
    assert find_cart_size_warnings([asia_full_cart_sku]) == []


def test_find_download_size_warnings_reports_download_size_on_full_cart(asia_full_cart_sku: Sku) -> None:
    assert find_download_size_warnings([asia_full_cart_sku]) == [
        "skus.yaml: 'asia-example-game-standard' tiene download_size_gb con format 'full_cart'"
    ]


def test_find_download_size_warnings_returns_empty_list_for_game_key_card(eu_key_card_sku: Sku) -> None:
    assert find_download_size_warnings([eu_key_card_sku]) == []


@pytest.mark.parametrize("status", [TitleStatus.NEW, TitleStatus.PENDING])
def test_find_unpublished_sku_warnings_reports_skus_of_titles_not_reviewed(
    title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku, status: TitleStatus
) -> None:
    not_reviewed = title.model_copy(update={"status": status})

    assert find_unpublished_sku_warnings([not_reviewed], [eu_key_card_sku, asia_full_cart_sku]) == [
        "skus.yaml: 'example-game' tiene 2 SKU(s) sin publicar porque su título no está reviewed"
    ]


def test_find_unpublished_sku_warnings_reports_skus_of_titles_not_imported(eu_key_card_sku: Sku) -> None:
    assert len(find_unpublished_sku_warnings([], [eu_key_card_sku])) == 1


def test_find_unpublished_sku_warnings_returns_empty_list_when_title_is_reviewed(
    title: Title, eu_key_card_sku: Sku
) -> None:
    reviewed = title.model_copy(update={"status": TitleStatus.REVIEWED})

    assert find_unpublished_sku_warnings([reviewed], [eu_key_card_sku]) == []


def test_list_omitted_optional_sku_fields_lists_missing_optional_keys(sku_row: dict[str, object]) -> None:
    row = {field: value for field, value in sku_row.items() if field not in {"ean", "includes_download_code"}}

    assert list_omitted_optional_sku_fields(row) == ["includes_download_code", "ean"]


def test_list_omitted_optional_sku_fields_ignores_missing_required_keys(sku_row: dict[str, object]) -> None:
    row = {field: value for field, value in sku_row.items() if field != "verified_at"}

    assert list_omitted_optional_sku_fields(row) == []


def test_list_omitted_optional_sku_fields_returns_empty_list_when_row_is_not_a_dict() -> None:
    assert list_omitted_optional_sku_fields("texto") == []


def test_find_omitted_sku_field_warnings_reports_row_position_and_keys(sku_row: dict[str, object]) -> None:
    row_without_ean = {field: value for field, value in sku_row.items() if field != "ean"}

    assert find_omitted_sku_field_warnings([sku_row, row_without_ean]) == [
        "skus.yaml #1 eu-example-game-standard: faltan las claves ['ean'] (null si no se sabe)"
    ]


def test_find_omitted_sku_field_warnings_returns_empty_list_when_rows_are_complete(
    sku_row: dict[str, object],
) -> None:
    assert find_omitted_sku_field_warnings([sku_row]) == []


def test_collect_integrity_errors_returns_empty_list_for_consistent_data(
    title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    assert collect_integrity_errors([title], [eu_key_card_sku, asia_full_cart_sku], [], []) == []


def test_collect_integrity_errors_combines_every_check(title: Title, eu_key_card_sku: Sku) -> None:
    errors = collect_integrity_errors([title, title], [eu_key_card_sku, eu_key_card_sku], [], [])

    # 1 title_id repetido + 1 igdb_id repetido + 1 sku_id repetido
    assert len(errors) == 3


def test_collect_integrity_warnings_combines_every_check(
    title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    sku_with_cart_size = eu_key_card_sku.model_copy(update={"cart_size_gb": 16})

    warnings = collect_integrity_warnings(
        [title], [sku_with_cart_size, asia_full_cart_sku], [], [{"sku_id": "row-without-keys"}]
    )

    # cart_size_gb sin full_cart + download_size_gb en full_cart + SKUs sin publicar
    # + fila con claves omitidas
    assert len(warnings) == 4


def test_find_physical_release_errors_reports_unknown_and_duplicated_title_ids(title: Title) -> None:
    release = build_release("example-game", False)
    orphan = build_release("other-game", False)

    errors = find_physical_release_errors([title], [release, release, orphan], [])

    assert errors == [
        "physical_release.yaml: title_id repetido 'example-game'",
        "physical_release.yaml: 'other-game' no está en titles.yaml",
    ]


def test_find_physical_release_errors_reports_digital_only_title_with_skus(
    title: Title, eu_key_card_sku: Sku
) -> None:
    errors = find_physical_release_errors([title], [build_release("example-game", False)], [eu_key_card_sku])

    assert errors == ["physical_release.yaml: 'example-game' dice que no hay edición física, pero tiene SKUs"]


def test_find_missing_sku_warnings_reports_physical_title_without_skus() -> None:
    warnings = find_missing_sku_warnings([build_release("example-game", True)], [])

    assert warnings == [
        "physical_release.yaml: 'example-game' tiene edición física y todavía no tiene ningún SKU"
    ]


def test_find_sku_status_warnings_reports_new_pending_and_refresh_skus(
    eu_key_card_sku: Sku, new_sku: Sku, pending_sku: Sku
) -> None:
    to_refresh = eu_key_card_sku.model_copy(update={"status": SkuStatus.REFRESH})

    warnings = find_sku_status_warnings([eu_key_card_sku, new_sku, pending_sku, to_refresh])

    assert warnings == [
        "skus.yaml: 'example-game' tiene 1 SKU(s) con status new, que no salen en la web",
        "skus.yaml: 'example-game' tiene 1 SKU(s) sin fuente encontrada (status pending): "
        "salen como formato desconocido y hay que buscarlos a fondo",
        "skus.yaml: 'example-game' tiene 1 SKU(s) marcados para volver a comprobar (status refresh)",
    ]


def test_find_excluded_title_errors_reports_excluded_titles_still_in_titles_yaml(title: Title) -> None:
    excluded = [ExcludedTitle(igdb_id=title.igdb_id, name=title.name, reason="Solo en una recopilación")]

    assert find_excluded_title_errors([title], excluded) == [
        "titles.yaml: 'example-game' tiene el igdb_id 12345, que está en excluded_titles.yaml"
    ]


def test_find_excluded_title_errors_reports_duplicated_igdb_ids() -> None:
    entry = ExcludedTitle(igdb_id=1, name="Alpha", reason="Solo en una recopilación")

    assert find_excluded_title_errors([], [entry, entry]) == ["excluded_titles.yaml: igdb_id repetido 1"]


def test_find_excluded_title_errors_returns_empty_list_when_nothing_overlaps(title: Title) -> None:
    excluded = [ExcludedTitle(igdb_id=1, name="Alpha", reason="Solo en una recopilación")]

    assert find_excluded_title_errors([title], excluded) == []


def build_merge(igdb_id: int, former_title_id: str, merged_into: str) -> ExcludedTitle:
    """Edición excluida cuyo título viejo se ha fusionado en otro."""
    return ExcludedTitle(
        igdb_id=igdb_id,
        name="Example Game: Deluxe Edition",
        reason="Edición de Example Game",
        former_title_id=former_title_id,
        merged_into=merged_into,
    )


def test_find_merged_title_errors_reports_unknown_target_and_former_id_still_in_use(title: Title) -> None:
    excluded = [build_merge(1, "old-game", "missing-game"), build_merge(2, "example-game", "example-game")]

    assert find_merged_title_errors([title], excluded) == [
        "excluded_titles.yaml: 1 va a 'missing-game', que no está en titles.yaml",
        "excluded_titles.yaml: el former_title_id 'example-game' sigue en titles.yaml",
    ]


def test_find_merged_title_errors_reports_duplicated_former_title_ids(title: Title) -> None:
    excluded = [build_merge(1, "old-game", "example-game"), build_merge(2, "old-game", "example-game")]

    assert find_merged_title_errors([title], excluded) == [
        "excluded_titles.yaml: former_title_id repetido 'old-game'"
    ]


def test_find_merged_title_errors_returns_empty_list_for_a_valid_merge(title: Title) -> None:
    excluded = [
        build_merge(1, "example-game-deluxe-edition", "example-game"),
        ExcludedTitle(igdb_id=2, name="Alpha", reason="Solo en una recopilación"),
    ]

    assert find_merged_title_errors([title], excluded) == []
