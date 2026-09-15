from switch2db.models import Edition, Evidence, Format

LANGUAGES: tuple[str, ...] = ("es", "en")

FORMAT_LABELS: dict[Format, dict[str, str]] = {
    Format.FULL_CART: {"es": "Cartucho completo", "en": "Full cartridge"},
    Format.GAME_KEY_CARD: {"es": "Game-Key Card", "en": "Game-Key Card"},
    Format.CODE_IN_BOX: {"es": "Código en la caja", "en": "Code in box"},
    Format.UNKNOWN: {"es": "Desconocido", "en": "Unknown"},
}

EDITION_LABELS: dict[Edition, dict[str, str]] = {
    Edition.STANDARD: {"es": "Estándar", "en": "Standard"},
    Edition.DELUXE: {"es": "Deluxe", "en": "Deluxe"},
    Edition.COLLECTORS: {"es": "Coleccionista", "en": "Collector's"},
}

EVIDENCE_LABELS: dict[Evidence, dict[str, str]] = {
    Evidence.OFFICIAL: {"es": "Fuente oficial", "en": "Official source"},
    Evidence.BOX_PHOTO: {"es": "Foto de la caja", "en": "Box photo"},
    Evidence.RETAILER_LISTING: {"es": "Ficha de tienda", "en": "Retailer listing"},
    Evidence.PRESS_REPORT: {"es": "Prensa", "en": "Press report"},
    Evidence.UNCONFIRMED: {"es": "Sin confirmar", "en": "Unconfirmed"},
}

UI_STRINGS: dict[str, dict[str, str]] = {
    "tagline": {
        "es": (
            "Base de datos abierta del formato físico de los juegos de Nintendo Switch 2: "
            "cartucho completo, Game-Key Card o código en la caja, región por región."
        ),
        "en": (
            "Open database of the physical format of Nintendo Switch 2 games: "
            "full cartridge, Game-Key Card or code in box, region by region."
        ),
    },
    "stat_titles": {"es": "juegos catalogados", "en": "games catalogued"},
    "stat_skus": {"es": "SKUs regionales documentados", "en": "regional SKUs documented"},
    "divergence_flag": {"es": "El formato cambia según la región", "en": "Format differs by region"},
    "no_data": {"es": "Todavía sin SKUs documentados.", "en": "No SKUs documented yet."},
    "col_region": {"es": "Región", "en": "Region"},
    "col_edition": {"es": "Edición", "en": "Edition"},
    "col_format": {"es": "Formato", "en": "Format"},
    "col_distributor": {"es": "Distribuidora", "en": "Distributor"},
    "col_size": {"es": "Tamaño", "en": "Size"},
    "col_source": {"es": "Fuente", "en": "Source"},
    "cart_suffix": {"es": "GB (cartucho)", "en": "GB (cartridge)"},
    "download_suffix": {"es": "GB (descarga)", "en": "GB (download)"},
    "footer": {"es": "Generado el {date}.", "en": "Generated on {date}."},
    "language_label": {"es": "Idioma", "en": "Language"},
    "search_placeholder": {"es": "Buscar juego...", "en": "Search game..."},
    "sort_by_label": {"es": "Ordenar por", "en": "Sort by"},
    "sort_name": {"es": "Nombre", "en": "Name"},
    "no_results": {"es": "No se encontraron juegos.", "en": "No games found."},
}

SHOWING_COUNT_TEMPLATES: dict[str, str] = {
    "es": "Mostrando {shown} de {total} juegos",
    "en": "Showing {shown} of {total} games",
}
