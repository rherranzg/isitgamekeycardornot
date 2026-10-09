import re
import time
import unicodedata
import xml.etree.ElementTree as ElementTree
from collections.abc import Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import requests
from pydantic import BaseModel, Field

from switch2db.models import Title
from switch2db.names import normalize_name
from switch2db.quote import REQUEST_TIMEOUT_SECONDS, USER_AGENT, html_to_text
from switch2db.slug import strip_accents

MAX_PAGES_PER_FEED = 40
PAGE_PAUSE_SECONDS = 0.5
CONTENT_NAMESPACE = "{http://purl.org/rss/1.0/modules/content/}encoded"
# Compared after NFKC, so full-width "Ｓｗｉｔｃｈ ２" also counts.
SWITCH_2_MENTION = re.compile(r"switch\s*2|スイッチ\s*2|스위치\s*2", re.IGNORECASE)
TOPIC_PATTERNS = {
    "format": re.compile(
        r"physical|retail|boxed|cartridge|game[- ]?card|key[- ]?card|limited run|collector'?s edition|"
        r"pre-?order|パッケージ|キーカード|ゲームカード|패키지|실물",
        re.IGNORECASE,
    ),
    "date": re.compile(
        r"delay|postpone|release date|launch|releas(?:e|es|ed|ing) (?:on|in)|coming (?:on|in)|"
        r"発売日|延期|発売決定|출시",
        re.IGNORECASE,
    ),
}
# Only these topics are reported for news that names no known title (Japanese names, renamed games).
UNMATCHED_TOPICS = frozenset({"format"})


class Feed(BaseModel):
    """News feed (RSS) read to find changes in Switch 2 boxes."""

    name: str = Field(..., description="Site name, as shown in the report")
    url: str = Field(..., description="RSS feed URL")
    paginated: bool = Field(..., description="True if older pages are reachable with ?paged=N (WordPress)")


FEEDS = (
    Feed(name="Nintendo Everything", url="https://nintendoeverything.com/feed/", paginated=True),
    Feed(name="Nintendo Life", url="https://www.nintendolife.com/feeds/latest", paginated=False),
    Feed(name="GoNintendo", url="https://www.gonintendo.com/feeds/all", paginated=False),
    Feed(name="Gematsu", url="https://www.gematsu.com/c/switch-2/feed", paginated=True),
    Feed(name="Perfectly Nintendo", url="https://www.perfectly-nintendo.com/feed/", paginated=True),
    Feed(name="Nintendo Insider", url="https://www.nintendo-insider.com/feed/", paginated=True),
    Feed(name="My Nintendo News", url="https://mynintendonews.com/feed/", paginated=True),
    Feed(name="Siliconera", url="https://www.siliconera.com/feed/", paginated=True),
    Feed(name="VGC", url="https://www.videogameschronicle.com/feed/", paginated=True),
    Feed(name="AUTOMATON", url="https://automaton-media.com/feed/", paginated=True),
)


class NewsItem(BaseModel):
    """One news item of a feed, with its text reduced to plain words."""

    source: str = Field(..., description="Name of the feed it comes from")
    headline: str = Field(..., description="Headline of the news item")
    url: str = Field(..., description="Link to the news item")
    published: datetime = Field(..., description="Publication date, with time zone")
    text: str = Field(..., description="Headline, categories, summary and body (if the feed has it) as text")


class FeedCoverage(BaseModel):
    """How far back a feed was read, so the gaps can be covered with web searches."""

    source: str = Field(..., description="Feed name")
    items_in_window: int = Field(..., description="News items published inside the window")
    oldest: datetime | None = Field(None, description="Oldest news item read")
    covers_window: bool = Field(..., description="True if the feed reached the start of the window")
    error: str | None = Field(None, description="Why the feed could not be read, if it failed")


class NewsCandidate(BaseModel):
    """News item that names a known title and talks about its box or its date."""

    title_id: str = Field(..., description="Title the news item names")
    name: str = Field(..., description="Title name")
    source: str = Field(..., description="Feed name")
    headline: str = Field(..., description="Headline")
    url: str = Field(..., description="Link to the news item")
    published: datetime = Field(..., description="Publication date")
    topics: list[str] = Field(..., description="What it talks about: format (box) and/or date")
    in_headline: bool = Field(..., description="True if the title is named in the headline itself")


class UnmatchedNews(BaseModel):
    """News item about Switch 2 boxes that names no known title (Japanese name, new game...)."""

    source: str = Field(..., description="Feed name")
    headline: str = Field(..., description="Headline")
    url: str = Field(..., description="Link to the news item")
    published: datetime = Field(..., description="Publication date")


def build_page_url(feed: Feed, page: int) -> str:
    """Return the URL of a feed page; WordPress pages older items with ?paged=N."""
    if page == 1:
        return feed.url
    separator = "&" if "?" in feed.url else "?"
    return f"{feed.url}{separator}paged={page}"


def read_element_text(element: ElementTree.Element, tag: str) -> str:
    """Return the text of a child element, or an empty string if it is missing."""
    child = element.find(tag)
    return (child.text or "").strip() if child is not None else ""


def parse_published(text: str) -> datetime:
    """Parse an RSS date; a date without time zone ("-0000") is taken as UTC."""
    published = parsedate_to_datetime(text)
    return published if published.tzinfo is not None else published.replace(tzinfo=UTC)


