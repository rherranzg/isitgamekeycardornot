from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from switch2db.catalog import CatalogEntry
from switch2db.models import PhysicalRelease, Sku, Title

ModelT = TypeVar("ModelT", bound=BaseModel)

TITLES_HEADER = (
    "# Juegos de Switch 2 conocidos. Los añade scripts/add_titles.py desde data/igdb_catalog.yaml.\n"
    "# name y publisher vienen de IGDB; a mano solo se edita status (la web publica todos los status):\n"
    "#   new      = del catálogo y sin investigar (lo pone add_titles)\n"
    "#   pending  = investigado sin confirmar la edición de la caja ni encontrar fuente\n"
    "#   reviewed = investigado y comprobado\n"
)
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


def load_titles(path: Path) -> tuple[list[Title], list[str]]:
    """Carga y valida los títulos importados de IGDB."""
    return parse_rows(read_yaml_rows(path), Title, path.name)


def load_skus(path: Path) -> tuple[list[Sku], list[str]]:
    """Carga y valida los SKUs regionales."""
    return parse_rows(read_yaml_rows(path), Sku, path.name)


def load_physical_releases(path: Path) -> tuple[list[PhysicalRelease], list[str]]:
    """Carga y valida lo investigado sobre la existencia de edición física de cada juego."""
    return parse_rows(read_yaml_rows(path), PhysicalRelease, path.name)


def require_valid(loaded: tuple[list[ModelT], list[str]], file_name: str) -> list[ModelT]:
    """Devuelve las filas validadas de un load_*; falla con todos sus errores si hubo alguno."""
    rows, errors = loaded
    if errors:
        raise ValueError(f"{file_name} tiene {len(errors)} errores (ejecuta scripts.validate_data): {errors}")
    return rows


def write_generated_yaml(path: Path, rows: list[dict[str, object]], header: str) -> None:
    """Escribe las filas como YAML precedidas de la cabecera de fichero generado."""
    content = yaml.safe_dump(rows, sort_keys=False, allow_unicode=True)
    path.write_text(f"{header}{content}", encoding="utf-8")


def write_titles(path: Path, titles: list[Title]) -> None:
    """Reescribe el fichero de títulos conservando el status de cada uno, con el enum como texto plano."""
    write_generated_yaml(path, [title.model_dump(mode="json") for title in titles], TITLES_HEADER)


def write_catalog(path: Path, entries: list[CatalogEntry]) -> None:
    """Reescribe el catálogo local de juegos de IGDB, con las fechas en ISO."""
    write_generated_yaml(path, [entry.model_dump(mode="json") for entry in entries], CATALOG_HEADER)
