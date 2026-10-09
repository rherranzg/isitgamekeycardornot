from datetime import UTC, datetime

import pytest
import requests
from pytest_mock import MockerFixture

from switch2db.models import Title
from switch2db.news import (
    Feed,
    NewsItem,
    build_news_candidates,
    build_page_url,
    collect_feed,
    find_topics,
    match_titles,
    mentions_switch_2,
    parse_feed,
)

PAGED_FEED = Feed(name="Example News", url="https://news.example.com/feed/", paginated=True)
SINGLE_PAGE_FEED = Feed(name="Example News", url="https://news.example.com/feed/", paginated=False)


def build_news_item(headline: str, text: str, published: datetime | None = None) -> NewsItem:
    """News item with the given headline and text."""
    return NewsItem(
        source="Example News",
        headline=headline,
        url=f"https://news.example.com/{len(text)}",
        published=published or datetime(2026, 10, 8, tzinfo=UTC),
        text=text,
    )


@pytest.mark.parametrize(
    "page,expected",
    [
        (1, "https://news.example.com/feed/"),
        (3, "https://news.example.com/feed/?paged=3"),
    ],
)
def test_build_page_url_success(page: int, expected: str) -> None:
    assert build_page_url(PAGED_FEED, page) == expected


def test_build_page_url_appends_to_existing_query() -> None:
    feed = Feed(name="Example", url="https://news.example.com/?feed=rss2", paginated=True)

    assert build_page_url(feed, 2) == "https://news.example.com/?feed=rss2&paged=2"


def test_parse_feed_success(rss_feed: str) -> None:
    items = parse_feed(rss_feed, "Example News")

    assert [item.url for item in items] == [
        "https://news.example.com/example-game-physical",
        "https://news.example.com/other-game-review",
    ]
    assert items[0].headline == "Example Game & friends get a physical release on Switch 2"
    assert items[0].published == datetime(2026, 10, 8, 10, tzinfo=UTC)
    assert "Switch 2" in items[0].text
    assert "game-key card" in items[0].text
    assert "Pre-orders open now." in items[0].text


def test_parse_feed_takes_dates_without_time_zone_as_utc(rss_feed: str) -> None:
    items = parse_feed(rss_feed, "Example News")

    assert items[1].published == datetime(2026, 10, 5, 10, tzinfo=UTC)


def test_collect_feed_pages_until_older_than_since(mocker: MockerFixture, rss_feed: str) -> None:
    mocker.patch("switch2db.news.time.sleep")
    mock_fetch = mocker.patch("switch2db.news.fetch_page", side_effect=[rss_feed, rss_feed])

    items, coverage = collect_feed(PAGED_FEED, datetime(2026, 10, 6, tzinfo=UTC))

    assert [item.url for item in items] == ["https://news.example.com/example-game-physical"]
    assert coverage.covers_window is True
    assert coverage.oldest == datetime(2026, 10, 5, 10, tzinfo=UTC)
    mock_fetch.assert_called_once_with("https://news.example.com/feed/")


def test_collect_feed_reads_next_page_while_inside_window(mocker: MockerFixture, rss_feed: str) -> None:
    mocker.patch("switch2db.news.time.sleep")
    mock_fetch = mocker.patch("switch2db.news.fetch_page", side_effect=[rss_feed, "<rss><channel/></rss>"])

    items, coverage = collect_feed(PAGED_FEED, datetime(2026, 10, 1, tzinfo=UTC))

    assert len(items) == 2
    assert coverage.covers_window is False
    assert mock_fetch.call_count == 2


def test_collect_feed_stops_after_first_page_when_not_paginated(mocker: MockerFixture, rss_feed: str) -> None:
    mock_fetch = mocker.patch("switch2db.news.fetch_page", return_value=rss_feed)

    _, coverage = collect_feed(SINGLE_PAGE_FEED, datetime(2026, 10, 1, tzinfo=UTC))

    assert coverage.covers_window is False
    mock_fetch.assert_called_once()


def test_collect_feed_reports_error_without_raising(mocker: MockerFixture) -> None:
    mocker.patch("switch2db.news.fetch_page", side_effect=requests.HTTPError("403 Forbidden"))

    items, coverage = collect_feed(PAGED_FEED, datetime(2026, 10, 1, tzinfo=UTC))

    assert items == []
    assert coverage.error == "403 Forbidden"
    assert coverage.covers_window is False


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Coming to Nintendo Switch 2 in March", True),
        ("Ｎｉｎｔｅｎｄｏ Ｓｗｉｔｃｈ ２版", True),
        ("Nintendo Switch2", True),
        ("Coming to Switch in March", False),
    ],
)
def test_mentions_switch_2_success(text: str, expected: bool) -> None:
    assert mentions_switch_2(text) is expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("The physical edition is a game-key card", ["format"]),
        ("Example Game delayed to 2027", ["date"]),
        ("パッケージ版の発売日が決定", ["format", "date"]),
        ("Example Game review", []),
    ],
)
def test_find_topics_success(text: str, expected: list[str]) -> None:
    assert find_topics(text) == expected


def test_match_titles_drops_names_inside_longer_names() -> None:
    names = {"hollow-knight": "hollow knight", "hollow-knight-silksong": "hollow knight silksong"}

    assert match_titles("Hollow Knight: Silksong gets a physical release", names) == [
        "hollow-knight-silksong"
    ]


def test_match_titles_requires_capital_letter_for_one_word_names() -> None:
    names = {"stray": "stray", "dispatch": "dispatch"}

    assert match_titles("A stray cat reviews Dispatch", names) == ["dispatch"]


def test_match_titles_returns_empty_list_without_matches() -> None:
    assert match_titles("Nothing to see here", {"example-game": "example game"}) == []


def test_build_news_candidates_success(title: Title) -> None:
    item = build_news_item(
        "Example Game physical edition announced", "Example Game physical edition announced | Switch 2"
    )

    candidates, unmatched = build_news_candidates([item], [title])

    assert [(candidate.title_id, candidate.topics, candidate.in_headline) for candidate in candidates] == [
        ("example-game", ["format"], True)
    ]
    assert unmatched == []


def test_build_news_candidates_keeps_box_news_without_known_title(title: Title) -> None:
    item = build_news_item("新作のパッケージ版", "新作のパッケージ版 | Nintendo Switch 2")

    candidates, unmatched = build_news_candidates([item], [title])

    assert candidates == []
    assert [news.headline for news in unmatched] == ["新作のパッケージ版"]


def test_build_news_candidates_skips_news_without_switch_2_or_topic(title: Title) -> None:
    items = [
        build_news_item("Example Game physical edition", "Example Game physical edition | PS5"),
        build_news_item("Example Game review", "Example Game review | Switch 2"),
    ]

    assert build_news_candidates(items, [title]) == ([], [])
