import os


def read_required_env(name: str) -> str:
    """Lee una variable de entorno obligatoria; falla si no existe o está vacía."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name} (usa uv run --env-file .env)")
    return value
