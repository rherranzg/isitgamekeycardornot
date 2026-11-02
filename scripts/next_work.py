import argparse
from datetime import date, timedelta

from aws_lambda_powertools import Logger

from switch2db.data_store import load_physical_releases, load_skus, load_titles, require_valid
from switch2db.paths import DATA_DIR
from switch2db.worklist import WorkQueue, build_work_queue, drop_checked_since, list_upcoming_titles

logger = Logger(service="switch2db-next-work")


def parse_args() -> argparse.Namespace:
    """Define and parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Show what is left to research, refresh or complete, based on the stored data."
    )
    parser.add_argument("--limit", type=int, help="Trim each list to N items to work in batches")
    parser.add_argument(
        "--upcoming",
        type=int,
        help="Instead of the queue, list the next N titles to come out (any status), soonest first",
    )
    parser.add_argument(
        "--skip-checked-days",
        type=int,
        help="With --upcoming, drop the titles checked in the last N days, without replacing them",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than 0")
    if args.upcoming is not None and args.upcoming <= 0:
        parser.error("--upcoming must be greater than 0")
    if args.skip_checked_days is not None and (args.upcoming is None or args.skip_checked_days <= 0):
        parser.error("--skip-checked-days needs --upcoming and must be greater than 0")
    return args


def truncate_queue(queue: WorkQueue, limit: int | None) -> WorkQueue:
    """Trim each queue list to its first `limit` items (None = no trimming)."""
    if limit is None:
        return queue
    return WorkQueue(
        titles_to_research=queue.titles_to_research[:limit],
        titles_to_refresh=queue.titles_to_refresh[:limit],
        titles_to_complete=queue.titles_to_complete[:limit],
        titles_missing_regions=dict(list(queue.titles_missing_regions.items())[:limit]),
        skus_without_source=queue.skus_without_source[:limit],
    )


def main() -> None:
    """Compute and log the pending work queue (or, with --upcoming, the next titles to come out).
    Does not query any external source."""
    args = parse_args()
    titles = require_valid(load_titles(DATA_DIR / "titles.yaml"), "titles.yaml")
    if args.upcoming is not None:
        upcoming = list_upcoming_titles(titles, date.today(), args.upcoming)
        if args.skip_checked_days is not None:
            upcoming = drop_checked_since(upcoming, date.today() - timedelta(days=args.skip_checked_days))
        logger.info(
            "Upcoming titles",
            extra={
                "upcoming_titles": [
                    title.model_dump(
                        mode="json", include={"title_id", "release_date", "status", "last_checked_at"}
                    )
                    for title in upcoming
                ]
            },
        )
        return
    skus = require_valid(load_skus(DATA_DIR / "skus.yaml"), "skus.yaml")
    releases = require_valid(
        load_physical_releases(DATA_DIR / "physical_release.yaml"), "physical_release.yaml"
    )

    queue = build_work_queue(titles, skus, releases)
    logger.info("Pending work", extra=truncate_queue(queue, args.limit).model_dump())


if __name__ == "__main__":
    main()
