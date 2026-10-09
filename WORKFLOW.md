# Workflow: from a new game to the website

**English** · [Español](WORKFLOW.es.md)

This page explains how a game gets into the database, what is automatic and what is manual. The individual
commands are in `README.md`. The data rules are in the header of each file in `data/`.

## 1. Overview

```
IGDB (platform 508)
   │  [AUTO]   download_igdb_catalog  → skips DLC, packs, bundles and expansions
   ▼
data/igdb_catalog.yaml            (local only, not in git)
   │  [AUTO]   add_titles             → new titles with status: new
   ▼
data/titles.yaml                  (the only list of titles)
   │  [AUTO]   next_work              → what is left to research
   │  [MANUAL] research the format    → find a source, write the SKUs
   ▼
data/physical_release.yaml        (is there a boxed edition at all?)
data/skus.yaml                    (one SKU per region and edition)
   │  [AUTO]   validate_data          → errors, warnings and report
   │  [AUTO]   build_site             → docs/index.html
   ▼
docs/  ──[MANUAL] git commit + push──▶  GitHub Pages
```

The main rule: **scripts bring metadata; a person confirms the format with a source.** No structured data
source says whether a game is a game-key card or a full cartridge. So every value needs a **quote from the
source**, written in the YAML next to its `source_url`. No quote, no value.

**The website shows every title in `titles.yaml` and all its SKUs, whatever their status.** The title status
only decides the work queue.

### Title status

| status | Meaning |
|---|---|
| `new` | added from the catalog, nothing researched: research every region. It has no SKUs nor `physical_release.yaml` entries |
| `refresh` | research every region again. What is there is a starting point to check, not trusted: what is found replaces it (a source that still says the same is kept, with its `updates`) |
| `pending` | what is there is trusted: research only what is missing (regions, SKUs without source, empty fields) |
| `completed` | nothing is missing: every region answered (a sourced SKU or a sourced "no box in this region") and every SKU with all its data, or a sourced "no physical edition". No need to search again |

Researching a `new`, `refresh` or `pending` title ends in `completed` if nothing is missing, and in `pending`
otherwise. If `name`, `publisher` or `igdb_id` turn out wrong, fix them by hand in `titles.yaml`.

When a game will have no box in one region (only digital there), write it in `physical_release.yaml` with
that `region`, `has_physical_release: false` and its source. With a source, the region counts as answered.

A SKU is complete when it has a `source_url`, its `format` is known and it has `distributor`, `release_date`,
`includes_download_code` and `ean`, plus `edition_name` (non-standard editions), `cart_size_gb` (`full_cart`)
or `download_size_gb` (game-key card, code in box). If anything is missing, the title stays `pending`;
`validate_data` fails on a `completed` title that is not.

Each time a title is researched or refreshed, its `last_checked_at` is set to that day, along with the status.
It is `null` while the title is `new`, and also on titles researched before the field existed that left no
SKU or `physical_release.yaml` entry to date them. `validate_data` fails if it is missing or older than the
`verified_at` of one of its SKUs, the `checked_at` of one of their `updates` or of its `physical_release.yaml`
entry.

### SKU source

SKUs have no status. A SKU with a known `format` always has a `source_url` that was opened and checked. A SKU
searched without finding a source has `source_url: null` and `format: unknown`: the website shows it as
unknown format, and `next_work` lists it in `skus_without_source`.

A later source that updates a SKU (a delay, a format change) does not replace `source_url`: it is added to
the SKU's `updates` list with the `fields` it updates, and the site links it next to the source. Nothing shown
on the site changes without its link: a value filled from another source (a date that was `null`) also goes in
`updates`, and a title date written by hand has its source in the title's `updates`.

## 2. Step by step

### Step 1 — Download the IGDB catalog (auto)

```bash
uv run --env-file .env python -m scripts.download_igdb_catalog
```

Downloads all Switch 2 games from IGDB into `data/igdb_catalog.yaml`. It needs `TWITCH_CLIENT_ID` and
`TWITCH_CLIENT_SECRET` in `.env`. The file is not in git (IGDB licence, non-commercial use).

### Step 2 — Add titles (auto)

```bash
uv run python -m scripts.add_titles --count 10   # next 10 games from the catalog
uv run python -m scripts.add_titles --all        # all remaining games
uv run python -m scripts.add_titles --dates-only # only refresh release dates
```

- Works offline: it only reads the local catalog.
- Adds games that are not in `titles.yaml` or `excluded_titles.yaml`, with `status: new`.
- Creates the `title_id` from the name (`donkey-kong-bananza`).
- Refreshes `release_date` (Switch 2 release, e.g. `2026-08-20`, `2026-Q3` or `null`), except exact past dates.

