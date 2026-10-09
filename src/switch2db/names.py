import re

from switch2db.slug import strip_accents

# Removed before decomposing: NFKD turns "™" into "TM" and it would stick to the name.
TRADEMARK_SIGNS = re.compile(r"[™®©]")
# Store suffixes that do not change which game it is ("Absolum - Nintendo Switch 2 Edition").
STORE_SUFFIXES = re.compile(
    r"\s*[-–—:]?\s*(nintendo switch\s*2 edition|for nintendo switch\s*2|standard edition)\s*$"
)
NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_name(name: str) -> str:
    """Normalize a game name to compare it across sources: lowercase ASCII words separated by one space,
    without trademark signs, accents or store suffixes. Non-Latin text (Japanese, Korean) is dropped."""
    without_signs = TRADEMARK_SIGNS.sub("", name)
    lowered = strip_accents(without_signs).lower()
    without_suffix = STORE_SUFFIXES.sub("", lowered)
    return NON_ALNUM.sub(" ", without_suffix).strip()
