import sys
from pathlib import Path

from aws_lambda_powertools import Logger

from switch2db.data_store import load_skus, load_title_seeds, load_titles
from switch2db.integrity import collect_integrity_errors, collect_integrity_warnings
from switch2db.report import build_report

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILL_RATE_THRESHOLD = 60.0

logger = Logger(service="switch2db-validate-data")


def main() -> int:
    """Valida los YAML de data/, registra el informe y devuelve el código de salida."""
    seeds, seed_errors = load_title_seeds(DATA_DIR / "title_seeds.yaml")
    titles, title_errors = load_titles(DATA_DIR / "titles.yaml")
    skus, sku_errors = load_skus(DATA_DIR / "skus.yaml")
    errors = [*seed_errors, *title_errors, *sku_errors, *collect_integrity_errors(seeds, titles, skus)]

    for warning in collect_integrity_warnings(seeds, titles, skus):
        logger.warning(warning)
    logger.info("Informe de datos", extra=build_report(skus, FILL_RATE_THRESHOLD).model_dump())
    for error in errors:
        logger.error(error)
    logger.info("Validación terminada", extra={"error_count": len(errors)})
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
