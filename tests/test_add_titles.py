from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
import yaml
from pytest_mock import MockerFixture

from scripts.add_titles import main
from switch2db.data_store import load_titles

WriteYaml = Callable[[str, Sequence[object]], Path]


def catalog_row(igdb_id: int, name: str, release_date: str | None = None) -> dict[str, object]:
    """igdb_catalog.yaml row as written by download_igdb_catalog."""
    return {
        "igdb_id": igdb_id,
        "name": name,
        "game_type": "Main Game",
        "release_date": release_date,
        "publishers": "Example Publisher",
    }


def read_titles(tmp_path: Path) -> list[dict[str, object]]:
    """Return the validated titles.yaml rows as dicts."""
    titles, errors = load_titles(tmp_path / "titles.yaml")
    assert errors == []
    return [title.model_dump(mode="json") for title in titles]


def test_main_adds_the_requested_number_of_new_titles(
    mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml
) -> None:
    mocker.patch("scripts.add_titles.DATA_DIR", tmp_path)
    mocker.patch("sys.argv", ["add_titles", "--count", "2"])
    write_yaml(
        "igdb_catalog.yaml", [catalog_row(1, "Alpha"), catalog_row(2, "Beta"), catalog_row(3, "Gamma")]
    )
    write_yaml("titles.yaml", [])
    write_yaml("excluded_titles.yaml", [])

    main()

    assert [row["title_id"] for row in read_titles(tmp_path)] == ["alpha", "beta"]
    assert {row["status"] for row in read_titles(tmp_path)} == {"new"}


def test_main_keeps_the_existing_titles_and_their_status(
    mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml, title_row: dict[str, object]
) -> None:
    mocker.patch("scripts.add_titles.DATA_DIR", tmp_path)
    mocker.patch("sys.argv", ["add_titles", "--all"])
    write_yaml("igdb_catalog.yaml", [catalog_row(12345, "Example Game"), catalog_row(2, "Beta")])
    write_yaml("titles.yaml", [title_row])
    write_yaml("excluded_titles.yaml", [])

    main()

    rows = read_titles(tmp_path)
    assert [row["title_id"] for row in rows] == ["example-game", "beta"]
    assert rows[0]["status"] == "pending"


def test_main_requires_count_or_all(mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml) -> None:
    mocker.patch("scripts.add_titles.DATA_DIR", tmp_path)
    mocker.patch("sys.argv", ["add_titles"])

    with pytest.raises(SystemExit):
        main()


def test_main_writes_the_generated_header(
    mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml
) -> None:
    mocker.patch("scripts.add_titles.DATA_DIR", tmp_path)
    mocker.patch("sys.argv", ["add_titles", "--count", "1"])
    write_yaml("igdb_catalog.yaml", [catalog_row(1, "Alpha")])
    write_yaml("titles.yaml", [])
    write_yaml("excluded_titles.yaml", [])

    main()

    assert (tmp_path / "titles.yaml").read_text(encoding="utf-8").startswith("# Known Switch 2 games")


def test_main_rejects_a_count_that_is_not_positive(
    mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml
) -> None:
    mocker.patch("scripts.add_titles.DATA_DIR", tmp_path)
    mocker.patch("sys.argv", ["add_titles", "--count", "0"])

    with pytest.raises(SystemExit):
        main()


def test_main_fails_when_titles_yaml_is_invalid(
    mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml
) -> None:
    mocker.patch("scripts.add_titles.DATA_DIR", tmp_path)
    mocker.patch("sys.argv", ["add_titles", "--all"])
    write_yaml("igdb_catalog.yaml", [catalog_row(1, "Alpha")])
    write_yaml("titles.yaml", [{"title_id": "example-game"}])
    write_yaml("excluded_titles.yaml", [])

    with pytest.raises(ValueError, match="titles.yaml has 1 errors"):
        main()


def test_main_leaves_the_file_untouched_when_there_is_nothing_to_add(
    mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml, title_row: dict[str, object]
) -> None:
    mocker.patch("scripts.add_titles.DATA_DIR", tmp_path)
    mocker.patch("sys.argv", ["add_titles", "--all"])
    write_yaml("igdb_catalog.yaml", [catalog_row(12345, "Example Game")])
    path = write_yaml("titles.yaml", [title_row])
    write_yaml("excluded_titles.yaml", [])
    before = yaml.safe_load(path.read_text(encoding="utf-8"))

    main()

    assert yaml.safe_load(path.read_text(encoding="utf-8")) == before


def test_main_skips_the_excluded_games(mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml) -> None:
    mocker.patch("scripts.add_titles.DATA_DIR", tmp_path)
    mocker.patch("sys.argv", ["add_titles", "--all"])
    write_yaml("igdb_catalog.yaml", [catalog_row(1, "Alpha"), catalog_row(2, "Beta")])
    write_yaml("titles.yaml", [])
    write_yaml(
        "excluded_titles.yaml", [{"igdb_id": 1, "name": "Alpha", "reason": "Solo en una recopilación"}]
    )

    main()

    assert [row["title_id"] for row in read_titles(tmp_path)] == ["beta"]


def test_main_dates_only_refreshes_dates_without_adding_titles(
    mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml, title_row: dict[str, object]
) -> None:
    mocker.patch("scripts.add_titles.DATA_DIR", tmp_path)
    mocker.patch("sys.argv", ["add_titles", "--dates-only"])
    write_yaml(
        "igdb_catalog.yaml",
        [catalog_row(12345, "Example Game", release_date="2027"), catalog_row(2, "Beta")],
    )
    write_yaml("titles.yaml", [title_row])
    write_yaml("excluded_titles.yaml", [])

    main()

    rows = read_titles(tmp_path)
    assert [row["title_id"] for row in rows] == ["example-game"]
    assert rows[0]["release_date"] == "2027"
