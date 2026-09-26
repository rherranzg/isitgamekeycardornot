from pathlib import Path

# Repo root: uv sync installs the package in editable mode, so src/switch2db stays inside the repo.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
# docs/, not site/: it is the folder GitHub Pages can serve straight from main.
DOCS_DIR = PROJECT_ROOT / "docs"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
