from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from scripts.build_site import main

WriteYaml = Callable[[str, Sequence[object]], Path]


@pytest.fixture
def docs_dir(mocker: MockerFixture, tmp_path: Path) -> Path:
    """Redirige data/ a tmp_path y docs/ a tmp_path/docs para no tocar el repo."""
    output_dir = tmp_path / "docs"
    mocker.patch("scripts.build_site.DATA_DIR", tmp_path)
    mocker.patch("scripts.build_site.DOCS_DIR", output_dir)
    return output_dir


def test_main_publishes_every_title_regardless_of_status(
    docs_dir: Path, write_yaml: WriteYaml, title_row: dict[str, object], sku_row: dict[str, object]
) -> None:
    reviewed = {**title_row, "status": "reviewed"}
    reviewed_without_skus = {
        **title_row,
        "title_id": "empty-game",
        "name": "Empty Game",
        "status": "reviewed",
    }
    pending_with_skus = {**title_row, "title_id": "pending-game", "name": "Pending Game"}
    pending_sku = {**sku_row, "sku_id": "eu-pending-game-standard", "title_id": "pending-game"}
    new_title = {**title_row, "title_id": "new-game", "name": "New Game", "status": "new"}
    write_yaml("titles.yaml", [reviewed, reviewed_without_skus, pending_with_skus, new_title])
    write_yaml("skus.yaml", [sku_row, pending_sku])
    write_yaml("physical_release.yaml", [])

    exit_code = main()

    html = (docs_dir / "index.html").read_text(encoding="utf-8")
    assert exit_code == 0
    assert (docs_dir / ".nojekyll").exists()
    assert 'id="example-game"' in html
    assert 'data-search="example game example publisher"' in html
    assert 'data-region="EU"' in html
    assert "Empty Game" in html
    assert "Pending Game" in html
    assert "New Game" in html
    assert 'data-no-skus="true"' in html
    assert 'value="no_skus"' in html


def test_main_escapes_html_in_title_names(
    docs_dir: Path, write_yaml: WriteYaml, title_row: dict[str, object], sku_row: dict[str, object]
) -> None:
    write_yaml("titles.yaml", [{**title_row, "name": "<script>alert(1)</script>", "status": "reviewed"}])
    write_yaml("skus.yaml", [sku_row])
    write_yaml("physical_release.yaml", [])

    main()

    html = (docs_dir / "index.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_main_returns_one_without_writing_when_data_is_invalid(
    docs_dir: Path, write_yaml: WriteYaml, title_row: dict[str, object], sku_row: dict[str, object]
) -> None:
    write_yaml("titles.yaml", [title_row])
    write_yaml("skus.yaml", [{**sku_row, "source_url": None}])
    write_yaml("physical_release.yaml", [])

    assert main() == 1
    assert not (docs_dir / "index.html").exists()


def test_main_publishes_games_without_a_boxed_edition(
    docs_dir: Path,
    write_yaml: WriteYaml,
    title_row: dict[str, object],
    sku_row: dict[str, object],
    digital_only_row: dict[str, object],
) -> None:
    digital_game = {
        **title_row,
        "title_id": "digital-game",
        "name": "Digital Game",
        "status": "reviewed",
    }
    write_yaml("titles.yaml", [{**title_row, "status": "reviewed"}, digital_game])
    write_yaml("skus.yaml", [sku_row])
    write_yaml("physical_release.yaml", [{**digital_only_row, "title_id": "digital-game"}])

    exit_code = main()

    html = (docs_dir / "index.html").read_text(encoding="utf-8")
    assert exit_code == 0
    assert 'id="digital-game"' in html
    assert 'data-no-box="true"' in html
    assert "Solo digital" in html
    assert "https://example.com/digital-only" in html
    assert 'value="no_box"' in html
