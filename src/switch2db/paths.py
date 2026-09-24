from pathlib import Path

# Raíz del repo: uv sync instala el paquete en modo editable, así que src/switch2db sigue dentro del repo.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
# docs/, no site/: es la carpeta que GitHub Pages puede servir directamente desde main.
DOCS_DIR = PROJECT_ROOT / "docs"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
