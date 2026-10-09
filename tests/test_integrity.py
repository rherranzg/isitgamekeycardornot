from datetime import date, datetime, timedelta, timezone

import pytest

from switch2db.integrity import (
    collect_integrity_errors,
    collect_integrity_warnings,
    find_cart_size_warnings,
    find_completed_title_errors,
    find_download_size_warnings,
    find_duplicates,
    find_excluded_title_errors,
    find_id_duplication_errors,
    find_last_checked_errors,
    find_merged_title_errors,
    find_missing_sku_warnings,
    find_new_title_errors,
    find_omitted_sku_field_warnings,
    find_orphan_sku_errors,
    find_physical_release_errors,
    find_sourceless_sku_warnings,
    list_missing_sku_data,
    list_omitted_optional_sku_fields,
)
from switch2db.models import (
    Edition,
    ExcludedTitle,
    PhysicalRelease,
    Region,
    Sku,
    Title,
    TitleStatus,
)


def build_complete_skus(sku: Sku) -> list[Sku]:
    """The given SKU, with every field completed requires, copied to every region."""
    return [
        sku.model_copy(update={"region": region, "sku_id": f"{region.lower()}-example-game-standard"})
        for region in Region
    ]


def build_release(title_id: str, has_physical_release: bool, region: Region | None = None) -> PhysicalRelease:
    """physical_release.yaml entry for the given game, for the whole game or for one region."""
    return PhysicalRelease.model_validate(
        {
            "title_id": title_id,
            "has_physical_release": has_physical_release,
            "region": region,
            "evidence": "unconfirmed",
            "source_url": None,
            "checked_at": "2026-09-16",
        }
    )


def build_sourced_no_box(title_id: str, region: Region) -> PhysicalRelease:
    """Sourced "no box in that region" entry."""
    return build_release(title_id, False, region).model_copy(
        update={"evidence": "official", "source_url": "https://example.com/no-box"}
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
        "skus.yaml: 'eu-example-game-standard' references title_id 'example-game', "
        "which is not in titles.yaml"
    ]


def test_find_orphan_sku_errors_returns_empty_list_when_title_is_known(
    title: Title, eu_key_card_sku: Sku
) -> None:
    assert find_orphan_sku_errors([title], [eu_key_card_sku]) == []


def test_find_last_checked_errors_compares_the_day_of_a_check_with_time(
    title: Title, eu_key_card_sku: Sku
) -> None:
    checked = title.model_copy(
        update={"last_checked_at": datetime(2026, 9, 13, 8, 30, tzinfo=timezone(timedelta(hours=2)))}
    )

    assert find_last_checked_errors([checked], [eu_key_card_sku], []) == []


def test_find_last_checked_errors_reports_researched_title_without_date(
    title: Title, eu_key_card_sku: Sku
) -> None:
    unchecked = title.model_copy(update={"last_checked_at": None})

    errors = find_last_checked_errors([unchecked], [eu_key_card_sku], [])

    assert errors == ["titles.yaml: 'example-game' has sources checked on 2026-09-13, but no last_checked_at"]


def test_find_last_checked_errors_reports_date_older_than_a_checked_source(
    title: Title, eu_key_card_sku: Sku
) -> None:
    checked = title.model_copy(update={"last_checked_at": date(2026, 9, 15)})

    errors = find_last_checked_errors([checked], [eu_key_card_sku], [build_release("example-game", True)])

    assert errors == [
        "titles.yaml: 'example-game' last_checked_at 2026-09-15 is earlier than a "
        "source checked on 2026-09-16"
    ]


def test_find_last_checked_errors_counts_the_dates_of_sku_updates(title: Title, eu_key_card_sku: Sku) -> None:
    checked = title.model_copy(update={"last_checked_at": date(2026, 9, 13)})
    sku = Sku.model_validate(
        {
            **eu_key_card_sku.model_dump(mode="json"),
            "updates": [
                {"url": "https://example.com/delay", "checked_at": "2026-10-01", "fields": ["release_date"]}
            ],
        }
    )

    errors = find_last_checked_errors([checked], [sku], [])

    assert errors == [
        "titles.yaml: 'example-game' last_checked_at 2026-09-13 is earlier than a "
        "source checked on 2026-10-01"
    ]


