import argparse
from collections import Counter
from datetime import date, datetime, timedelta

from aws_lambda_powertools import Logger

from switch2db.data_store import (
    load_skus,
    load_store_snapshot,
    load_titles,
    require_valid,
    write_store_snapshot,
)
from switch2db.nintendo_store import (
    collect_store_dates,
    diff_snapshots,
    fetch_eu_entries,
    fetch_jp_entries,
    fetch_na_entries,
    find_sku_date_findings,
    find_title_date_findings,
    match_entries_to_titles,
)
from switch2db.paths import DATA_DIR

logger = Logger(service="switch2db-check-store-dates")


def parse_args() -> argparse.Namespace:
    """Define and parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download the Switch 2 games of the Nintendo EU, NA and JP stores, list what changed "
        "since the last saved snapshot and the dates that do not agree with titles.yaml and skus.yaml."
    )
    parser.add_argument(
        "--days", type=int, required=True, help="Compare only dates from this many days ago onwards"
    )
    parser.add_argument(
        "--save", action="store_true", help="Save the downloaded stores as the snapshot for the next run"
    )
    args = parser.parse_args()
    if args.days <= 0:
        parser.error("--days must be greater than 0")
    return args


def main() -> None:
    """Compare the Nintendo stores against the previous snapshot and against the data, and log it. Only
    writes the local snapshot (with --save), never the data files."""
    args = parse_args()
    since = date.today() - timedelta(days=args.days)
    titles = require_valid(load_titles(DATA_DIR / "titles.yaml"), "titles.yaml")
    skus = require_valid(load_skus(DATA_DIR / "skus.yaml"), "skus.yaml")
    snapshot_path = DATA_DIR / "nintendo_store_catalog.yaml"
    previous = load_store_snapshot(snapshot_path)
    previous_date = (
        datetime.fromtimestamp(snapshot_path.stat().st_mtime).date().isoformat() if previous else None
    )

    entries = fetch_eu_entries() + fetch_na_entries() + fetch_jp_entries()
    title_ids = match_entries_to_titles(entries, titles)
    store_dates = collect_store_dates(entries, title_ids)
    changes = diff_snapshots(previous, entries, title_ids) if previous else []
    if args.save:
        write_store_snapshot(snapshot_path, entries)

    logger.info(
        "Store dates",
        extra={
            "since": since.isoformat(),
            "previous_snapshot": previous_date,
            "saved": args.save,
            "store_games": Counter(entry.region.value for entry in entries),
            "matched_titles": len(set(title_ids.values())),
            "changes": [change.model_dump(mode="json") for change in changes],
            "title_findings": [
                finding.model_dump(mode="json")
                for finding in find_title_date_findings(titles, store_dates, since, date.today())
            ],
            "sku_findings": [
                finding.model_dump(mode="json")
                for finding in find_sku_date_findings(skus, store_dates, since)
            ],
        },
    )


if __name__ == "__main__":
    main()
