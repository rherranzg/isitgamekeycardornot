import argparse

from aws_lambda_powertools import Logger

from switch2db.data_store import load_skus, load_titles, require_valid
from switch2db.paths import DATA_DIR
from switch2db.worklist import WorkQueue, build_work_queue

logger = Logger(service="switch2db-next-work")


def parse_args() -> argparse.Namespace:
    """Define and parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Show what is left to review, research or accept, based on the stored data."
    )
    parser.add_argument("--limit", type=int, help="Trim each list to N items to work in batches")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than 0")
    return args


def truncate_queue(queue: WorkQueue, limit: int | None) -> WorkQueue:
    """Trim each queue list to its first `limit` items (None = no trimming)."""
    if limit is None:
        return queue
    return WorkQueue(
        titles_to_review=queue.titles_to_review[:limit],
        titles_to_research=queue.titles_to_research[:limit],
        titles_missing_regions=dict(list(queue.titles_missing_regions.items())[:limit]),
        new_skus=queue.new_skus[:limit],
        skus_without_source=queue.skus_without_source[:limit],
        skus_to_refresh=queue.skus_to_refresh[:limit],
    )


def main() -> None:
    """Compute and log the pending work queue. Does not query any external source."""
    args = parse_args()
    titles = require_valid(load_titles(DATA_DIR / "titles.yaml"), "titles.yaml")
    skus = require_valid(load_skus(DATA_DIR / "skus.yaml"), "skus.yaml")

    queue = build_work_queue(titles, skus)
    logger.info("Pending work", extra=truncate_queue(queue, args.limit).model_dump())


if __name__ == "__main__":
    main()