def test_find_last_checked_errors_counts_the_dates_of_title_updates(title: Title) -> None:
    updated = Title.model_validate(
        {
            **title.model_dump(mode="json"),
            "updates": [
                {"url": "https://example.com/date", "checked_at": "2026-10-01", "fields": ["release_date"]}
            ],
        }
    )

    errors = find_last_checked_errors([updated], [], [])

    assert errors == [
        "titles.yaml: 'example-game' last_checked_at 2026-09-13 is earlier than a "
        "source checked on 2026-10-01"
    ]


def test_find_last_checked_errors_accepts_a_date_on_or_after_every_source(
    title: Title, eu_key_card_sku: Sku
) -> None:
    checked = title.model_copy(update={"last_checked_at": date(2026, 9, 16)})

    assert find_last_checked_errors([checked], [eu_key_card_sku], [build_release("example-game", True)]) == []


def test_find_last_checked_errors_ignores_titles_without_sources_or_not_researched(
    title: Title, eu_key_card_sku: Sku
) -> None:
    untouched = title.model_copy(update={"status": TitleStatus.NEW, "last_checked_at": None})
    no_sources = title.model_copy(update={"title_id": "searched-game", "last_checked_at": None})

    assert find_last_checked_errors([untouched, no_sources], [eu_key_card_sku], []) == []


def test_find_cart_size_warnings_reports_cart_size_on_non_full_cart(eu_key_card_sku: Sku) -> None:
    sku = eu_key_card_sku.model_copy(update={"cart_size_gb": 16})

    assert find_cart_size_warnings([sku]) == [
        "skus.yaml: 'eu-example-game-standard' has cart_size_gb with format 'game_key_card'"
    ]


def test_find_cart_size_warnings_returns_empty_list_for_full_cart(asia_full_cart_sku: Sku) -> None:
    assert find_cart_size_warnings([asia_full_cart_sku]) == []


def test_find_download_size_warnings_reports_download_size_on_full_cart(asia_full_cart_sku: Sku) -> None:
    assert find_download_size_warnings([asia_full_cart_sku]) == [
        "skus.yaml: 'asia-example-game-standard' has download_size_gb with format 'full_cart'"
    ]


def test_find_download_size_warnings_reports_download_size_on_unknown_format(jp_unknown_sku: Sku) -> None:
    sku_with_eshop_size = jp_unknown_sku.model_copy(update={"download_size_gb": 38.9})

    assert find_download_size_warnings([sku_with_eshop_size]) == [
        "skus.yaml: 'jp-example-game-standard' has download_size_gb with format 'unknown'"
    ]


def test_find_download_size_warnings_returns_empty_list_for_game_key_card(eu_key_card_sku: Sku) -> None:
    assert find_download_size_warnings([eu_key_card_sku]) == []


def test_list_omitted_optional_sku_fields_lists_missing_optional_keys(sku_row: dict[str, object]) -> None:
    row = {field: value for field, value in sku_row.items() if field not in {"ean", "includes_download_code"}}

    assert list_omitted_optional_sku_fields(row) == ["includes_download_code", "ean"]


def test_list_omitted_optional_sku_fields_allows_leaving_out_the_updates(sku_row: dict[str, object]) -> None:
    assert "updates" not in sku_row

    assert list_omitted_optional_sku_fields(sku_row) == []


def test_list_omitted_optional_sku_fields_ignores_missing_required_keys(sku_row: dict[str, object]) -> None:
    row = {field: value for field, value in sku_row.items() if field != "verified_at"}

    assert list_omitted_optional_sku_fields(row) == []


def test_list_omitted_optional_sku_fields_returns_empty_list_when_row_is_not_a_dict() -> None:
    assert list_omitted_optional_sku_fields("texto") == []


