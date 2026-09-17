from switch2db.models import PhysicalRelease, Region, Sku, Title, TitleStatus
from switch2db.site import (
    FORMAT_FILTER_LABELS,
    NO_BOX_FILTER_VALUE,
    NO_SKUS_FILTER_VALUE,
    build_search_text,
    build_sku_view,
    build_title_views,
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


def test_build_title_views_includes_titles_of_every_status(title: Title) -> None:
    new_title = title.model_copy(update={"title_id": "new-game", "status": TitleStatus.NEW})
    pending_title = title.model_copy(update={"title_id": "pending-game", "status": TitleStatus.PENDING})
    reviewed_title = title.model_copy(update={"title_id": "reviewed-game", "status": TitleStatus.REVIEWED})

    views = build_title_views([new_title, pending_title, reviewed_title], [], [])

    assert {view.title_id for view in views} == {"new-game", "pending-game", "reviewed-game"}


def test_build_title_views_includes_new_skus(title: Title, eu_key_card_sku: Sku, new_sku: Sku) -> None:
    views = build_title_views([title], [eu_key_card_sku, new_sku], [])

    assert [sku.region for sku in views[0].skus] == [Region.EU, Region.NA]


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


def test_format_filter_labels_add_the_no_box_and_no_skus_options() -> None:
    assert list(FORMAT_FILTER_LABELS) == [
        "full_cart",
        "game_key_card",
        "code_in_box",
        "unknown",
        NO_BOX_FILTER_VALUE,
        NO_SKUS_FILTER_VALUE,
    ]
    assert FORMAT_FILTER_LABELS[NO_BOX_FILTER_VALUE]["es"] == "Solo digital"
    assert FORMAT_FILTER_LABELS[NO_SKUS_FILTER_VALUE]["es"] == "Sin SKUs todavía"
