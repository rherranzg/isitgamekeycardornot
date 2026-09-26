from switch2db.models import Edition, Evidence, Format, Region

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

REGION_LABELS: dict[Region, dict[str, str]] = {
    Region.EU: {"es": "Europa (EU)", "en": "Europe (EU)"},
    Region.NA: {"es": "Norteamérica (NA)", "en": "North America (NA)"},
    Region.JP: {"es": "Japón (JP)", "en": "Japan (JP)"},
    Region.KR: {"es": "Corea (KR)", "en": "Korea (KR)"},
    Region.ASIA: {"es": "Asia: HK/TW/SEA (ASIA)", "en": "Asia: HK/TW/SEA (ASIA)"},
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
    "col_region": {"es": "Región", "en": "Region"},
    "col_edition": {"es": "Edición", "en": "Edition"},
    "col_format": {"es": "Formato", "en": "Format"},
    "col_distributor": {"es": "Distribuidora", "en": "Distributor"},
    "col_size": {"es": "Tamaño", "en": "Size"},
    "col_source": {"es": "Fuente", "en": "Source"},
    "cart_suffix": {"es": "GB (cartucho)", "en": "GB (cartridge)"},
    "download_suffix": {"es": "GB (descarga)", "en": "GB (download)"},
    "footer": {"es": "Generado el {date}.", "en": "Generated on {date}."},
    "footer_repo": {"es": "Código y datos en GitHub", "en": "Code and data on GitHub"},
    "footer_license": {"es": "Datos bajo licencia ODbL 1.0", "en": "Data licensed under ODbL 1.0"},
    "footer_report": {"es": "Reportar una corrección", "en": "Report a correction"},
    "footer_accuracy": {
        "es": "Cada dato enlaza la fuente en la que se basa. Puede haber errores: "
        "compruébalo antes de comprar.",
        "en": "Every entry links to the source it is based on. Mistakes are possible: "
        "double-check before buying.",
    },
    "footer_igdb": {
        "es": "Nombres, publishers y fechas de salida:",
        "en": "Game names, publishers and release dates:",
    },
    "footer_trademark": {
        "es": "Nintendo, Nintendo Switch 2 y Game-Key Card son marcas de Nintendo. Proyecto independiente, "
        "sin relación con Nintendo ni respaldado por ella.",
        "en": "Nintendo, Nintendo Switch 2 and Game-Key Card are trademarks of Nintendo. "
        "Independent project, not affiliated with or endorsed by Nintendo.",
    },
    "language_label": {"es": "Idioma", "en": "Language"},
    "search_placeholder": {"es": "Buscar juego o publisher...", "en": "Search game or publisher..."},
    "no_results": {"es": "No se encontraron juegos.", "en": "No games found."},
    "no_data": {"es": "Todavía sin SKUs documentados.", "en": "No SKUs documented yet."},
    "no_box_filter": {"es": "Sin edición física", "en": "No physical edition"},
    "no_skus_filter": {"es": "Sin SKUs todavía", "en": "No SKUs yet"},
    "pagination_label": {"es": "Páginas", "en": "Pages"},
    "page_size_label": {"es": "Juegos por página", "en": "Games per page"},
    "pagination_previous": {"es": "‹ Anterior", "en": "‹ Previous"},
    "pagination_next": {"es": "Siguiente ›", "en": "Next ›"},
    "no_box_note": {
        "es": "Solo digital",
        "en": "Digital only",
    },
    # Searched without finding a box, but with no source saying there is none: "digital only" is not claimed.
    "no_box_unconfirmed_note": {
        "es": "No se ha encontrado edición física",
        "en": "No physical edition found",
    },
}

MONTH_ABBREVIATIONS: dict[str, tuple[str, ...]] = {
    "es": ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"),
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
}

# Release date by precision; {month} is the abbreviation from MONTH_ABBREVIATIONS.
RELEASE_DATE_TEMPLATES: dict[str, dict[str, str]] = {
    "day": {"es": "{day} {month} {year}", "en": "{month} {day}, {year}"},
    "month": {"es": "{month} {year}", "en": "{month} {year}"},
    "quarter": {"es": "T{quarter} {year}", "en": "Q{quarter} {year}"},
    "year": {"es": "{year}", "en": "{year}"},
}

SHOWING_COUNT_TEMPLATES: dict[str, str] = {
    "es": "Mostrando {shown} de {total} juegos",
    "en": "Showing {shown} of {total} games",
}
