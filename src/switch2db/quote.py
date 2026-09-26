import html
import re
from pathlib import Path

import requests

USER_AGENT = "isitgamekeycardornot/1.0"
REQUEST_TIMEOUT_SECONDS = 30
NON_CONTENT_TAGS = re.compile(r"<(script|style|noscript|svg)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
BLOCK_TAGS = re.compile(
    r"</?(p|div|li|dd|dt|tr|td|th|h[1-6]|br|ul|ol|section|article)\b[^>]*>", re.IGNORECASE
)
ANY_TAG = re.compile(r"<[^>]+>")
WHITESPACE = re.compile(r"\s+")


def read_source(source: str) -> str:
    """Return the content of a URL (with the project's User-Agent) or of a downloaded local file."""
    if not source.startswith(("http://", "https://")):
        return Path(source).read_text(encoding="utf-8", errors="ignore")
    response = requests.get(source, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text


def html_to_text(page: str) -> str:
    """Strip scripts, styles and tags; blocks are separated by ' | ' so cells do not run together."""
    without_code = NON_CONTENT_TAGS.sub(" ", page)
    with_separators = BLOCK_TAGS.sub(" | ", without_code)
    text = html.unescape(ANY_TAG.sub(" ", with_separators))
    return re.sub(r"(\s*\|\s*)+", " | ", WHITESPACE.sub(" ", text)).strip(" |")


def find_quotes(text: str, pattern: str, context: int, max_quotes: int) -> list[str]:
    """Return distinct snippets around each match (regex, case-insensitive)."""
    quotes: list[str] = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        quote = text[max(0, match.start() - context) : match.end() + context].strip()
        if quote not in quotes:
            quotes.append(quote)
        if len(quotes) == max_quotes:
            break
    return quotes
