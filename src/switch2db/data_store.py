from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from switch2db.catalog import CatalogEntry
from switch2db.models import Sku, Title, TitleSeed

ModelT = TypeVar("ModelT", bound=BaseModel)

TITLES_HEADER = "# Generado por scripts/import_titles.py a partir de title_seeds.yaml. No editar a mano.\n"
CATALOG_HEADER = "# Juegos de Switch 2 en IGDB (scripts/download_igdb_catalog.py). Local, no se versiona.\n"


def read_yaml_rows(path: Path) -> list[object]:
    """Lee un YAML cuya raíz debe ser una lista y devuelve sus filas."""
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(content, list):
        raise ValueError(f"{path}: la raíz del YAML debe ser una lista (usa [] si está vacío)")
    return content


def describe_row(row: object, index: int) -> str:
    """Identifica una fila por su posición y, si lo tiene, por su sku_id o title_id."""
    if isinstance(row, dict):
        row_id = row.get("sku_id") or row.get("title_id")
        if row_id:
            return f"#{index} {row_id}"
    return f"#{index}"


def format_validation_error(error: ValidationError) -> str:
    """Resume los errores de Pydantic en una línea con campo y mensaje."""
    parts = []
    for detail in error.errors():
        location = ".".join(str(part) for part in detail["loc"])
        parts.append(f"{location}: {detail['msg']}" if location else detail["msg"])
    return "; ".join(parts)


def parse_rows(rows: Sequence[object], model: type[ModelT], source: str) -> tuple[list[ModelT], list[str]]:
    """Valida cada fila contra el modelo acumulando los errores en vez de parar en el primero."""
    parsed: list[ModelT] = []
    errors: list[str] = []
    for index, row in enumerate(rows):
        try:
            parsed.append(model.model_validate(row))
        except ValidationError as error:
            errors.append(f"{source} {describe_row(row, index)}: {format_validation_error(error)}")
    return parsed, errors


def load_title_seeds(path: Path) -> tuple[list[TitleSeed], list[str]]:
    """Carga y valida las semillas de títulos."""
    return parse_rows(read_yaml_rows(path), TitleSeed, path.name)


def load_titles(path: Path) -> tuple[list[Title], list[str]]:
    """Carga y valida los títulos importados de IGDB."""
    return parse_rows(read_yaml_rows(path), Title, path.name)


def load_skus(path: Path) -> tuple[list[Sku], list[str]]:
    """Carga y valida los SKUs regionales."""
    return parse_rows(read_yaml_rows(path), Sku, path.name)


def write_generated_yaml(path: Path, rows: list[dict[str, object]], header: str) -> None:
    """Escribe las filas como YAML precedidas de la cabecera de fichero generado."""
    content = yaml.safe_dump(rows, sort_keys=False, allow_unicode=True)
    path.write_text(f"{header}{content}", encoding="utf-8")


def append_title_seeds(path: Path, seeds: list[TitleSeed], comment: str) -> None:
    """Añade semillas nuevas al final de title_seeds.yaml sin tocar el contenido existente."""
    if not seeds:
        return
    block = yaml.safe_dump([seed.model_dump() for seed in seeds], sort_keys=False, allow_unicode=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n# {comment}\n{block}")


def write_titles(path: Path, titles: list[Title]) -> None:
    """Reescribe el fichero de títulos importados de IGDB."""
    write_generated_yaml(path, [title.model_dump() for title in titles], TITLES_HEADER)


def write_catalog(path: Path, entries: list[CatalogEntry]) -> None:
    """Reescribe el catálogo local de juegos de IGDB, con las fechas en ISO."""
    write_generated_yaml(path, [entry.model_dump(mode="json") for entry in entries], CATALOG_HEADER)
