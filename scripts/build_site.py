import sys
from datetime import UTC, datetime
from pathlib import Path

from aws_lambda_powertools import Logger
from jinja2 import Environment, FileSystemLoader, select_autoescape

from switch2db.data_store import load_skus, load_titles
from switch2db.i18n import EDITION_LABELS, FORMAT_LABELS, SHOWING_COUNT_TEMPLATES, UI_STRINGS
from switch2db.models import Edition, Format
from switch2db.site import TitleView, build_footer_text, build_title_views

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "src" / "switch2db" / "templates"
# docs/, no site/: es la carpeta que GitHub Pages puede servir directamente desde main.
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs"

logger = Logger(service="switch2db-build-site")


def render_index(title_views: list[TitleView], generated_at: str) -> str:
    """Renderiza la página única de la web, con buscador, filtros y orden, a partir de los títulos."""
    environment = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape())
    template = environment.get_template("index.html.jinja")
    return template.render(
        titles=title_views,
        title_count=len(title_views),
        sku_count=sum(len(title.skus) for title in title_views),
        t=UI_STRINGS,
        footer=build_footer_text(generated_at),
        formats=list(Format),
        editions=list(Edition),
        format_labels=FORMAT_LABELS,
        edition_labels=EDITION_LABELS,
        showing_count_templates=SHOWING_COUNT_TEMPLATES,
    )


def main() -> int:
    """Genera la web estática en docs/ a partir de titles.yaml y skus.yaml."""
    titles, title_errors = load_titles(DATA_DIR / "titles.yaml")
    skus, sku_errors = load_skus(DATA_DIR / "skus.yaml")
    for error in [*title_errors, *sku_errors]:
        logger.error(error)
    if title_errors or sku_errors:
        return 1

    title_views = build_title_views(titles, skus)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / ".nojekyll").touch()
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(render_index(title_views, generated_at), encoding="utf-8")
    logger.info("Web generada", extra={"output": str(output_path), "title_count": len(title_views)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
