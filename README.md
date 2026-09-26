# Is It Game-Key Card Or Not?

An open database of the physical format of Nintendo Switch 2 games, region by region and edition by edition.

**Browse it: https://rherranzg.github.io/isitgamekeycardornot/**

For every boxed release it records which of these you get:

| Format | What is in the box |
|---|---|
| **Full cartridge** | The whole game is on the cartridge. |
| **Game-Key Card** | The cartridge is a key: the game is downloaded, and the card must be inserted to play. |
| **Code in box** | A download code, with no game card. |
| **Unknown** | Someone looked but found no source yet. |
| **No physical edition** | No boxed release was found. "Digital only" is shown only when a source says so. |

The same game can have different formats in different regions or editions, so each regional box (a "SKU") is
listed separately.

## Where the data comes from

Every SKU links to the **public source** it is based on: a Nintendo or publisher page, a press article, a
retailer listing or a photo of the box. The site shows what kind of source each one is. In `data/skus.yaml`,
the comment above each entry quotes the exact sentence that backs it, marked `(leída)` (the page was read),
`(listado)` (only the title of a retailer's search result was visible) or `(API)`.

If there is no source, the field is left empty (`null`) or the format is shown as unknown. Nothing is guessed.

Game names, publishers and release dates come from [IGDB](https://www.igdb.com).

**Mistakes are possible.** Formats change between announcement and release, and retailer listings can be
wrong. Check before you buy, and if you find an error, please report it.

## Report a correction

Open an issue with the
[correction form](https://github.com/rherranzg/isitgamekeycardornot/issues/new?template=correction.yml). The
one thing it needs is a **link to a source** that states the format. Pull requests that edit the data directly
are welcome too: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Using the data

The data is plain YAML in [`data/`](data/):

- `titles.yaml` — every known Switch 2 game (`title_id`, `igdb_id`, `name`, `publisher`, `release_date`).
- `skus.yaml` — one entry per region and edition: format, distributor, release date, cartridge or download
  size, barcode, evidence type and source URL.
- `physical_release.yaml` — games checked for a boxed edition that has not turned up, with their source when
  there is one.
- `excluded_titles.yaml` — IGDB entries deliberately not listed (editions covered by their base game, games
  only sold inside a compilation...).

Each file documents its fields at the top. Each game on the site can be linked with `#<title_id>`.

## License

- Code: MIT (see [`LICENSE`](LICENSE)).
- Data: [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), except the IGDB metadata and the quoted
  excerpts (see [`data/LICENSE`](data/LICENSE)).

Nintendo, Nintendo Switch 2 and Game-Key Card are trademarks of Nintendo. This is an independent project, not
affiliated with or endorsed by Nintendo.

---

## For maintainers

The detailed working flow, from a new game to the site, is in [`WORKFLOW.md`](WORKFLOW.md) (in Spanish).

### Setup

```bash
uv sync
```

IGDB (Twitch) credentials are only needed for `download_igdb_catalog`, the single entry point to IGDB. Copy
`.env.example` to `.env` and fill in `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET`. Every other script works
offline on the local YAML files. `data/igdb_catalog.yaml`, the local IGDB dump that `add_titles` draws from,
is git-ignored.

### Statuses

Every SKU carries a `status`. The site publishes all of them:

| status | Meaning | On the site |
|---|---|---|
| `new` | draft nobody has researched yet | unknown format |
| `pending` | researched, but no source turned up | unknown format |
| `reviewed` | its source was opened and says what the SKU claims | its format and source |
| `refresh` | has a source, but needs re-checking (stale data, dead link, new region) | its format and source |

A SKU is only `reviewed` with a `source_url`, and a `pending` SKU has none (the model rejects it).

Titles carry `new` (from the IGDB catalog, not researched), `pending` (researched without confirming the
boxed edition) or `reviewed` (confirmed that the `igdb_id` is the game's, and that the name and publisher
are right). The site publishes every title whatever its status; a title with no SKUs shows an empty table.

If `name`, `publisher` or `igdb_id` turn out wrong, fix them by hand in `titles.yaml`. A title's `title_id` is
frozen once a SKU points at it: it is part of every `sku_id` and the site's `#<title_id>` anchor. When a
published title is merged into another, move it to `excluded_titles.yaml` with `former_title_id` and
`merged_into`, and the site keeps its old anchor.

### Editions

An edition (Deluxe, Gold, Collector's...; IGDB links it to its game with `version_parent`) is not a title: its
box is a SKU of the base game, with `edition: collectors` when it is called Collector's, Limited, Premium or
Special or is a box with goodies, and `deluxe` otherwise (extra content, SteelBook, sleeve...). Its commercial
name goes in `edition_name`. Digital-only editions are not cataloged. The exception is a game that Switch 2 only
sells as that edition (ELDEN RING Tarnished Edition, Cyberpunk 2077: Ultimate Edition): then the edition is the
title and the base game goes to `excluded_titles.yaml`.

### Commands

```bash
uv run python -m scripts.next_work [--limit 10]     # what is left to research (offline)
uv run --env-file .env python -m scripts.download_igdb_catalog   # refresh the IGDB catalog (network)
uv run python -m scripts.add_titles --count 10      # add the next games from the catalog (or --all)
uv run python -m scripts.add_titles --dates-only    # only refresh release dates
uv run python -m scripts.fetch_quote <url-or-file> '<regex>' [--context 120] [--max 5] [--raw]
uv run python -m scripts.validate_data              # schema, integrity and fill-rate report
uv run python -m scripts.build_site                 # regenerate docs/index.html
```

`add_titles` takes `name`, `publisher` and `release_date` from the catalog and never touches an existing
title's `status`. `release_date` is the Switch 2 release with whatever precision IGDB knows (`2026-08-20`,
`2026-08`, `2026-Q3`, `2026` or `null`), refreshed on every run unless it is already an exact day in the past.
When IGDB has no Switch 2 date, it can be written by hand from a checked source (Nintendo's own store data, the
publisher or the press); a refresh never replaces it with IGDB's `null`, only with a date.

`fetch_quote` downloads a page, identifying itself with the project's User-Agent (or reads a local file), strips
scripts and tags, and prints only the fragments that match: the literal quote a SKU comment needs. A site that
answers 403 is not retried by other means.

GitHub Pages serves `docs/` from `main`, so publishing means committing the regenerated `docs/` with the data.

### Before considering a change done

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python -m scripts.validate_data
```