Check by hand:

- **An edition is not a title.** Deluxe, Gold or Collector's editions are SKUs of the base game. Exception:
  if the game is *only* sold as that edition on Switch 2 (ELDEN RING Tarnished Edition), the edition is the
  title and the base game goes to `excluded_titles.yaml`.
- **The `title_id` can change only while the title is `new` and has no SKUs.** After that it is frozen: it
  is part of every `sku_id` and of the public link `#<title_id>`.
- **Not a boxed game?** (DLC, digital-only edition, game only sold inside a compilation.) Move it to
  `excluded_titles.yaml` with a `reason`, so `add_titles` does not add it again.

### Step 3 — Pick what to research (auto)

```bash
uv run python -m scripts.next_work --limit 10
```

Shows the work queue. **Start with `titles_to_research`** (titles in `new`). Other lists:
`titles_to_refresh` (`refresh`), `titles_to_complete` (`pending`, least recently checked first),
`titles_missing_regions` and `skus_without_source`.

### Step 4 — Research the format (manual)

1. **Is there a physical edition?** Many indie games have none. If no region has a box, write it in
   `data/physical_release.yaml` (`has_physical_release: false`, with source). No SKUs needed. The website
   shows the game as "no physical edition": that is an answer, not a gap. If only some regions will have no
   box, write one entry per region (`region: KR`...), with source.
2. **Search by publisher**, because it predicts the format best:
   - Nintendo → almost always `full_cart`.
   - Japanese third-party → Nintendo JP data and Japanese press.
   - Western third-party → game-key card lists in the press and Nintendo EU/US data.
   - Indie → the website of the company that makes the physical edition.
3. **Write the SKUs in `data/skus.yaml`** with every key (unknown values as `null`) and a comment with the
   quote and how it was read: `(leída)`, `(listado)` or `(API)`. Without a source → `format: unknown`,
   `source_url: null`. Each boxed edition is its own SKU.
4. **Set the title to `completed`** if nothing is missing, or to `pending` if something is, and
   `last_checked_at` to today.

To fix a wrong value later, edit `skus.yaml`.

### Step 5 — Validate (auto)

```bash
uv run python -m scripts.validate_data
```

Checks all YAML files and how they link to each other, then prints a report (counts, fill rates, formats
that differ between regions). **Errors** (duplicate ids, a SKU without its title, a known format without
source, a bad barcode, a `completed` title with gaps...) stop the process. **Warnings** (for example a SKU without source) do not.

### Step 6 — Build the website (auto)

```bash
uv run python -m scripts.build_site
```

Builds `docs/index.html` (Spanish and English, with search and filters) from `titles.yaml`, `skus.yaml` and
`physical_release.yaml`. If a YAML file is invalid, it builds nothing.

### Step 7 — Publish (manual)

There is no CI. GitHub Pages serves `docs/` from `main`, so **publishing means commit and push** of `data/`
and `docs/`. Before that, run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python -m scripts.validate_data
```

## 3. Who writes each file

| File | Written by | Edit by hand? |
|---|---|---|
| `data/igdb_catalog.yaml` | `download_igdb_catalog` | no (not in git) |
| `data/titles.yaml` | `add_titles` (keeps existing `status`) | `status` only; name, publisher or `igdb_id` if IGDB is wrong |
| `data/excluded_titles.yaml` | by hand | yes |
| `data/skus.yaml` | by hand, with source | yes |
| `data/physical_release.yaml` | by hand | yes |
| `docs/index.html` | `build_site` | no |

## 4. The normal cycle

```bash
uv run python -m scripts.next_work --limit 10   # what to do
# research those games                         → SKUs with source (+ physical_release.yaml)
uv run python -m scripts.validate_data
uv run python -m scripts.build_site
# commit + push data/ and docs/
```

For new games, first run `download_igdb_catalog` and `add_titles --count 20`. They then appear in
`titles_to_research`.

**Catching up with the news** of the last days (delays, new boxes, format changes):

```bash
uv run python -m scripts.news_candidates --days 7          # news items that name a known title
uv run python -m scripts.check_store_dates --days 7 --save # what changed in the Nintendo stores
# read each lead; a confirmed change goes into the SKU's `updates` with its quote
uv run python -m scripts.validate_data
uv run python -m scripts.build_site
```

Both scripts only point at what to check: the data changes by hand, with a quote, like any other update. Games
that are not in `titles.yaml` yet are skipped; they come in with the next catalog import.

**Never** write a value without a quote from its source, nor a known `format` without a `source_url`.