def parse_feed(xml_text: str, source: str) -> list[NewsItem]:
    """Read the items of an RSS feed; items without link or date are skipped."""
    root = ElementTree.fromstring(xml_text)
    items: list[NewsItem] = []
    for element in root.iter("item"):
        url = read_element_text(element, "link")
        published_text = read_element_text(element, "pubDate")
        if not url or not published_text:
            continue
        headline = html_to_text(read_element_text(element, "title"))
        categories = [(category.text or "").strip() for category in element.findall("category")]
        body = " ".join(
            html_to_text(read_element_text(element, tag)) for tag in ("description", CONTENT_NAMESPACE)
        )
        items.append(
            NewsItem(
                source=source,
                headline=headline,
                url=url,
                published=parse_published(published_text),
                text=" | ".join([headline, *categories, body]),
            )
        )
    return items


def fetch_page(url: str) -> str:
    """Download a feed page with the project's User-Agent."""
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text


def collect_feed(feed: Feed, since: datetime) -> tuple[list[NewsItem], FeedCoverage]:
    """Read a feed page by page until the news items are older than `since` (or there are no more pages).
    A failing feed does not stop the others: its error goes into the coverage."""
    items: dict[str, NewsItem] = {}
    oldest: datetime | None = None
    error: str | None = None
    for page in range(1, MAX_PAGES_PER_FEED + 1):
        try:
            page_items = parse_feed(fetch_page(build_page_url(feed, page)), feed.name)
        except (requests.RequestException, ElementTree.ParseError) as page_error:
            error = str(page_error)
            break
        if not page_items:
            break
        for item in page_items:
            items.setdefault(item.url, item)
        oldest = min(item.published for item in items.values())
        if not feed.paginated or oldest < since:
            break
        time.sleep(PAGE_PAUSE_SECONDS)
    in_window = [item for item in items.values() if item.published >= since]
    coverage = FeedCoverage(
        source=feed.name,
        items_in_window=len(in_window),
        oldest=oldest,
        covers_window=oldest is not None and oldest < since,
        error=error,
    )
    return in_window, coverage


def mentions_switch_2(text: str) -> bool:
    """True if the text names the Switch 2 (also in Japanese, Korean or full-width characters)."""
    return SWITCH_2_MENTION.search(unicodedata.normalize("NFKC", text)) is not None


def find_topics(text: str) -> list[str]:
    """Return what the text talks about: the box (format) and/or the release date (date)."""
    return [topic for topic, pattern in TOPIC_PATTERNS.items() if pattern.search(text)]


def is_capitalized_word_in(word: str, text: str) -> bool:
    """True if the word appears as a whole word starting with a capital letter or digit: a game called
    "Stray" or "Dispatch" should not match every lowercase "stray" or "dispatch" in the news."""
    pattern = re.compile(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", re.IGNORECASE)
    return any(not match.group(0)[0].islower() for match in pattern.finditer(text))


def name_appears_in(normalized_name: str, raw_text: str, normalized_text: str) -> bool:
    """True if the name appears as whole words in the text; one-word names need a capital letter."""
    if " " not in normalized_name:
        return is_capitalized_word_in(normalized_name, strip_accents(raw_text))
    return f" {normalized_name} " in normalized_text


def match_titles(text: str, names_by_title_id: dict[str, str]) -> list[str]:
    """Return the titles named in the text. A name inside a longer matched name is dropped ("Hollow
    Knight" inside "Hollow Knight Silksong")."""
    normalized_text = f" {normalize_name(text)} "
    matched = {
        title_id: name
        for title_id, name in names_by_title_id.items()
        if name and name_appears_in(name, text, normalized_text)
    }
    return [
        title_id
        for title_id, name in matched.items()
        if not any(other != name and f" {name} " in f" {other} " for other in matched.values())
    ]


def build_news_candidates(
    items: Sequence[NewsItem], titles: Sequence[Title]
) -> tuple[list[NewsCandidate], list[UnmatchedNews]]:
    """Keep the Switch 2 news items that talk about a box or a date; split them into those that name a
    known title and those about boxes that name none."""
    names_by_title_id = {title.title_id: normalize_name(title.name) for title in titles}
    titles_by_id = {title.title_id: title for title in titles}
    candidates: list[NewsCandidate] = []
    unmatched: list[UnmatchedNews] = []
    for item in items:
        topics = find_topics(item.text)
        if not topics or not mentions_switch_2(item.text):
            continue
        title_ids = match_titles(item.text, names_by_title_id)
        headline_title_ids = set(match_titles(item.headline, names_by_title_id))
        candidates.extend(
            NewsCandidate(
                title_id=title_id,
                name=titles_by_id[title_id].name,
                source=item.source,
                headline=item.headline,
                url=item.url,
                published=item.published,
                topics=topics,
                in_headline=title_id in headline_title_ids,
            )
            for title_id in title_ids
        )
        if not title_ids and UNMATCHED_TOPICS.intersection(topics):
            unmatched.append(
                UnmatchedNews(
                    source=item.source, headline=item.headline, url=item.url, published=item.published
                )
            )
    candidates.sort(key=lambda candidate: (candidate.title_id, candidate.published))
    unmatched.sort(key=lambda news: news.published)
    return candidates, unmatched
