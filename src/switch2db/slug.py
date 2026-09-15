import re
import unicodedata

NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Convierte un nombre en un slug ascii en minúsculas separado por guiones."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = NON_ALNUM.sub("-", normalized.lower()).strip("-")
    if not slug:
        raise ValueError(f"No se puede generar un slug a partir de '{name}'")
    return slug


def make_unique_slug(name: str, taken: set[str]) -> str:
    """Genera un slug a partir del nombre, añadiendo un sufijo numérico si ya está en uso."""
    base = slugify(name)
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"
