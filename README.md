# isitgamekeycardornot

Open database of the physical format (full cartridge vs. Game-Key Card) of Nintendo Switch 2 games, per region. Published as a static site via GitHub Pages.

## Project layout

- `data/titles.yaml` — every known Switch 2 game: `title_id`, `igdb_id`, `name`, `publisher` and `status`. Added by `add_titles` from the local IGDB catalog; `status` (`new` / `pending` / `reviewed`) is the only field normally edited by hand.
- `data/skus.yaml` — per-region SKUs (format, cart size, distributor, evidence, source...), curated by hand or by the research skill. Never invented; unknown fields are written as `null`. Each SKU carries a `status` (`new` / `pending` / `reviewed` / `refresh`); only `new` is kept off the site, and `pending` means the search came up empty.
- `data/physical_release.yaml` — whether a game ever got a boxed edition at all, with the source backing it. Games confirmed as digital-only are published too, as a "no physical edition" card.
- `data/igdb_catalog.yaml` — IGDB dump of Switch 2 games that can have a box of their own (DLC, packs, bundles and expansions are dropped on download), used as the pool `add_titles` draws from. Local only (git-ignored).
- `data/LICENSE` — data license (ODbL 1.0; IGDB metadata excluded).
- `WORKFLOW.md` — step-by-step flow from a new game to the published site, marking which steps are
  automatic (scripts) and which are manual (review, format research).
- `SOURCES.md` — catalog of third-party data sources tried so far (Nintendo APIs, retailers, press, barcodes): how to query them, what they return and their limits.
- `CLAUDE.md` — working rules for Claude Code in this repo.
- `.claude/skills/investigar-juego/` — skill that routes the format research by publisher and region and writes the SKUs with their source, leaving what it could verify as `reviewed`.
- `src/switch2db/` — library code (data loading, validation, IGDB client, site generation).
- `scripts/` — entry points, run with `uv run python -m scripts.<name>`.
- `docs/` — generated static site, served directly by GitHub Pages from `main`.

## Setup

```bash
uv sync
```

IGDB (Twitch) credentials are only needed for `download_igdb_catalog`, the single entry point to IGDB. Copy `.env.example` to `.env` and fill in `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET`. Every other script works offline on the local YAML files.

## Workflows

See `WORKFLOW.md` for the end-to-end flow and what is automatic vs. manual at each step.

### See what is pending

```bash
uv run python -m scripts.next_work            # the whole queue
uv run python -m scripts.next_work --limit 10 # in batches
```

Lists the titles nobody has researched yet (`status: new`), the ones researched without a confirmed edition
(`pending`), the regions missing per title, and the SKUs still without a source (`new_skus`, never searched,
and `skus_without_source`, searched with nothing found) or marked `refresh` (needs re-checking evidence).
Reads only the local files: no network, no IGDB.

### Add or update a game's SKUs

Edit `data/skus.yaml` by hand following the format documented at the top of the file (write every key, using
`null` when the value is unknown), then validate:

```bash
uv run python -m scripts.validate_data
```

Every SKU carries a `status` that decides how it is published:

| status | Meaning | On the site |
|---|---|---|
| `new` | draft nobody has researched yet | not published |
| `pending` | researched, but no source turned up: needs a deeper search | published as unknown format |
| `reviewed` | its source was opened and says what the SKU claims | published |
| `refresh` | needs re-searching the web for evidence of its format (stale data, dead source, new region) | published |

A SKU whose `source_url` has been read is written straight as `reviewed` — by hand or by the research skill.
What backs the data is the quoted citation in the YAML comment, not a second review pass. No source, no
`reviewed`. A `pending` SKU carries no `source_url` (the model rejects it), so its `format` is `unknown`:
the site says nobody knows yet rather than hiding the region.

If a game has no boxed edition at all, don't write SKUs: record it in `data/physical_release.yaml`, so it is
not researched again.

