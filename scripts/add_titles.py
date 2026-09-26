import argparse
from datetime import date
from pathlib import Path

from aws_lambda_powertools import Logger

from switch2db.catalog import CatalogEntry
from switch2db.data_store import (
    load_excluded_titles,
    load_titles,
    read_yaml_rows,
    require_valid,
    write_titles,
)
from switch2db.paths import DATA_DIR
from switch2db.title_selection import refresh_release_dates, select_new_titles

logger = Logger(service="switch2db-add-titles")


def parse_args() -> argparse.Namespace:
    """Define and parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Add games from the local IGDB catalog to titles.yaml with status new, and refresh the "
        "release date of those already there."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--count", type=int, help="Number of new games to add")
    group.add_argument("--all", action="store_true", help="Add every game left in the catalog")
    group.add_argument("--dates-only", action="store_true", help="Add no games: only refresh release dates")
    args = parser.parse_args()
    if args.count is not None and args.count <= 0:
        parser.error("--count must be greater than 0")
    return args


def load_catalog(path: Path) -> list[CatalogEntry]:
    """Load the local IGDB catalog downloaded by download_igdb_catalog."""
    return [CatalogEntry.model_validate(row) for row in read_yaml_rows(path)]


def resolve_limit(args: argparse.Namespace) -> int | None:
    """Turn the arguments into how many titles to add: None means all of them."""
    if args.dates_only:
        return 0
    if args.all:
        return None
    return args.count


def main() -> None:
    """Refresh release dates and add new titles from the local catalog to titles.yaml. Does not query
    IGDB or any other network."""
    args = parse_args()
    titles_path = DATA_DIR / "titles.yaml"
    catalog = load_catalog(DATA_DIR / "igdb_catalog.yaml")
    titles = require_valid(load_titles(titles_path), titles_path.name)
    excluded = require_valid(load_excluded_titles(DATA_DIR / "excluded_titles.yaml"), "excluded_titles.yaml")

    refreshed = refresh_release_dates(titles, catalog, date.today())
    changed_dates = sum(
        old.release_date != new.release_date for old, new in zip(titles, refreshed, strict=True)
    )
    new_titles = select_new_titles(catalog, refreshed, excluded, resolve_limit(args))
    write_titles(titles_path, refreshed + new_titles)
    logger.info(
        "titles.yaml updated",
        extra={
            "added": len(new_titles),
            "changed_release_dates": changed_dates,
            "total_titles": len(titles) + len(new_titles),
            "catalog_size": len(catalog),
            "excluded": len(excluded),
            "not_added_yet": len(catalog) - len(titles) - len(excluded) - len(new_titles),
        },
    )


if __name__ == "__main__":
    main()
