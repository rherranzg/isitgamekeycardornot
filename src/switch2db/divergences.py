from collections import defaultdict

from switch2db.models import Edition, Format, Region, Sku

FormatsByRegion = dict[Region, Format]


def group_known_formats(skus: list[Sku]) -> dict[tuple[str, Edition], FormatsByRegion]:
    """Group the known format of each region by game and edition, ignoring unknown ones."""
    groups: defaultdict[tuple[str, Edition], FormatsByRegion] = defaultdict(dict)
    for sku in skus:
        if sku.format != Format.UNKNOWN:
            groups[(sku.title_id, sku.edition)][sku.region] = sku.format
    return dict(groups)


def find_format_divergences(skus: list[Sku]) -> dict[tuple[str, Edition], FormatsByRegion]:
    """Return the game-edition pairs whose known format differs between regions."""
    return {
        key: formats_by_region
        for key, formats_by_region in group_known_formats(skus).items()
        if len(set(formats_by_region.values())) > 1
    }