### Title statuses

Every title in `data/titles.yaml` carries a `status`, and it is the only field edited by hand:

| status | Meaning | On the site |
|---|---|---|
| `new` | taken from the IGDB catalog, nobody has researched it | not published |
| `pending` | researched without confirming the box edition or finding a source | not published |
| `reviewed` | researched: the `igdb_id` is the boxed edition and the rest checks out | published if it has a SKU that is not `new` |

A title moves to `reviewed` while researching it (by hand or with the research skill), never before: its SKUs,
or an entry in `physical_release.yaml` saying there is no box, are what back it. `validate_data` warns about
any title claiming to be researched with neither.

If `name`, `publisher` or `igdb_id` turn out wrong (IGDB changed the entry, or it was mismatched), fix them by
hand directly in `titles.yaml`. There is no status for this: it's a fix to the title's identity, not evidence
to re-check — that's what a SKU's `refresh` status is for.

While a title is `new` and has no SKUs, its auto-generated `title_id` can still be changed. Once a SKU points
at it, it is frozen.

### Add titles (bulk)

1. Refresh the local IGDB catalog (the only step that hits the network):
   `uv run --env-file .env python -m scripts.download_igdb_catalog`.
2. Add games not in `titles.yaml` yet, with `status: new` (the `title_id` is slugified from the name):

```bash
uv run python -m scripts.add_titles --count 10   # next 10 games from the catalog
uv run python -m scripts.add_titles --all        # every remaining game in the catalog
```

`name` and `publisher` come from the catalog, so this needs no IGDB credentials. Titles already in the file
keep their `status` untouched.

3. Research them (see `WORKFLOW.md`), write their SKUs in `data/skus.yaml` and validate.

### Add a single title by hand

1. If the game is not in `data/igdb_catalog.yaml`, refresh it:
   `uv run --env-file .env python -m scripts.download_igdb_catalog`.
2. Add a row to `data/titles.yaml` by hand with every key (`title_id`, `igdb_id`, `name`, `publisher`,
   `status: new`), picking the IGDB entry whose name matches the Switch 2 box (e.g. "Ultimate Edition"), not
   the base game.
3. Research it, add its SKUs to `data/skus.yaml` and validate.

### Quote a source without dumping it

```bash
uv run python -m scripts.fetch_quote <url-or-file> '<regex>' [--context 120] [--max 5] [--raw]
```

Downloads the page with a browser User-Agent (or reads a local file), strips scripts and tags, and prints only
the fragments that match: the literal quote a SKU comment needs. `--raw` skips the HTML cleanup (JSON, text).

### Validate data

```bash
uv run python -m scripts.validate_data
```

Checks `titles.yaml`, `skus.yaml` and `physical_release.yaml` for schema and integrity errors (including EAN/UPC
check digits), logs warnings (titles that claim to be researched but left neither SKUs nor a `physical_release`
entry, SKUs marked `refresh`, SKU keys left out instead of `null`, sizes that don't match the format, SKUs of
unreviewed titles...), and reports the titles pending review and the SKU fill rate. Exit code is non-zero on
errors.

### Regenerate the website

```bash
uv run python -m scripts.build_site
```

Renders `docs/index.html` (ES/EN, with search by game or publisher and region/format/edition filters) from
`titles.yaml`, `skus.yaml` and `physical_release.yaml`. A `reviewed` title is published when it has **at least
one SKU that is not `new`**, or when `physical_release.yaml` says it never got a box — those show a "no
physical edition" card with its source, and answer to the `no_box` value of the format filter. Left out:
`new` and `pending` titles, and reviewed titles with a box but no publishable SKU yet. Each game can
be linked with `#<title_id>`. Commit the regenerated `docs/` to publish.

### Tests, lint, types

Run all of these before considering a change done:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python -m scripts.validate_data
```

## License

Code: MIT (see `LICENSE`). Data: see `data/LICENSE`.
