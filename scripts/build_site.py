import sys
from datetime import UTC, datetime

from aws_lambda_powertools import Logger
from jinja2 import Environment, FileSystemLoader

from switch2db.data_store import load_excluded_titles, load_physical_releases, load_skus, load_titles
from switch2db.i18n import SHOWING_COUNT_TEMPLATES, UI_STRINGS
from switch2db.paths import DATA_DIR, DOCS_DIR, TEMPLATES_DIR
from switch2db.site import (
    DATA_LICENSE_URL,
    DEFAULT_PAGE_SIZE,
    EDITION_FILTER_LABELS,
    FORMAT_FILTER_LABELS,
    IGDB_URL,
    NO_BOX_FILTER_VALUE,
    NO_SKUS_FILTER_VALUE,
    PAGE_SIZES,
    REGION_FILTER_LABELS,
    REPO_URL,
    REPORT_ISSUE_URL,
    TitleView,
    build_footer_text,
    build_title_views,
)

logger = Logger(service="switch2db-build-site")


def render_index(title_views: list[TitleView], generated_at: str) -> str:
    """Renderiza la página única de la web, con buscador y filtros, a partir de los títulos."""
    # autoescape=True y no select_autoescape(): este solo escapa .html/.htm/.xml y la plantilla es .jinja.
    environment = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = environment.get_template("index.html.jinja")
    return template.render(
        titles=title_views,
        title_count=len(title_views),
        sku_count=sum(len(title.skus) for title in title_views),
        t=UI_STRINGS,
        footer=build_footer_text(generated_at),
        region_labels=REGION_FILTER_LABELS,
        format_labels=FORMAT_FILTER_LABELS,
        edition_labels=EDITION_FILTER_LABELS,
        no_box_filter_value=NO_BOX_FILTER_VALUE,
        no_skus_filter_value=NO_SKUS_FILTER_VALUE,
        page_sizes=PAGE_SIZES,
        default_page_size=DEFAULT_PAGE_SIZE,
        showing_count_templates=SHOWING_COUNT_TEMPLATES,
        repo_url=REPO_URL,
        data_license_url=DATA_LICENSE_URL,
        report_issue_url=REPORT_ISSUE_URL,
        igdb_url=IGDB_URL,
    )


def main() -> int:
    """Genera la web estática en docs/ con todos los títulos y SKUs de la base de datos."""
    titles, title_errors = load_titles(DATA_DIR / "titles.yaml")
    skus, sku_errors = load_skus(DATA_DIR / "skus.yaml")
    releases, release_errors = load_physical_releases(DATA_DIR / "physical_release.yaml")
    excluded, excluded_errors = load_excluded_titles(DATA_DIR / "excluded_titles.yaml")
    errors = [*title_errors, *sku_errors, *release_errors, *excluded_errors]
    for error in errors:
        logger.error(error)
    if errors:
        return 1

    title_views = build_title_views(titles, skus, releases, excluded)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / ".nojekyll").touch()
    output_path = DOCS_DIR / "index.html"
    output_path.write_text(render_index(title_views, generated_at), encoding="utf-8")
    logger.info(
        "Web generada",
        extra={
            "output": str(output_path),
            "title_count": len(title_views),
            "digital_only_count": sum(1 for view in title_views if view.no_box),
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
