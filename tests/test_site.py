from switch2db.models import Region, Sku, Title, TitleStatus
from switch2db.site import build_sku_view, build_title_views, select_published_titles


def test_build_sku_view_translates_labels(eu_key_card_sku: Sku) -> None:
    view = build_sku_view(eu_key_card_sku)

    assert view.format_label == {"es": "Game-Key Card", "en": "Game-Key Card"}
    assert view.format_css_class == "format-game-key-card"
    assert view.edition_label == {"es": "Estándar", "en": "Standard"}
    assert view.evidence_label == {"es": "Foto de la caja", "en": "Box photo"}
    assert view.size_text == {"es": "~20.5 GB (descarga)", "en": "~20.5 GB (download)"}
    assert view.source_url == "https://example.com/eu"
    assert view.verified_at == "2026-09-13"


def test_build_sku_view_size_text_prefers_cart_size(asia_full_cart_sku: Sku) -> None:
    view = build_sku_view(asia_full_cart_sku)

    assert view.size_text == {"es": "64 GB (cartucho)", "en": "64 GB (cartridge)"}


def test_build_sku_view_size_text_is_dash_when_no_size_known(eu_key_card_sku: Sku) -> None:
    sku_without_size = eu_key_card_sku.model_copy(update={"download_size_gb": None})

    view = build_sku_view(sku_without_size)

    assert view.size_text == {"es": "—", "en": "—"}


def test_build_sku_view_keeps_source_url_none_when_missing(jp_unknown_sku: Sku) -> None:
    assert build_sku_view(jp_unknown_sku).source_url is None


def test_build_title_views_groups_and_sorts_skus_by_region(
    title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    views = build_title_views([title], [eu_key_card_sku, asia_full_cart_sku])

    assert len(views) == 1
    view = views[0]
    assert view.name == "Example Game"
    assert [sku.region for sku in view.skus] == [Region.ASIA, Region.EU]


def test_build_title_views_flags_divergence_when_formats_differ(
    title: Title, eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    views = build_title_views([title], [eu_key_card_sku, asia_full_cart_sku])

    assert views[0].has_divergence is True


def test_build_title_views_no_divergence_when_formats_agree(title: Title, eu_key_card_sku: Sku) -> None:
    same_format_other_region = eu_key_card_sku.model_copy(
        update={"sku_id": "na-example-game-standard", "region": Region.NA}
    )

    views = build_title_views([title], [eu_key_card_sku, same_format_other_region])

    assert views[0].has_divergence is False


def test_build_title_views_includes_titles_without_skus(title: Title) -> None:
    views = build_title_views([title], [])

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

    views = build_title_views([lowercase_title, uppercase_title], [])

    assert [view.name for view in views] == ["Animal Crossing", "zelda"]


def test_select_published_titles_keeps_only_reviewed_titles(title: Title) -> None:
    reviewed = title.model_copy(update={"title_id": "reviewed-game", "status": TitleStatus.REVIEWED})
    marked = title.model_copy(update={"title_id": "refresh-game", "status": TitleStatus.REFRESH})

    assert select_published_titles([title, reviewed, marked]) == [reviewed]


def test_select_published_titles_returns_empty_list_when_nothing_is_reviewed(title: Title) -> None:
    assert select_published_titles([title]) == []
