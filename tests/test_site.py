from switch2db.models import PhysicalRelease, Region, Sku, Title, TitleStatus
from switch2db.site import (
    FORMAT_FILTER_LABELS,
    NO_BOX_FILTER_VALUE,
    build_search_text,
    build_sku_view,
    build_title_views,
    select_published_skus,
    select_published_titles,
)


def test_build_sku_view_translates_labels(eu_key_card_sku: Sku) -> None:
    view = build_sku_view(eu_key_card_sku)

    assert view.format_label == {"es": "Game-Key Card", "en": "Game-Key Card"}
    assert view.format_css_class == "format-game-key-card"
    assert view.edition_label == {"es": "Estándar", "en": "Standard"}
    assert view.evidence_label == {"es": "Foto de la caja", "en": "Box photo"}
    assert view.size_text == {"es": "~20.5 GB (descarga)", "en": "~20.5 GB (download)"}
    assert view.source_url == "https://example.com/eu"


def test_build_sku_view_size_text_prefers_cart_size(asia_full_cart_sku: Sku) -> None:
    view = build_sku_view(asia_full_cart_sku)

    assert view.size_text == {"es": "64 GB (cartucho)", "en": "64 GB (cartridge)"}


def test_build_sku_view_size_text_is_dash_when_no_size_known(eu_key_card_sku: Sku) -> None:
    sku_without_size = eu_key_card_sku.model_copy(update={"download_size_gb": None})

    view = build_sku_view(sku_without_size)

    assert view.size_text == {"es": "—", "en": "—"}


def test_build_sku_view_keeps_source_url_none_when_missing(jp_unknown_sku: Sku) -> None:
    assert build_sku_view(jp_unknown_sku).source_url is None


def test_build_search_text_joins_name_and_publisher_without_accents(title: Title) -> None:
    accented = title.model_copy(update={"name": "Pokémon Légendes: Z-A", "publisher": "Nintendo"})

    assert build_search_text(accented) == "pokemon legendes: z-a nintendo"


def test_build_title_views_groups_and_sorts_skus_by_region(
    title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    views = build_title_views([title], [eu_key_card_sku, asia_full_cart_sku], [])

    assert len(views) == 1
    view = views[0]
    assert view.name == "Example Game"
    assert view.search_text == "example game example publisher"
    assert [sku.region for sku in view.skus] == [Region.ASIA, Region.EU]


def test_build_title_views_flags_divergence_when_formats_differ(
    title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    views = build_title_views([title], [eu_key_card_sku, asia_full_cart_sku], [])

    assert views[0].has_divergence is True


def test_build_title_views_no_divergence_when_formats_agree(title: Title, eu_key_card_sku: Sku) -> None:
    same_format_other_region = eu_key_card_sku.model_copy(
        update={"sku_id": "na-example-game-standard", "region": Region.NA}
    )

    views = build_title_views([title], [eu_key_card_sku, same_format_other_region], [])

    assert views[0].has_divergence is False


def test_build_title_views_includes_titles_without_skus(title: Title) -> None:
    views = build_title_views([title], [], [])

    assert views[0].skus == []
    assert views[0].has_divergence is False


def test_build_title_views_sorts_by_name_case_insensitive() -> None:
    lowercase_title = Title(
        title_id="zelda", igdb_id=1, name="zelda", publisher="Nintendo", status=TitleStatus.PENDING
    )
    uppercase_title = Title(
        title_id="animal-crossing",
        igdb_id=2,
        name="Animal Crossing",
        publisher="Nintendo",
        status=TitleStatus.PENDING,
    )

    views = build_title_views([lowercase_title, uppercase_title], [], [])

    assert [view.name for view in views] == ["Animal Crossing", "zelda"]


def test_select_published_titles_keeps_only_reviewed_titles(title: Title, eu_key_card_sku: Sku) -> None:
    reviewed = title.model_copy(update={"status": TitleStatus.REVIEWED})
    untouched = title.model_copy(update={"status": TitleStatus.NEW})

    assert select_published_titles([title, reviewed, untouched], [eu_key_card_sku], []) == [reviewed]


def test_select_published_titles_skips_reviewed_titles_without_skus(
    title: Title, eu_key_card_sku: Sku
) -> None:
    reviewed = title.model_copy(update={"status": TitleStatus.REVIEWED})
    reviewed_without_skus = title.model_copy(
        update={"title_id": "empty-game", "status": TitleStatus.REVIEWED}
    )

    assert select_published_titles([reviewed, reviewed_without_skus], [eu_key_card_sku], []) == [reviewed]


def test_select_published_titles_returns_empty_list_when_nothing_is_reviewed(
    title: Title, eu_key_card_sku: Sku
) -> None:
    assert select_published_titles([title], [eu_key_card_sku], []) == []


def test_select_published_skus_hides_new_skus(eu_key_card_sku: Sku, new_sku: Sku, pending_sku: Sku) -> None:
    published = select_published_skus([eu_key_card_sku, new_sku, pending_sku])

    assert [sku.sku_id for sku in published] == ["eu-example-game-standard", "kr-example-game-standard"]


def test_select_published_titles_skips_titles_whose_skus_are_all_new(title: Title, new_sku: Sku) -> None:
    reviewed = title.model_copy(update={"status": TitleStatus.REVIEWED})

    assert select_published_titles([reviewed], [new_sku], []) == []


def test_build_title_views_leaves_new_skus_out(title: Title, eu_key_card_sku: Sku, new_sku: Sku) -> None:
    views = build_title_views([title], [eu_key_card_sku, new_sku], [])

    assert [sku.region for sku in views[0].skus] == [Region.EU]


def test_select_published_titles_keeps_reviewed_titles_without_box(
    title: Title, digital_only: PhysicalRelease
) -> None:
    reviewed = title.model_copy(update={"status": TitleStatus.REVIEWED})

    assert select_published_titles([reviewed], [], [digital_only]) == [reviewed]


def test_select_published_titles_skips_titles_with_a_box_but_no_skus_yet(
    title: Title, digital_only: PhysicalRelease
) -> None:
    reviewed = title.model_copy(update={"status": TitleStatus.REVIEWED})
    with_box = digital_only.model_copy(update={"has_physical_release": True})

    assert select_published_titles([reviewed], [], [with_box]) == []


def test_build_title_views_shows_the_no_box_note_with_its_source(
    title: Title, digital_only: PhysicalRelease
) -> None:
    view = build_title_views([title], [], [digital_only])[0]

    assert view.skus == []
    assert view.no_box is not None
    assert view.no_box.evidence_label == {"es": "Fuente oficial", "en": "Official source"}
    assert view.no_box.source_url == "https://example.com/digital-only"


def test_build_title_views_prefers_the_skus_over_the_no_box_note(
    title: Title, eu_key_card_sku: Sku, digital_only: PhysicalRelease
) -> None:
    view = build_title_views([title], [eu_key_card_sku], [digital_only])[0]

    assert view.no_box is None
    assert [sku.region for sku in view.skus] == [Region.EU]


def test_format_filter_labels_add_the_no_box_option() -> None:
    assert list(FORMAT_FILTER_LABELS) == [
        "full_cart",
        "game_key_card",
        "code_in_box",
        "unknown",
        NO_BOX_FILTER_VALUE,
    ]
    assert FORMAT_FILTER_LABELS[NO_BOX_FILTER_VALUE]["es"] == "Sin edición física"
