import argparse

from aws_lambda_powertools import Logger

from switch2db.quote import find_quotes, html_to_text, read_source

logger = Logger(service="switch2db-fetch-quote")


def parse_args() -> argparse.Namespace:
    """Define and parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Download a page (or read an already downloaded file) and show only the snippets that "
            "match the pattern, to quote without dumping the whole HTML."
        )
    )
    parser.add_argument("source", help="URL or path to a local file")
    parser.add_argument("pattern", help="Case-insensitive regular expression (e.g. 'key.?card|cart')")
    parser.add_argument("--context", type=int, default=120, help="Characters around each match")
    parser.add_argument("--max", type=int, default=5, dest="max_quotes", help="Maximum number of snippets")
    parser.add_argument("--raw", action="store_true", help="Do not convert HTML to text (JSON, plain text)")
    args = parser.parse_args()
    if args.context < 0 or args.max_quotes <= 0:
        parser.error("--context cannot be negative and --max must be greater than 0")
    return args


def main() -> None:
    """Show the quotable snippets of a source."""
    args = parse_args()
    content = read_source(args.source)
    text = content if args.raw else html_to_text(content)
    quotes = find_quotes(text, args.pattern, args.context, args.max_quotes)
    logger.info(
        "Snippets found",
        extra={"source": args.source, "pattern": args.pattern, "match_count": len(quotes), "quotes": quotes},
    )


if __name__ == "__main__":
    main()
