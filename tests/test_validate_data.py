from collections.abc import Callable, Sequence
from pathlib import Path

from pytest_mock import MockerFixture

from scripts.validate_data import main

WriteYaml = Callable[[str, Sequence[object]], Path]


def test_main_returns_zero_for_valid_data(
    mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml, sku_row: dict[str, object]
) -> None:
    mocker.patch("scripts.validate_data.DATA_DIR", tmp_path)
    write_yaml("title_seeds.yaml", [{"title_id": "example-game", "igdb_id": 12345}])
    write_yaml("titles.yaml", [])
    write_yaml("skus.yaml", [sku_row])

    assert main() == 0


def test_main_reports_titles_pending_review(
    mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml, title_row: dict[str, object]
) -> None:
    mocker.patch("scripts.validate_data.DATA_DIR", tmp_path)
    mock_logger = mocker.patch("scripts.validate_data.logger")
    reviewed_row = {**title_row, "title_id": "reviewed-game", "igdb_id": 67890, "status": "reviewed"}
    write_yaml(
        "title_seeds.yaml",
        [{"title_id": "example-game", "igdb_id": 12345}, {"title_id": "reviewed-game", "igdb_id": 67890}],
    )
    write_yaml("titles.yaml", [title_row, reviewed_row])
    write_yaml("skus.yaml", [])

    exit_code = main()

    report = mock_logger.info.call_args_list[0].kwargs["extra"]
    assert exit_code == 0
    assert report["titles_by_status"] == {"pending": 1, "reviewed": 1}
    assert report["pending_review_titles"] == ["example-game"]


def test_main_returns_one_and_logs_every_invalid_row(
    mocker: MockerFixture, tmp_path: Path, write_yaml: WriteYaml, sku_row: dict[str, object]
) -> None:
    mocker.patch("scripts.validate_data.DATA_DIR", tmp_path)
    mock_logger = mocker.patch("scripts.validate_data.logger")
    asia_sku_without_source = {
        **sku_row,
        "sku_id": "asia-example-game-standard",
        "region": "ASIA",
        "source_url": None,
    }
    write_yaml("title_seeds.yaml", [])
    write_yaml("titles.yaml", [])
    write_yaml("skus.yaml", [sku_row, asia_sku_without_source])

    exit_code = main()

    logged_errors = [call.args[0] for call in mock_logger.error.call_args_list]
    assert exit_code == 1
    assert len(logged_errors) == 2
    assert "asia-example-game-standard" in logged_errors[0]
    assert "source_url es obligatorio" in logged_errors[0]
    assert "'eu-example-game-standard' referencia title_id 'example-game'" in logged_errors[1]
