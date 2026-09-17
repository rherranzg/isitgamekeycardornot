from collections import defaultdict

from pydantic import BaseModel

from switch2db.divergences import find_format_divergences
from switch2db.i18n import (
    EDITION_LABELS,
    EVIDENCE_LABELS,
    FORMAT_LABELS,
    LANGUAGES,
    REGION_LABELS,
    UI_STRINGS,
)
from switch2db.models import Edition, Format, PhysicalRelease, Region, Sku, Title
from switch2db.slug import strip_accents

LocalizedText = dict[str, str]

# Valor con el que el filtro de formato representa a los juegos que nunca salieron en caja: no son un
# formato del enum, pero el visitante los busca en el mismo sitio que los demás.
NO_BOX_FILTER_VALUE = "no_box"

# Igual que NO_BOX_FILTER_VALUE, pero para los títulos que todavía no tienen ningún SKU documentado
# (status new/pending sin investigar).
NO_SKUS_FILTER_VALUE = "no_skus"

REPO_URL = "https://github.com/rherranzg/isitgamekeycardornot"
DATA_LICENSE_URL = f"{REPO_URL}/blob/main/data/LICENSE"
REPORT_ISSUE_URL = f"{REPO_URL}/issues/new"

FORMAT_CSS_CLASSES: dict[Format, str] = {
    Format.FULL_CART: "format-full-cart",
    Format.GAME_KEY_CARD: "format-game-key-card",
    Format.CODE_IN_BOX: "format-code-in-box",
    Format.UNKNOWN: "format-unknown",
}

# Etiquetas de los filtros, con la clave ya en texto: el filtro de formato añade un valor que no es un Format.
REGION_FILTER_LABELS: dict[str, LocalizedText] = {region.value: REGION_LABELS[region] for region in Region}
EDITION_FILTER_LABELS: dict[str, LocalizedText] = {
    edition.value: EDITION_LABELS[edition] for edition in Edition
}
FORMAT_FILTER_LABELS: dict[str, LocalizedText] = {
    **{format_.value: FORMAT_LABELS[format_] for format_ in Format},
    NO_BOX_FILTER_VALUE: UI_STRINGS["no_box_filter"],
    NO_SKUS_FILTER_VALUE: UI_STRINGS["no_skus_filter"],
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


class NoBoxView(BaseModel):
    """Nota de un juego que nunca salió en caja, con la fuente que lo respalda."""

    evidence_label: LocalizedText
    source_url: str | None


class TitleView(BaseModel):
    """Juego con sus SKUs agrupados y ordenados, listo para mostrar en la web."""

    title_id: str
    name: str
    publisher: str | None
    search_text: str
    skus: list[SkuView]
    has_divergence: bool
    no_box: NoBoxView | None


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
    )


def build_search_text(title: Title) -> str:
    """Texto por el que se busca un título: nombre y publisher sin tildes y en minúsculas, como en el JS."""
    return strip_accents(" ".join(filter(None, [title.name, title.publisher]))).lower()


def sku_sort_key(sku: Sku) -> tuple[str, str]:
    """Ordena los SKUs de un título por región y luego por edición."""
    return (sku.region.value, sku.edition.value)


def group_skus_by_title(skus: list[Sku]) -> dict[str, list[Sku]]:
    """Agrupa los SKUs por title_id, en el orden en que llegan."""
    groups: defaultdict[str, list[Sku]] = defaultdict(list)
    for sku in skus:
        groups[sku.title_id].append(sku)
    return dict(groups)


def build_no_box_view(release: PhysicalRelease) -> NoBoxView:
    """Traduce a la vista lo investigado sobre un juego que no llegó a tener caja."""
    return NoBoxView(
        evidence_label=EVIDENCE_LABELS[release.evidence],
        source_url=str(release.source_url) if release.source_url else None,
    )


def find_digital_only_releases(releases: list[PhysicalRelease]) -> dict[str, PhysicalRelease]:
    """Indexa por title_id los juegos investigados que no salieron en caja en ninguna región."""
    return {release.title_id: release for release in releases if not release.has_physical_release}


def build_title_view(
    title: Title,
    skus_by_title: dict[str, list[Sku]],
    diverging_title_ids: set[str],
    digital_only: dict[str, PhysicalRelease],
) -> TitleView:
    """Construye la vista de un título con sus SKUs ordenados, o con su nota de "no salió en caja"."""
    title_skus = sorted(skus_by_title.get(title.title_id, []), key=sku_sort_key)
    release = digital_only.get(title.title_id)
    return TitleView(
        title_id=title.title_id,
        name=title.name,
        publisher=title.publisher,
        search_text=build_search_text(title),
        skus=[build_sku_view(sku) for sku in title_skus],
        has_divergence=title.title_id in diverging_title_ids,
        no_box=build_no_box_view(release) if release is not None and not title_skus else None,
    )


def build_title_views(
    titles: list[Title], skus: list[Sku], releases: list[PhysicalRelease]
) -> list[TitleView]:
    """Agrupa los SKUs por título y devuelve las vistas ordenadas por nombre, para todos los títulos."""
    skus_by_title = group_skus_by_title(skus)
    diverging_title_ids = {title_id for title_id, _ in find_format_divergences(skus)}
    digital_only = find_digital_only_releases(releases)
    views = [build_title_view(title, skus_by_title, diverging_title_ids, digital_only) for title in titles]
    return sorted(views, key=lambda view: view.name.casefold())


def build_footer_text(generated_at: str) -> LocalizedText:
    """Compone el texto del pie de página con la fecha de generación, en cada idioma."""
    return {lang: text.format(date=generated_at) for lang, text in UI_STRINGS["footer"].items()}
