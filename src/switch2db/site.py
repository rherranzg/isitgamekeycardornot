from collections import defaultdict

from pydantic import BaseModel

from switch2db.divergences import find_format_divergences
from switch2db.i18n import EDITION_LABELS, EVIDENCE_LABELS, FORMAT_LABELS, LANGUAGES, UI_STRINGS
from switch2db.models import Edition, Format, Region, Sku, Title, TitleStatus

LocalizedText = dict[str, str]

# Solo se publica lo comprobado a mano: pending y refresh tienen datos de IGDB sin revisar.
PUBLISHED_TITLE_STATUS = TitleStatus.REVIEWED

FORMAT_CSS_CLASSES: dict[Format, str] = {
    Format.FULL_CART: "format-full-cart",
    Format.GAME_KEY_CARD: "format-game-key-card",
    Format.CODE_IN_BOX: "format-code-in-box",
    Format.UNKNOWN: "format-unknown",
}


class SkuView(BaseModel):
    """SKU regional traducido a etiquetas legibles, en cada idioma soportado."""

    region: Region
    edition: Edition
    format: Format
    format_label: LocalizedText
    format_css_class: str
    edition_label: LocalizedText
    distributor: str | None
    size_text: LocalizedText
    evidence_label: LocalizedText
    source_url: str | None
    verified_at: str


class TitleView(BaseModel):
    """Juego con sus SKUs agrupados y ordenados, listo para mostrar en la web."""

    title_id: str
    name: str
    publisher: str
    skus: list[SkuView]
    has_divergence: bool


def build_size_text(sku: Sku) -> LocalizedText:
    """Compone el texto de tamaño del SKU (cartucho o descarga) en cada idioma."""
    if sku.cart_size_gb is not None:
        return {lang: f"{sku.cart_size_gb} {UI_STRINGS['cart_suffix'][lang]}" for lang in LANGUAGES}
    if sku.download_size_gb is not None:
        return {lang: f"~{sku.download_size_gb} {UI_STRINGS['download_suffix'][lang]}" for lang in LANGUAGES}
    return dict.fromkeys(LANGUAGES, "—")


def build_sku_view(sku: Sku) -> SkuView:
    """Traduce un Sku a las etiquetas y el formato de texto que usa la plantilla."""
    return SkuView(
        region=sku.region,
        edition=sku.edition,
        format=sku.format,
        format_label=FORMAT_LABELS[sku.format],
        format_css_class=FORMAT_CSS_CLASSES[sku.format],
        edition_label=EDITION_LABELS[sku.edition],
        distributor=sku.distributor,
        size_text=build_size_text(sku),
        evidence_label=EVIDENCE_LABELS[sku.evidence],
        source_url=str(sku.source_url) if sku.source_url else None,
        verified_at=sku.verified_at.isoformat(),
    )


def sku_sort_key(sku: Sku) -> tuple[str, str]:
    """Ordena los SKUs de un título por región y luego por edición."""
    return (sku.region.value, sku.edition.value)


def group_skus_by_title(skus: list[Sku]) -> dict[str, list[Sku]]:
    """Agrupa los SKUs por title_id, en el orden en que llegan."""
    groups: defaultdict[str, list[Sku]] = defaultdict(list)
    for sku in skus:
        groups[sku.title_id].append(sku)
    return dict(groups)


def build_title_view(
    title: Title, skus_by_title: dict[str, list[Sku]], diverging_title_ids: set[str]
) -> TitleView:
    """Construye la vista de un título con sus SKUs ordenados."""
    title_skus = sorted(skus_by_title.get(title.title_id, []), key=sku_sort_key)
    return TitleView(
        title_id=title.title_id,
        name=title.name,
        publisher=title.publisher,
        skus=[build_sku_view(sku) for sku in title_skus],
        has_divergence=title.title_id in diverging_title_ids,
    )


def select_published_titles(titles: list[Title]) -> list[Title]:
    """Devuelve los títulos que se publican en la web: solo los revisados a mano."""
    return [title for title in titles if title.status == PUBLISHED_TITLE_STATUS]


def build_title_views(titles: list[Title], skus: list[Sku]) -> list[TitleView]:
    """Agrupa los SKUs por título y devuelve las vistas ordenadas por nombre."""
    skus_by_title = group_skus_by_title(skus)
    diverging_title_ids = {title_id for title_id, _ in find_format_divergences(skus)}
    views = [build_title_view(title, skus_by_title, diverging_title_ids) for title in titles]
    return sorted(views, key=lambda view: view.name.casefold())


def build_footer_text(generated_at: str) -> LocalizedText:
    """Compone el texto del pie de página con la fecha de generación, en cada idioma."""
    return {lang: text.format(date=generated_at) for lang, text in UI_STRINGS["footer"].items()}
