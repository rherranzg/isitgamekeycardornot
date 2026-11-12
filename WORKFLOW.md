# Workflow: from a new game to the website

This page explains how a game gets into the database, what is automatic and what is manual. Every command is
listed in [section 5](#5-command-reference). The data fields are described in the `README.md` and, with their
writing rules, in the header of each file in `data/`.

## Setup

```bash
uv sync
```

IGDB (Twitch) credentials are only needed for `download_igdb_catalog`, the single entry point to IGDB. Copy
`.env.example` to `.env` and fill in `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET`. No other script needs
credentials.

Only `fetch_quote`, `news_candidates`, `check_store_dates` and `download_covers` use the network.
`data/igdb_catalog.yaml`, the local IGDB dump that `add_titles` draws from, is git-ignored.

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

A title's `title_id` is frozen once a SKU points at it: it is part of every `sku_id` and the site's
`#<title_id>` anchor. When a published title is merged into another, move it to `excluded_titles.yaml` with
`former_title_id` and `merged_into`, and the site keeps its old anchor.

When a game will have no box in one region (only digital there), write it in `physical_release.yaml` with
that `region`, `has_physical_release: false` and its source. With a source, the region counts as answered.

A SKU is complete when it has a `source_url`, its `format` is known and it has `distributor` and `release_date`,
plus `edition_name` (non-standard editions) and `download_size_gb` (game-key card, code in box).
`cart_size_gb`, `includes_download_code` and `ean` are written when known, but are not required. If anything is missing, the title stays `pending`;
`validate_data` fails on a `completed` title that is not.

Each time a title is researched or refreshed, its `last_checked_at` is set to that moment, with date, time and
UTC offset (`2026-10-09T19:42:10+02:00`), along with the status. Older checks only kept the day.
It is `null` while the title is `new`, and also on titles researched before the field existed that left no
SKU or `physical_release.yaml` entry to date them. `validate_data` fails if it is missing or its day is older than the
`verified_at` of one of its SKUs, the `checked_at` of one of their `updates` or of its `physical_release.yaml`
entry.

### SKU source

SKUs have no status. A SKU with a known `format` always has a `source_url` that was opened and checked. A SKU
searched without finding a source has `source_url: null` and `format: unknown`: the website shows it as
unknown format, and `next_work` lists it in `skus_without_source`.

`source_url` is the original source that backs the format, and it only changes if it stops backing it. A
later source that updates a SKU (a delay, a new date, a format change) goes in the SKU's `updates`, oldest
first, with the date it was read and the kind of update in `fields`: `release_date`, `format`, `edition`,
`distributor`, `size`, or `other` for a kind that has no value yet. The field it changes is rewritten with the
new value. The site links each update next to the source, newest first, named by its kind ("Date update"; just
"Update" for `other`).

```yaml
  source_url: "https://www.nintendolife.com/guides/..."
  updates:
    - url: "https://www.fangamer.com/products/..."  # (leída) "will not ship until November 10, 2026"
      checked_at: "2026-10-09"
      fields: ["release_date"]
```

Nothing shown on the site changes without its link: any value that comes from a source other than
`source_url` (a date that was `null`, a distributor) also goes in `updates`, even on a SKU just created.

A title's `release_date` comes from IGDB. When it is written by hand (IGDB has none, or a wrong one), its
source goes in the title's own `updates` in `titles.yaml`; the site links it next to the date, and `add_titles`
keeps that date instead of IGDB's.

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

- **An edition is not a title.** Deluxe, Gold or Collector's editions (IGDB links them to their game with
  `version_parent`) are SKUs of the base game: `edition: collectors` when it is called Collector's, Limited,
  Premium or Special or is a box with goodies, and `deluxe` otherwise (extra content, SteelBook, sleeve...). Its
  commercial name goes in `edition_name`. Digital-only editions are not cataloged. Exception: if the game is
  *only* sold as that edition on Switch 2 (ELDEN RING Tarnished Edition, Cyberpunk 2077: Ultimate Edition), the
  edition is the title and the base game goes to `excluded_titles.yaml`.
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
   quote and how it was read: `(leída)` (the page was opened and read), `(listado)` (only the title of a
   search or retailer result was visible, for example because the store answered 403) or `(API)` (a store's
   data feed). `verified_at` is the day the source was opened. Without a source → `format: unknown`,
   `source_url: null`. Each boxed edition is its own SKU.
