# Contributing

Thanks for helping. The one rule of this database: **no source, no change.** However likely a format seems,
it is only recorded when a public source says it.

## Reporting an error or missing data

Use the [correction form](https://github.com/rherranzg/isitgamekeycardornot/issues/new?template=correction.yml),
or the "Spotted a mistake?" link under each game on the site, which fills in the game for you. It asks what is
wrong (format, box release date, a missing edition, region or game...), the region, the right value and the
source: a link plus the exact sentence that states it, or a photo of the box dragged into the form.

Good sources, roughly from strongest to weakest:

1. Nintendo or the publisher (official site, store page, support FAQ, press release).
2. A photo of the box (the back or the spine usually says whether it is a Game-Key Card).
3. A press article that states the format for that region.
4. A retailer listing that names the format.

Forum posts and comments can point to a source, but they aren't sources themselves.

## Editing the data directly

1. Edit `data/skus.yaml` (or `data/physical_release.yaml` for a game with no boxed edition), following the
   format documented at the top of the file. Write every key, using `null` for anything unknown.
2. Above the entry, add a comment that quotes the source, tagged `(leída)` when you opened and read the page,
   e.g.:

   ```yaml
   # (leída) Nintendo Life: "the physical game will be fully loaded on a 64GB Switch 2 cartridge"
   # (https://www.nintendolife.com/news/...).
   ```

3. Validate and regenerate the site:

   ```bash
   uv sync
   uv run python -m scripts.validate_data
   uv run python -m scripts.build_site
   ```

4. Open a pull request with the data files and `docs/index.html`.

The detailed working flow (in Spanish) is in [`WORKFLOW.md`](WORKFLOW.md).

Contributions to the data are accepted under the same license as the data (ODbL 1.0, see `data/LICENSE`).
