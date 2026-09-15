from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from switch2db.catalog import CatalogEntry
from switch2db.data_store import (
    CATALOG_HEADER,
    TITLES_HEADER,
    append_title_seeds,
    describe_row,
    format_validation_error,
    load_skus,
    load_title_seeds,
    load_titles,
    parse_rows,
    read_yaml_rows,
    write_catalog,
    write_titles,
)
from switch2db.models import Sku, Title, TitleSeed

WriteYaml = Callable[[str, Sequence[object]], Path]


def test_read_yaml_rows_success(write_yaml: WriteYaml) -> None:
    path = write_yaml("rows.yaml", [{"a": 1}])

    assert read_yaml_rows(path) == [{"a": 1}]


@pytest.mark.parametrize("content", ["# solo comentarios\n", "a: 1\n"])
def test_read_yaml_rows_raises_when_root_is_not_a_list(tmp_path: Path, content: str) -> None:
    path = tmp_path / "rows.yaml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="debe ser una lista"):
        read_yaml_rows(path)


@pytest.mark.parametrize(
    "row,expected",
    [
        ({"sku_id": "eu-example-game-standard"}, "#3 eu-example-game-standard"),
        ({"title_id": "example-game"}, "#3 example-game"),
        ({}, "#3"),
        ("texto", "#3"),
    ],
)
def test_describe_row_success(row: object, expected: str) -> None:
    assert describe_row(row, 3) == expected


def test_format_validation_error_lists_every_field() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TitleSeed.model_validate({"title_id": "Bad Id", "igdb_id": 0})

    message = format_validation_error(exc_info.value)

    assert message.startswith("title_id: ")
    assert "; igdb_id: " in message


def test_format_validation_error_uses_message_when_error_has_no_location(sku_row: dict[str, object]) -> None:
    with pytest.raises(ValidationError) as exc_info:
        Sku.model_validate({**sku_row, "sku_id": "wrong"})

    assert format_validation_error(exc_info.value).startswith("Value error, sku_id 'wrong'")


def test_parse_rows_accumulates_errors_without_stopping(sku_row: dict[str, object]) -> None:
    rows = [sku_row, {**sku_row, "source_url": None}, "texto"]

    skus, errors = parse_rows(rows, Sku, "skus.yaml")

    assert [sku.sku_id for sku in skus] == ["eu-example-game-standard"]
    assert len(errors) == 2
    assert errors[0].startswith("skus.yaml #1 eu-example-game-standard: ")
    assert errors[1].startswith("skus.yaml #2: ")


def test_load_skus_success(write_yaml: WriteYaml, sku_row: dict[str, object]) -> None:
    skus, errors = load_skus(write_yaml("skus.yaml", [sku_row]))

    assert errors == []
    assert [sku.sku_id for sku in skus] == ["eu-example-game-standard"]


def test_load_title_seeds_returns_errors_for_invalid_rows(write_yaml: WriteYaml) -> None:
    seeds, errors = load_title_seeds(write_yaml("title_seeds.yaml", [{"title_id": "example-game"}]))

    assert seeds == []
    assert errors == ["title_seeds.yaml #0 example-game: igdb_id: Field required"]


def test_write_titles_round_trips_with_load_titles(tmp_path: Path, title: Title) -> None:
    path = tmp_path / "titles.yaml"

    write_titles(path, [title])

    assert path.read_text(encoding="utf-8").startswith(TITLES_HEADER)
    assert load_titles(path) == ([title], [])


def test_write_titles_writes_empty_list(tmp_path: Path) -> None:
    path = tmp_path / "titles.yaml"

    write_titles(path, [])

    assert load_titles(path) == ([], [])


def test_append_title_seeds_preserves_existing_content_and_appends_new_rows(tmp_path: Path) -> None:
    path = tmp_path / "title_seeds.yaml"
    original = "# comentario de curación manual\n- title_id: example-game\n  igdb_id: 1\n"
    path.write_text(original, encoding="utf-8")

    append_title_seeds(path, [TitleSeed(title_id="other-game", igdb_id=2)], "comentario auto")

    content = path.read_text(encoding="utf-8")
    assert content.startswith(original)
    assert "# comentario auto" in content
    seeds, errors = load_title_seeds(path)
    assert errors == []
    assert [seed.title_id for seed in seeds] == ["example-game", "other-game"]


def test_append_title_seeds_does_nothing_when_no_new_seeds(tmp_path: Path) -> None:
    path = tmp_path / "title_seeds.yaml"
    original = "- title_id: example-game\n  igdb_id: 1\n"
    path.write_text(original, encoding="utf-8")

    append_title_seeds(path, [], "comentario auto")

    assert path.read_text(encoding="utf-8") == original


def test_write_catalog_writes_header_and_iso_dates(tmp_path: Path) -> None:
    path = tmp_path / "igdb_catalog.yaml"
    entry = CatalogEntry(
        igdb_id=12345,
        name="Example Game",
        game_type="Main Game",
        first_release_date=date(2025, 6, 5),
        publishers="Example Publisher",
    )

    write_catalog(path, [entry])

    content = path.read_text(encoding="utf-8")
    assert content.startswith(CATALOG_HEADER)
    assert yaml.safe_load(content) == [
        {
            "igdb_id": 12345,
            "name": "Example Game",
            "game_type": "Main Game",
            "first_release_date": "2025-06-05",
            "publishers": "Example Publisher",
        }
    ]
