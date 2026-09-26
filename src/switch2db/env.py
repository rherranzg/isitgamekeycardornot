import os


def read_required_env(name: str) -> str:
    """Read a required environment variable; fail if it is missing or empty."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing environment variable {name} (use uv run --env-file .env)")
    return value
