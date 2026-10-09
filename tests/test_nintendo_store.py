from datetime import date

import pytest
from pytest_mock import MockerFixture

from switch2db.models import Region, Sku, Title
from switch2db.nintendo_store import (
    ChangeKind,
    DateMismatch,
    StoreEntry,
    classify_title_date,
    collect_store_dates,
    diff_snapshots,
    fetch_jp_entries,
    fetch_na_entries,
    find_sku_date_findings,
    find_title_date_findings,
    match_entries_to_titles,
    parse_eu_doc,
    parse_jp_date,
    parse_jp_item,
    parse_na_hit,
    read_store_day,
)

SINCE = date(2026, 10, 2)
TODAY = date(2026, 10, 9)


def build_entry(region: Region, release_date: str | None, name: str = "Example Game") -> StoreEntry:
    """Store entry of the example game in a region."""
    return StoreEntry(region=region, product_id=f"{region}-1", name=name, release_date=release_date)


@pytest.mark.parametrize(
    "timestamp,expected",
    [
        ("2026-11-05T00:00:00Z", "2026-11-05"),
        ("2027-12-31T00:00:00.000Z", "2027"),
        ("2050-12-31T00:00:00Z", None),
        (None, None),
    ],
)
def test_read_store_day_success(timestamp: str | None, expected: str | None) -> None:
    assert read_store_day(timestamp) == expected


def test_parse_eu_doc_success(eu_store_doc: dict[str, object]) -> None:
    assert parse_eu_doc(eu_store_doc) == StoreEntry(
        region=Region.EU, product_id="2785803", name="Example Game™", release_date="2026-11-05"
    )


def test_parse_eu_doc_without_dates(eu_store_doc: dict[str, object]) -> None:
    assert parse_eu_doc({**eu_store_doc, "dates_released_dts": []}).release_date is None


def test_parse_na_hit_success(na_store_hit: dict[str, object]) -> None:
    entry = parse_na_hit(na_store_hit)

    assert (entry.region, entry.product_id, entry.release_date) == (Region.NA, "70010000095431", "2026-11-05")


def test_fetch_na_entries_pages_and_skips_upgrade_packs(
    mocker: MockerFixture, na_store_hit: dict[str, object]
) -> None:
    upgrade = {**na_store_hit, "nsuid": "2", "isUpgrade": True}
    mock_post = mocker.patch("switch2db.nintendo_store.requests.post")
    mock_post.return_value.json.side_effect = [
        {"nbHits": 2, "nbPages": 2, "hits": [na_store_hit]},
        {"nbHits": 2, "nbPages": 2, "hits": [upgrade]},
    ]

    entries = fetch_na_entries()

    assert [entry.product_id for entry in entries] == ["70010000095431"]
    assert mock_post.call_count == 2


def test_fetch_na_entries_raises_when_over_algolia_limit(mocker: MockerFixture) -> None:
    mock_post = mocker.patch("switch2db.nintendo_store.requests.post")
    mock_post.return_value.json.return_value = {"nbHits": 1001, "nbPages": 3, "hits": []}

    with pytest.raises(ValueError, match="must be split"):
        fetch_na_entries()


@pytest.mark.parametrize(
    "sdate,expected",
    [
        ("2026.11.5", "2026-11-05"),
        ("2027.春", "2027.春"),
        ("未定", None),
        (None, None),
    ],
)
def test_parse_jp_date_success(sdate: str | None, expected: str | None) -> None:
    assert parse_jp_date(sdate) == expected


@pytest.mark.parametrize(
    "sform,expected",
    [("BEE_DOWNLOADABLE", True), ("BEE_CARD", True), ("BEE_DL", False), (None, None)],
)
def test_parse_jp_item_success(
    jp_store_item: dict[str, object], sform: str | None, expected: bool | None
) -> None:
    entry = parse_jp_item({**jp_store_item, "sform": sform})

    assert entry is not None
    assert (entry.release_date, entry.has_package) == ("2027-05-20", expected)


@pytest.mark.parametrize("sform", ["DLC", "DL_DLC", "BEE_GC", "hard"])
def test_parse_jp_item_returns_none_for_non_games(jp_store_item: dict[str, object], sform: str) -> None:
    assert parse_jp_item({**jp_store_item, "sform": sform}) is None


def test_fetch_jp_entries_pages_until_total(mocker: MockerFixture, jp_store_item: dict[str, object]) -> None:
    dlc = {**jp_store_item, "id": "2", "sform": "DLC"}
    mock_get = mocker.patch("switch2db.nintendo_store.requests.get")
    mock_get.return_value.json.side_effect = [
        {"result": {"total": 2, "items": [jp_store_item]}},
        {"result": {"total": 2, "items": [dlc]}},
    ]

    entries = fetch_jp_entries()

    assert [entry.product_id for entry in entries] == ["70010000131656"]
    assert mock_get.call_count == 2


