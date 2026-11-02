import sys

from aws_lambda_powertools import Logger

from switch2db.data_store import (
    load_covers,
    load_excluded_titles,
    load_physical_releases,
    load_titles,
    parse_rows,
    read_yaml_rows,
)
from switch2db.integrity import collect_integrity_errors, collect_integrity_warnings, find_cover_errors
from switch2db.models import Sku
from switch2db.paths import COVERS_DIR, DATA_DIR
from switch2db.report import build_report

FILL_RATE_THRESHOLD = 60.0

logger = Logger(service="switch2db-validate-data")


def main() -> int:
    """Validate the YAML files in data/, log the report and return the exit code."""
    titles, title_errors = load_titles(DATA_DIR / "titles.yaml")
    releases, release_errors = load_physical_releases(DATA_DIR / "physical_release.yaml")
    excluded, excluded_errors = load_excluded_titles(DATA_DIR / "excluded_titles.yaml")
    # Keep the raw rows: the omitted-keys warning needs to see what was written before defaults apply.
    sku_rows = read_yaml_rows(DATA_DIR / "skus.yaml")
    skus, sku_errors = parse_rows(sku_rows, Sku, "skus.yaml")
    covers, cover_errors = load_covers(DATA_DIR / "covers.yaml")
    cover_files = {path.stem for path in COVERS_DIR.glob("*.webp")}
    errors = [
        *title_errors,
        *release_errors,
        *excluded_errors,
        *sku_errors,
        *cover_errors,
        *collect_integrity_errors(titles, skus, releases, excluded),
        *find_cover_errors(covers, skus, cover_files),
    ]

    for warning in collect_integrity_warnings(titles, skus, releases, sku_rows):
        logger.warning(warning)
    logger.info("Data report", extra=build_report(titles, skus, FILL_RATE_THRESHOLD).model_dump())
    for error in errors:
        logger.error(error)
    logger.info("Validation finished", extra={"error_count": len(errors)})
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
