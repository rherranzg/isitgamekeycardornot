import argparse
from datetime import UTC, datetime, timedelta

from aws_lambda_powertools import Logger

from switch2db.data_store import load_titles, require_valid
from switch2db.news import FEEDS, NewsItem, build_news_candidates, collect_feed
from switch2db.paths import DATA_DIR

logger = Logger(service="switch2db-news-candidates")


def parse_args() -> argparse.Namespace:
    """Define and parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Read the RSS feeds of the news sites and list the Switch 2 news items of the last days "
        "that talk about the box or the date of a known title."
    )
    parser.add_argument("--days", type=int, required=True, help="How many days back to read")
    args = parser.parse_args()
    if args.days <= 0:
        parser.error("--days must be greater than 0")
    return args


def main() -> None:
    """Read the feeds and log the news candidates, the box news that names no known title and how far
    back each feed reached. Does not change any data file."""
    args = parse_args()
    since = datetime.now(UTC) - timedelta(days=args.days)
    titles = require_valid(load_titles(DATA_DIR / "titles.yaml"), "titles.yaml")

    items: list[NewsItem] = []
    coverage = []
    for feed in FEEDS:
        feed_items, feed_coverage = collect_feed(feed, since)
        items.extend(feed_items)
        coverage.append(feed_coverage)
    candidates, unmatched = build_news_candidates(items, titles)
    logger.info(
        "News candidates",
        extra={
            "since": since.isoformat(),
            "coverage": [entry.model_dump(mode="json") for entry in coverage],
            "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
            "unmatched": [news.model_dump(mode="json") for news in unmatched],
        },
    )


if __name__ == "__main__":
    main()