def test_match_entries_to_titles_success(title: Title) -> None:
    entries = [
        build_entry(Region.EU, "2026-11-05", "Example Game™"),
        build_entry(Region.JP, "2026-11-05", "Example Game"),
    ]

    assert match_entries_to_titles(entries, [title]) == {(Region.EU, "EU-1"): "example-game"}


def test_match_entries_to_titles_skips_ambiguous_products(title: Title) -> None:
    entries = [
        StoreEntry(region=Region.NA, product_id="1", name="Example Game", release_date=None),
        StoreEntry(region=Region.NA, product_id="2", name="Example Game - Nintendo Switch 2 Edition"),
    ]

    assert match_entries_to_titles(entries, [title]) == {}


def test_diff_snapshots_reports_new_products_dates_and_boxes() -> None:
    previous = [
        StoreEntry(region=Region.EU, product_id="1", name="Delayed", release_date="2026-10-20"),
        StoreEntry(region=Region.JP, product_id="2", name="箱", release_date="2026.冬", has_package=False),
        StoreEntry(region=Region.NA, product_id="3", name="Same", release_date="2026-10-20"),
    ]
    current = [
        StoreEntry(region=Region.EU, product_id="1", name="Delayed", release_date="2026-11-20"),
        StoreEntry(region=Region.JP, product_id="2", name="箱", release_date="2026.冬", has_package=True),
        StoreEntry(region=Region.NA, product_id="3", name="Same", release_date="2026-10-20"),
        StoreEntry(region=Region.NA, product_id="4", name="Brand New", release_date=None),
    ]

    changes = diff_snapshots(previous, current, {(Region.EU, "1"): "delayed"})

    assert [(change.kind, change.before, change.after, change.title_id) for change in changes] == [
        (ChangeKind.RELEASE_DATE, "2026-10-20", "2026-11-20", "delayed"),
        (ChangeKind.PACKAGE, False, True, None),
        (ChangeKind.NEW, None, None, None),
    ]


def test_collect_store_dates_keeps_only_days() -> None:
    entries = [build_entry(Region.EU, "2026-11-05"), build_entry(Region.NA, "2027")]
    title_ids = {(Region.EU, "EU-1"): "example-game", (Region.NA, "NA-1"): "example-game"}

    assert collect_store_dates(entries, title_ids) == {"example-game": {"EU": "2026-11-05"}}


@pytest.mark.parametrize(
    "title_date,store_dates,expected",
    [
        (None, {"EU": "2026-11-05"}, DateMismatch.MISSING),
        ("2026-Q4", {"EU": "2026-11-05"}, DateMismatch.LESS_PRECISE),
        ("2026-11-05", {"EU": "2026-11-04", "NA": "2026-11-05"}, None),
        ("2026-11-05", {"EU": "2026-11-04"}, DateMismatch.STORE_EARLIER),
        ("2026-10-20", {"EU": "2026-11-20"}, DateMismatch.STORE_LATER),
        ("2026-09-24", {"EU": "2026-10-08"}, None),
        ("2026-Q3", {"EU": "2026-08-20"}, None),
        ("2026-05-01", {"EU": "2026-05-02"}, None),
    ],
)
def test_classify_title_date_success(
    title_date: str | None, store_dates: dict[str, str], expected: DateMismatch | None
) -> None:
    assert classify_title_date(title_date, store_dates, SINCE, TODAY) == expected


def test_find_title_date_findings_success(title: Title) -> None:
    findings = find_title_date_findings(
        [title], {"example-game": {"EU": "2026-11-05"}, "other-game": {"EU": "2026-11-05"}}, SINCE, TODAY
    )

    assert [(finding.title_id, finding.reason) for finding in findings] == [
        ("example-game", DateMismatch.MISSING)
    ]


@pytest.mark.parametrize(
    "store_date,expected",
    [("2026-11-20", ["eu-example-game-standard"]), ("2026-10-01", []), ("2026-10-20", [])],
)
def test_find_sku_date_findings_reports_only_later_store_days(
    eu_key_card_sku: Sku, store_date: str, expected: list[str]
) -> None:
    sku = eu_key_card_sku.model_copy(update={"release_date": date(2026, 10, 20)})

    findings = find_sku_date_findings([sku], {"example-game": {"EU": store_date}}, SINCE)

    assert [finding.sku_id for finding in findings] == expected


def test_find_sku_date_findings_skips_undated_and_asian_skus(
    eu_key_card_sku: Sku, asia_full_cart_sku: Sku
) -> None:
    undated = eu_key_card_sku.model_copy(update={"release_date": None})
    asia = asia_full_cart_sku.model_copy(update={"release_date": date(2026, 10, 20)})

    assert find_sku_date_findings([undated, asia], {"example-game": {"EU": "2026-11-20"}}, SINCE) == []
