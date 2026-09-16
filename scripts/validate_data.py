import sys

from aws_lambda_powertools import Logger

from switch2db.data_store import load_physical_releases, load_titles, parse_rows, read_yaml_rows
from switch2db.integrity import collect_integrity_errors, collect_integrity_warnings
from switch2db.models import Sku
from switch2db.paths import DATA_DIR
from switch2db.report import build_report

FILL_RATE_THRESHOLD = 60.0

logger = Logger(service="switch2db-validate-data")


def main() -> int:
    """Valida los YAML de data/, registra el informe y devuelve el código de salida."""
    titles, title_errors = load_titles(DATA_DIR / "titles.yaml")
    releases, release_errors = load_physical_releases(DATA_DIR / "physical_release.yaml")
    # Se guardan las filas crudas: el aviso de claves omitidas necesita ver lo escrito antes de los defaults.
    sku_rows = read_yaml_rows(DATA_DIR / "skus.yaml")
    skus, sku_errors = parse_rows(sku_rows, Sku, "skus.yaml")
    errors = [
        *title_errors,
        *release_errors,
        *sku_errors,
        *collect_integrity_errors(titles, skus, releases),
    ]

    for warning in collect_integrity_warnings(titles, skus, releases, sku_rows):
        logger.warning(warning)
    logger.info("Informe de datos", extra=build_report(titles, skus, FILL_RATE_THRESHOLD).model_dump())
    for error in errors:
        logger.error(error)
    logger.info("Validación terminada", extra={"error_count": len(errors)})
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