def test_find_omitted_sku_field_warnings_reports_row_position_and_keys(sku_row: dict[str, object]) -> None:
    row_without_ean = {field: value for field, value in sku_row.items() if field != "ean"}

    assert find_omitted_sku_field_warnings([sku_row, row_without_ean]) == [
        "skus.yaml #1 eu-example-game-standard: missing keys ['ean'] (null if unknown)"
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

    # 1 duplicate title_id + 1 duplicate igdb_id + 1 duplicate sku_id
    assert len(errors) == 3


def test_collect_integrity_warnings_combines_every_check(
    title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku, sku_without_source: Sku
) -> None:
    sku_with_cart_size = eu_key_card_sku.model_copy(update={"cart_size_gb": 16})
    skus = [sku_with_cart_size, asia_full_cart_sku, sku_without_source]

    warnings = collect_integrity_warnings([title], skus, [], [{"sku_id": "row-without-keys"}])

    # cart_size_gb without full_cart + download_size_gb on full_cart + SKU without source
    # + row with omitted keys
    assert len(warnings) == 4


def test_find_physical_release_errors_reports_unknown_and_duplicated_title_ids(title: Title) -> None:
    release = build_release("example-game", False)
    orphan = build_release("other-game", False)

    errors = find_physical_release_errors([title], [release, release, orphan], [])

    assert errors == [
        "physical_release.yaml: entrada repetida 'example-game'",
        "physical_release.yaml: 'other-game' is not in titles.yaml",
    ]


def test_find_physical_release_errors_reports_digital_only_title_with_skus(
    title: Title, eu_key_card_sku: Sku
) -> None:
    errors = find_physical_release_errors([title], [build_release("example-game", False)], [eu_key_card_sku])

    assert errors == [
        "physical_release.yaml: 'example-game' says there is no physical edition, but it has SKUs"
    ]


def test_find_physical_release_errors_accepts_one_entry_per_region(title: Title) -> None:
    releases = [
        build_release("example-game", False, Region.KR),
        build_release("example-game", False, Region.ASIA),
    ]

    assert find_physical_release_errors([title], releases, []) == []


def test_find_physical_release_errors_reports_no_box_region_with_a_sku(
    title: Title, eu_key_card_sku: Sku
) -> None:
    errors = find_physical_release_errors(
        [title], [build_release("example-game", False, Region.EU)], [eu_key_card_sku]
    )

    assert errors == [
        "physical_release.yaml: 'example-game' says there is no box in EU, but it has a SKU there"
    ]


def test_find_physical_release_errors_reports_region_entry_next_to_whole_game_entry(title: Title) -> None:
    releases = [build_release("example-game", False), build_release("example-game", False, Region.KR)]

    assert find_physical_release_errors([title], releases, []) == [
        "physical_release.yaml: 'example-game' has an entry for KR and one for the whole game"
    ]


def test_find_new_title_errors_reports_new_title_with_skus_or_releases(
    title: Title, eu_key_card_sku: Sku
) -> None:
    new_with_sku = title.model_copy(update={"status": TitleStatus.NEW, "last_checked_at": None})
    new_with_release = new_with_sku.model_copy(update={"title_id": "digital-game"})

    errors = find_new_title_errors(
        [new_with_sku, new_with_release], [eu_key_card_sku], [build_release("digital-game", False)]
    )

    assert errors == [
        "titles.yaml: 'example-game' is new but has SKUs or physical_release.yaml entries; use refresh",
        "titles.yaml: 'digital-game' is new but has SKUs or physical_release.yaml entries; use refresh",
    ]


def test_find_new_title_errors_ignores_researched_titles(title: Title, eu_key_card_sku: Sku) -> None:
    assert find_new_title_errors([title], [eu_key_card_sku], []) == []


def test_find_missing_sku_warnings_reports_physical_title_without_skus() -> None:
    warnings = find_missing_sku_warnings([build_release("example-game", True)], [])

    assert warnings == ["physical_release.yaml: 'example-game' has a physical edition but no SKU yet"]


def test_find_sourceless_sku_warnings_reports_skus_without_source_url(
    eu_key_card_sku: Sku, jp_unknown_sku: Sku, sku_without_source: Sku
) -> None:
    warnings = find_sourceless_sku_warnings([eu_key_card_sku, jp_unknown_sku, sku_without_source])

    assert warnings == [
        "skus.yaml: 'example-game' has 2 SKU(s) with no source: shown as unknown format, "
        "they need a deeper search"
    ]


def test_find_excluded_title_errors_reports_excluded_titles_still_in_titles_yaml(title: Title) -> None:
    excluded = [ExcludedTitle(igdb_id=title.igdb_id, name=title.name, reason="Solo en una recopilación")]

    assert find_excluded_title_errors([title], excluded) == [
        "titles.yaml: 'example-game' has igdb_id 12345, which is in excluded_titles.yaml"
    ]


def test_find_excluded_title_errors_reports_duplicated_igdb_ids() -> None:
    entry = ExcludedTitle(igdb_id=1, name="Alpha", reason="Solo en una recopilación")

    assert find_excluded_title_errors([], [entry, entry]) == ["excluded_titles.yaml: igdb_id repetido 1"]


def test_find_excluded_title_errors_returns_empty_list_when_nothing_overlaps(title: Title) -> None:
    excluded = [ExcludedTitle(igdb_id=1, name="Alpha", reason="Solo en una recopilación")]

    assert find_excluded_title_errors([title], excluded) == []


def build_merge(igdb_id: int, former_title_id: str, merged_into: str) -> ExcludedTitle:
    """Excluded edition whose old title was merged into another."""
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
        "excluded_titles.yaml: 1 goes to 'missing-game', which is not in titles.yaml",
        "excluded_titles.yaml: former_title_id 'example-game' is still in titles.yaml",
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


def test_list_missing_sku_data_returns_empty_list_for_a_complete_sku(eu_key_card_sku: Sku) -> None:
    assert list_missing_sku_data(eu_key_card_sku) == []


def test_list_missing_sku_data_does_not_require_cart_size_download_code_nor_ean(
    asia_full_cart_sku: Sku,
) -> None:
    without_optional = asia_full_cart_sku.model_copy(
        update={"cart_size_gb": None, "includes_download_code": None, "ean": None}
    )

    assert list_missing_sku_data(without_optional) == []


def test_list_missing_sku_data_lists_source_format_and_null_fields(sku_without_source: Sku) -> None:
    no_distributor = sku_without_source.model_copy(update={"distributor": None})

    assert list_missing_sku_data(no_distributor) == ["source_url", "format", "distributor"]


def test_list_missing_sku_data_requires_the_fields_that_apply_to_the_sku(eu_key_card_sku: Sku) -> None:
    deluxe = eu_key_card_sku.model_copy(update={"edition": Edition.DELUXE, "download_size_gb": None})

    assert list_missing_sku_data(deluxe) == ["edition_name", "download_size_gb"]


def test_find_completed_title_errors_accepts_every_region_with_complete_skus(
    title: Title, eu_key_card_sku: Sku
) -> None:
    completed = title.model_copy(update={"status": TitleStatus.COMPLETED})

    assert find_completed_title_errors([completed], build_complete_skus(eu_key_card_sku), []) == []


def test_find_completed_title_errors_reports_missing_regions_and_incomplete_skus(
    title: Title, eu_key_card_sku: Sku
) -> None:
    completed = title.model_copy(update={"status": TitleStatus.COMPLETED})
    skus = build_complete_skus(eu_key_card_sku)[:2]
    skus[1] = skus[1].model_copy(update={"distributor": None})

    assert find_completed_title_errors([completed], skus, []) == [
        "titles.yaml: 'example-game' is completed but no SKU nor sourced no-box entry in JP, KR, ASIA",
        "titles.yaml: 'example-game' is completed but 'na-example-game-standard' lacks distributor",
    ]


def test_find_completed_title_errors_accepts_regions_with_a_sourced_no_box_entry(
    title: Title, eu_key_card_sku: Sku
) -> None:
    completed = title.model_copy(update={"status": TitleStatus.COMPLETED})
    skus = build_complete_skus(eu_key_card_sku)[:3]
    releases = [
        build_sourced_no_box("example-game", Region.KR),
        build_sourced_no_box("example-game", Region.ASIA),
    ]

    assert find_completed_title_errors([completed], skus, releases) == []


def test_find_completed_title_errors_does_not_count_an_unsourced_no_box_region(
    title: Title, eu_key_card_sku: Sku
) -> None:
    completed = title.model_copy(update={"status": TitleStatus.COMPLETED})
    skus = build_complete_skus(eu_key_card_sku)[:4]

    errors = find_completed_title_errors(
        [completed], skus, [build_release("example-game", False, Region.ASIA)]
    )

    assert errors == ["titles.yaml: 'example-game' is completed but no SKU nor sourced no-box entry in ASIA"]


def test_find_completed_title_errors_accepts_a_sourced_digital_only_game(title: Title) -> None:
    completed = title.model_copy(update={"status": TitleStatus.COMPLETED})
    release = build_release("example-game", False).model_copy(
        update={"evidence": "official", "source_url": "https://example.com/digital"}
    )

    assert find_completed_title_errors([completed], [], [release]) == []


def test_find_completed_title_errors_reports_a_digital_only_game_without_source(title: Title) -> None:
    completed = title.model_copy(update={"status": TitleStatus.COMPLETED})

    assert find_completed_title_errors([completed], [], [build_release("example-game", False)]) == [
        "titles.yaml: 'example-game' is completed but physical_release.yaml entry without source_url"
    ]


def test_find_completed_title_errors_ignores_titles_not_completed(
    title: Title, sku_without_source: Sku
) -> None:
    assert find_completed_title_errors([title], [sku_without_source], []) == []
