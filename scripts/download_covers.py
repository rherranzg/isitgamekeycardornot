import argparse
import random
import sys
import time
from collections import Counter
from datetime import date

import requests
from aws_lambda_powertools import Logger

from switch2db.covers import CoverResult, fetch_cover, merge_covers, select_cover_skus
from switch2db.data_store import load_covers, load_skus, load_titles, require_valid, write_covers
from switch2db.models import Cover, Sku
from switch2db.paths import COVERS_DIR, DATA_DIR

# Pause between SKUs: each one is two or three requests to the same store.
PAUSE_SECONDS = 1.0

logger = Logger(service="switch2db-download-covers")


def parse_args() -> argparse.Namespace:
    """Define and parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download the European box front of the standard SKUs to docs/covers/ and record its "
        "source in data/covers.yaml. Without arguments, every SKU that has no cover yet."
    )
    parser.add_argument("--titles", nargs="+", metavar="TITLE_ID", help="Only the SKUs of these titles")
    parser.add_argument("--random", type=int, metavar="N", help="Only N SKUs picked at random")
    parser.add_argument("--refresh", action="store_true", help="Download again the SKUs that have a cover")
    args = parser.parse_args()
    if args.random is not None and args.random <= 0:
        parser.error("--random must be greater than 0")
    return args


def narrow_skus(skus: list[Sku], title_ids: list[str] | None, sample_size: int | None) -> list[Sku]:
    """Keep the SKUs of the given titles and, if asked, a random sample of them."""
    chosen = [sku for sku in skus if title_ids is None or sku.title_id in title_ids]
    if sample_size is not None and sample_size < len(chosen):
        return random.sample(chosen, sample_size)
    return chosen


def fetch_covers(skus: list[Sku], names: dict[str, str]) -> tuple[list[CoverResult], list[Cover], bool]:
    """Look for the box of each SKU; stops at the first network error (usually the store blocking)."""
    results: list[CoverResult] = []
    covers: list[Cover] = []
    for index, sku in enumerate(skus):
        if index:
            time.sleep(PAUSE_SECONDS)
        try:
            result, cover = fetch_cover(sku, names[sku.title_id], COVERS_DIR, date.today())
        except requests.RequestException as error:
            logger.error("Request failed, stopping", extra={"sku_id": sku.sku_id, "error": str(error)})
            return results, covers, False
        results.append(result)
        if cover is not None:
            covers.append(cover)
    return results, covers, True


def main() -> int:
    """Download the missing box fronts and rewrite data/covers.yaml with what was stored."""
    args = parse_args()
    titles = require_valid(load_titles(DATA_DIR / "titles.yaml"), "titles.yaml")
    skus = require_valid(load_skus(DATA_DIR / "skus.yaml"), "skus.yaml")
    covers_path = DATA_DIR / "covers.yaml"
    existing = require_valid(load_covers(covers_path), "covers.yaml")

    pending = narrow_skus(select_cover_skus(skus, existing, args.refresh), args.titles, args.random)
    names = {title.title_id: title.name for title in titles}
    results, new_covers, finished = fetch_covers(pending, names)
    write_covers(covers_path, merge_covers(existing, new_covers))

    logger.info(
        "Covers",
        extra={
            "looked_for": len(results),
            "outcomes": Counter(result.outcome.value for result in results),
            "results": [result.model_dump(mode="json") for result in results],
            "finished": finished,
        },
    )
    return 0 if finished else 1


if __name__ == "__main__":
    sys.exit(main())
