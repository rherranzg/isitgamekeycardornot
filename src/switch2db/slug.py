import re
import unicodedata

NON_ALNUM = re.compile(r"[^a-z0-9]+")
UNICODE_MARK_CATEGORY_PREFIX = "M"


def strip_accents(text: str) -> str:
    """Remove accents and other diacritical marks (Unicode category M) after NFKD decomposition."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        char for char in decomposed if not unicodedata.category(char).startswith(UNICODE_MARK_CATEGORY_PREFIX)
    )


def slugify(name: str) -> str:
    """Turn a name into a lowercase, hyphen-separated ASCII slug."""
    normalized = strip_accents(name).encode("ascii", "ignore").decode("ascii")
    slug = NON_ALNUM.sub("-", normalized.lower()).strip("-")
    if not slug:
        raise ValueError(f"Cannot generate a slug from '{name}'")
    return slug


def make_unique_slug(name: str, taken: set[str]) -> str:
    """Generate a slug from the name, adding a numeric suffix if it is already taken."""
    base = slugify(name)
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"
