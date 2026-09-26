from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from switch2db.catalog import CatalogEntry
from switch2db.models import ExcludedTitle, PhysicalRelease, Sku, Title

ModelT = TypeVar("ModelT", bound=BaseModel)

TITLES_HEADER = (
    "# Known Switch 2 games. Added by scripts/add_titles.py from data/igdb_catalog.yaml.\n"
    "# name, publisher and release_date come from IGDB; status is edited by hand (the site shows all).\n"
    "# release_date is the Switch 2 release with the known precision (2026-08-20, 2026-08, 2026-Q3,\n"
    "# 2026) or null; add_titles refreshes it unless it is an exact day already past. If IGDB lacks it,\n"
    "# it is written by hand with a checked source, and a null from IGDB does not erase it.\n"
    "# status:\n"
    "#   new      = from the catalog, not researched (set by add_titles)\n"
    "#   pending  = researched without confirming the boxed edition or finding a source\n"
    "#   reviewed = researched and checked\n"
)
CATALOG_HEADER = "# Switch 2 games on IGDB (scripts/download_igdb_catalog.py). Local, not versioned.\n"


def read_yaml_rows(path: Path) -> list[object]:
    """Read a YAML file whose root must be a list and return its rows."""
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(content, list):
        raise ValueError(f"{path}: the YAML root must be a list (use [] if empty)")
    return content


def describe_row(row: object, index: int) -> str:
    """Identify a row by its position and, if present, by its sku_id or title_id."""
    if isinstance(row, dict):
        row_id = row.get("sku_id") or row.get("title_id")
        if row_id:
            return f"#{index} {row_id}"
    return f"#{index}"


def format_validation_error(error: ValidationError) -> str:
    """Summarize Pydantic errors in one line with field and message."""
    parts = []
    for detail in error.errors():
        location = ".".join(str(part) for part in detail["loc"])
        parts.append(f"{location}: {detail['msg']}" if location else detail["msg"])
    return "; ".join(parts)


def parse_rows(rows: Sequence[object], model: type[ModelT], source: str) -> tuple[list[ModelT], list[str]]:
    """Validate each row against the model, collecting errors instead of stopping at the first."""
    parsed: list[ModelT] = []
    errors: list[str] = []
    for index, row in enumerate(rows):
        try:
            parsed.append(model.model_validate(row))
        except ValidationError as error:
            errors.append(f"{source} {describe_row(row, index)}: {format_validation_error(error)}")
    return parsed, errors


def load_titles(path: Path) -> tuple[list[Title], list[str]]:
    """Load and validate the titles imported from IGDB."""
    return parse_rows(read_yaml_rows(path), Title, path.name)


def load_excluded_titles(path: Path) -> tuple[list[ExcludedTitle], list[str]]:
    """Load and validate the IGDB catalog games that are not cataloged."""
    return parse_rows(read_yaml_rows(path), ExcludedTitle, path.name)


def load_skus(path: Path) -> tuple[list[Sku], list[str]]:
    """Load and validate the regional SKUs."""
    return parse_rows(read_yaml_rows(path), Sku, path.name)


def load_physical_releases(path: Path) -> tuple[list[PhysicalRelease], list[str]]:
    """Load and validate the research on whether each game has a physical edition."""
    return parse_rows(read_yaml_rows(path), PhysicalRelease, path.name)


def require_valid(loaded: tuple[list[ModelT], list[str]], file_name: str) -> list[ModelT]:
    """Return the validated rows of a load_*; fail with all its errors if there were any."""
    rows, errors = loaded
    if errors:
        raise ValueError(f"{file_name} has {len(errors)} errors (run scripts.validate_data): {errors}")
    return rows


def write_generated_yaml(path: Path, rows: list[dict[str, object]], header: str) -> None:
    """Write the rows as YAML preceded by the generated-file header."""
    content = yaml.safe_dump(rows, sort_keys=False, allow_unicode=True)
    path.write_text(f"{header}{content}", encoding="utf-8")


def write_titles(path: Path, titles: list[Title]) -> None:
    """Rewrite the titles file keeping each title's status, with the enum as plain text."""
    write_generated_yaml(path, [title.model_dump(mode="json") for title in titles], TITLES_HEADER)


def write_catalog(path: Path, entries: list[CatalogEntry]) -> None:
    """Rewrite the local IGDB games catalog, with ISO dates."""
    write_generated_yaml(path, [entry.model_dump(mode="json") for entry in entries], CATALOG_HEADER)
