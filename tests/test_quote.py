from pathlib import Path

from switch2db.quote import find_quotes, html_to_text, read_source


def test_html_to_text_drops_scripts_and_separates_blocks() -> None:
    page = "<script>var x = 'Game-Key Card';</script><dt>Physical Release</dt><dd>Game-Key Card</dd>"

    assert html_to_text(page) == "Physical Release | Game-Key Card"


def test_html_to_text_unescapes_entities() -> None:
    assert html_to_text("<li>Hitman &#8211; Signature Edition</li>") == "Hitman – Signature Edition"


def test_find_quotes_returns_context_around_each_match() -> None:
    text = "0123456789Game Card0123456789"

    assert find_quotes(text, "game card", context=3, max_quotes=5) == ["789Game Card012"]


def test_find_quotes_skips_duplicates_and_stops_at_max() -> None:
    text = "key card, key card, key card"

    assert find_quotes(text, "key card", context=0, max_quotes=5) == ["key card"]
    assert find_quotes("cart one, card two", "car[dt]", context=0, max_quotes=1) == ["cart"]


def test_find_quotes_returns_empty_list_without_matches() -> None:
    assert find_quotes("nothing here", "cartridge", context=50, max_quotes=5) == []


def test_read_source_reads_local_files(tmp_path: Path) -> None:
    page = tmp_path / "list.html"
    page.write_text("<li>1000xRESIST</li>", encoding="utf-8")

    assert read_source(str(page)) == "<li>1000xRESIST</li>"
