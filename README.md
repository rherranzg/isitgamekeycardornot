# isitgamekeycardornot

Open database of the physical format (full cartridge vs. Game-Key Card) of Nintendo Switch 2 games, per region. Published as a static site via GitHub Pages.

## Project layout

- `data/title_seeds.yaml` — curated list of titles (title_id + igdb_id) to import.
- `data/titles.yaml` — title metadata, generated from IGDB via the seeds above. Its `status` field (`pending` / `reviewed` / `refresh`) is the only one edited by hand.
- `data/skus.yaml` — hand-curated per-region SKUs (format, cart size, distributor, evidence, source...). Never invented; unknown fields are left `null`.
- `data/igdb_catalog.yaml` — full IGDB dump of Switch 2 games, used only to pick seed candidates.
- `SOURCES.md` — catalog of third-party data sources tried so far (Nintendo APIs, retailers, press, barcodes): how to query them, what they return and their limits.
- `src/switch2db/` — library code (data loading, validation, IGDB client, site generation).
- `scripts/` — entry points, run with `uv run python -m scripts.<name>`.
- `docs/` — generated static site, served directly by GitHub Pages from `main`.

## Setup

```bash
uv sync
```

IGDB (Twitch) credentials are only needed for `import_titles` and `download_igdb_catalog`. Copy `.env.example` to `.env` and fill in `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET`.

## Workflows

### Add or update a game's SKUs

Edit `data/skus.yaml` by hand following the format documented at the top of the file, then validate:

```bash
uv run python -m scripts.validate_data
```

### Review imported titles

Every title imported from IGDB lands in `data/titles.yaml` with `status: pending`. Once its data has been checked by
hand (the `igdb_id` is the Switch 2 edition, not the base game; name and publisher are right), change it to
`status: reviewed`. `validate_data` lists the titles still pending in its report (`pending_review_titles`).

To fetch a title from IGDB again, set `status: refresh` and run `import_titles`: the title is downloaded again and
goes back to `pending`. Any re-fetch (also `--refresh` / `--refresh-all`) keeps `reviewed` only if IGDB returns
exactly the same data.

### Add titles automatically (bulk)

1. Refresh the local IGDB catalog: `uv run --env-file .env python -m scripts.download_igdb_catalog`.
2. Add seeds for games not seeded yet (auto-generates `title_id` from the name, skips DLC/bundles/episodes):

```bash
uv run python -m scripts.select_seeds --count 10   # next 10 new games
uv run python -m scripts.select_seeds --all         # every remaining game in the catalog
```

New entries are appended to `data/title_seeds.yaml` under a dated "sin revisar" comment — review them
(especially the "correct edition, not base game" criterion at the top of the file) before trusting the data.

3. Import metadata from IGDB. By default this **skips titles already in `titles.yaml`** (unless marked
   `status: refresh`), so it's safe to re-run after a partial or failed run — it only fetches what's still missing:

```bash
uv run --env-file .env python -m scripts.import_titles              # import every title not imported yet
uv run --env-file .env python -m scripts.import_titles --count 20   # import only the next 20 not imported yet
uv run --env-file .env python -m scripts.import_titles --refresh mario-kart-world   # force re-fetch one title
uv run --env-file .env python -m scripts.import_titles --refresh-all                # force re-fetch everything
```

4. Review the imported titles (see above), add their SKUs to `data/skus.yaml` and validate.

### Add a single title by hand

1. Find its IGDB id: `uv run --env-file .env python -m scripts.download_igdb_catalog` (refreshes `data/igdb_catalog.yaml`).
2. Add an entry to `data/title_seeds.yaml` by hand (`title_id` + `igdb_id`), picking the entry whose name matches
   the Switch 2 box (e.g. "Ultimate Edition"), not the base game.
3. Import metadata from IGDB: `uv run --env-file .env python -m scripts.import_titles`.
4. Review the imported title, add its SKUs to `data/skus.yaml` and validate.

### Validate data

```bash
uv run python -m scripts.validate_data
```

Checks `title_seeds.yaml`, `titles.yaml` and `skus.yaml` for schema and integrity errors, logs warnings (seeds not imported yet, titles marked `refresh`...), and reports the titles pending review and the SKU fill rate. Exit code is non-zero on errors.

### Regenerate the website

```bash
uv run python -m scripts.build_site
```

Renders `docs/index.html` (ES/EN, paginated) from `titles.yaml` and `skus.yaml`. Only titles with `status: reviewed` (and their SKUs) are published; `pending` and `refresh` titles are left out. Commit the regenerated `docs/` to publish.

### Tests, lint, types

```bash
uv run pytest
uv run ruff check .
uv run ty check
```

## License

Code: MIT (see `LICENSE`). Data: see `data/LICENSE`.