4. **Set the title to `completed`** if nothing is missing, or to `pending` if something is, and
   `last_checked_at` to the current date and time.

There is no review step: everything is published. A SKU without `source_url` stays in `skus_without_source`
until a deeper search (another region, the press, a box photo) finds one. To fix a wrong value later, edit
`skus.yaml`, or delete the entry.

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

**Box covers** (European box of the standard SKUs, see `download_covers` in section 5):

```bash
uv run python -m scripts.download_covers                    # every EU SKU without a cover yet
uv run python -m scripts.download_covers --titles <id> ...  # only these games
uv run python -m scripts.download_covers --refresh          # download again (a provisional box replaced)
uv run python -m scripts.validate_data
```

`not_found` (MediaMarkt does not sell the standard box), `ean_mismatch` and `not_a_switch2_box` leave the SKU
without a cover; it is looked for again on the next run.

**Never** write a value without a quote from its source, nor a known `format` without a `source_url`.

## 5. Command reference

```bash
uv run python -m scripts.next_work [--limit 10]     # what is left to research (offline)
uv run python -m scripts.next_work --upcoming 10    # next 10 titles to come out (offline)
uv run python -m scripts.next_work --upcoming 10 --skip-checked-days 7   # minus those checked in the last 7 days
uv run --env-file .env python -m scripts.download_igdb_catalog   # refresh the IGDB catalog (network)
uv run python -m scripts.add_titles --count 10      # add the next games from the catalog (or --all)
uv run python -m scripts.add_titles --dates-only    # only refresh release dates
uv run python -m scripts.fetch_quote <url-or-file> '<regex>' [--context 120] [--max 5] [--raw]
uv run python -m scripts.news_candidates --days 7    # Switch 2 box and date news of the last days (network)
uv run python -m scripts.check_store_dates --days 7 [--save]   # Nintendo EU/NA/JP store dates (network)
uv run python -m scripts.download_covers [--titles ID ...] [--random N] [--refresh]   # EU box fronts (network)
uv run python -m scripts.validate_data              # schema, integrity and fill-rate report
uv run python -m scripts.build_site                 # regenerate docs/index.html
```

**`add_titles`** takes `name`, `publisher` and `release_date` from the catalog and never touches an existing
title's `status`. `release_date` is the Switch 2 release with whatever precision IGDB knows (`2026-08-20`,
`2026-08`, `2026-Q3`, `2026` or `null`), refreshed on every run unless it is already an exact day in the past.
When IGDB has no Switch 2 date, it can be written by hand from a checked source (Nintendo's own store data, the
publisher or the press); a refresh never replaces it with IGDB's `null`, only with a date.

**`fetch_quote`** downloads a page, identifying itself with the project's User-Agent (or reads a local file),
strips scripts and tags, and prints only the fragments that match: the literal quote a SKU comment needs. A site
that answers 403 is not retried by other means.

**`news_candidates`** reads the RSS feeds of several news sites (paging back where the feed allows it) and lists
the Switch 2 news items of the window that talk about a box or a release date, matched to `titles.yaml` by name.
It also says how far back each feed reached, so the gaps can be covered by searching.

**`check_store_dates`** downloads the Switch 2 games of the Nintendo EU, NA and JP stores and lists what changed
since the last snapshot saved with `--save` (new products, new dates, a JP game that now lists a boxed version)
and the title and SKU dates that no longer agree with the EU and NA stores. The snapshot,
`data/nintendo_store_catalog.yaml`, is git-ignored.

Neither `news_candidates` nor `check_store_dates` writes the data files: they point at what to check.

**`download_covers`** looks for the European box of each standard EU SKU without a cover on MediaMarkt Spain. It
takes the first Switch 2 product whose name, without platform, format or genre, is exactly the game's (so a
special edition or another game of the series is not taken), rejects it if its barcode differs from the SKU's,
and keeps the image only if it has the red Nintendo Switch 2 header across its top (another platform's box or
promotional art does not). It stores a 300 px wide WebP in `docs/covers/<sku_id>.webp` and its source in
`data/covers.yaml`; `--refresh` downloads again the ones already there. It stops at the first network error and
keeps what it got. `validate_data` checks that every image has its entry and every entry its image.
