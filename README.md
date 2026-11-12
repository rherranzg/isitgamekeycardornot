# Is It Game-Key Card Or Not?

An open database of the physical format of Nintendo Switch 2 games, region by region and edition by edition.

**Browse it: https://isitgamekeycardornot.com/**

## Why it matters

Many Switch 2 boxes do not hold the game. A **Game-Key Card** is a cartridge that only works as a key: the game
has to be downloaded first, which needs an internet connection and free storage, and the card must be inserted
to play. The same game can come as a full cartridge in one region and as a Game-Key Card in another, or change
between its standard and special editions.

This site tells you, box by box, what you actually get, and links the source that says so.

## What is in the box

| Format | What you get |
|---|---|
| **Full cartridge** | The whole game is on the cartridge. |
| **Game-Key Card** | The cartridge is a key: the game is downloaded, and the card must be inserted to play. |
| **Code in box** | A download code, with no game card. |

Two more values describe how much is known, not a format:

- **Unknown**: the box exists, but no source stating its format has been found yet.
- **No physical edition**: no boxed release was found. "Digital only" is shown only when a source says so.

Each regional box is listed separately, as a **SKU** (one region and edition of a game).

## Where the data comes from

Every SKU links to the **public source** it is based on: a Nintendo or publisher page, a press article, a
retailer listing or a photo of the box. The site shows which kind of source each one is.

If there is no source, the value is left empty or the format is shown as unknown. Nothing is guessed.

Game names, publishers and release dates come from [IGDB](https://www.igdb.com).

**Mistakes are possible.** Formats change between announcement and release, and retailer listings can be
wrong. Check before you buy, and if you find an error, please report it.

## Report a correction

Open an issue with the
[correction form](https://github.com/rherranzg/isitgamekeycardornot/issues/new?template=correction.yml), or
from the "Spotted a mistake?" link under each game on the site, which fills in the game for you. The one thing
it needs is a **source**: a link to a page that states it, or a photo of the box.

A game is missing? Use the same form. For a question, open a
[regular issue](https://github.com/rherranzg/isitgamekeycardornot/issues/new).

Pull requests that edit the data directly are welcome too: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Using the data

The data is plain YAML in [`data/`](data/). Each file can be downloaded directly from
`https://raw.githubusercontent.com/rherranzg/isitgamekeycardornot/main/data/<file>.yaml`.

| File | What it holds |
|---|---|
| `titles.yaml` | Every known Switch 2 game: `title_id`, `igdb_id`, `name`, `publisher`, `release_date` (first Switch 2 release, digital or boxed). |
| `skus.yaml` | One entry per region and edition of a game (fields below). |
| `physical_release.yaml` | Games checked for a boxed edition that has not turned up, worldwide or in one region, with their source when there is one. |
| `covers.yaml` | The European box front of each standard SKU that has one, stored as `docs/covers/<sku_id>.webp`, with the page it comes from. |
| `excluded_titles.yaml` | IGDB entries deliberately not listed (editions covered by their base game, games only sold inside a compilation...). |

### SKU fields

| Field | Values |
|---|---|
| `sku_id` | `<region>-<title_id>-<edition>`, lowercase, e.g. `eu-mario-kart-world-standard`. |
| `title_id` | The game in `titles.yaml`. |
| `region` | `EU`, `NA`, `JP`, `KR` or `ASIA` (Hong Kong, Taiwan and Southeast Asia). |
| `edition` | `standard`, `deluxe` (extra content, SteelBook...) or `collectors` (Collector's, Limited, Premium, a box with goodies). |
| `edition_name` | The commercial name ("Gold Edition"); `null` for the standard edition. |
| `format` | `full_cart`, `game_key_card`, `code_in_box` or `unknown`. |
| `distributor` | Who sells the box in that market. |
| `release_date` | Release date of the box in that market. |
| `cart_size_gb` | Cartridge capacity, for full cartridges. |
| `download_size_gb` | Approximate download needed, for Game-Key Cards and codes in box. |
| `includes_download_code` | `true` if the box also carries a code (DLC, season pass...). |
| `ean` | EAN-13 or UPC-A barcode, as a string. |
| `evidence` | Kind of source: `official`, `box_photo`, `press_report`, `retailer_listing` or `unconfirmed`. |
| `source_url` | The source that backs the format; `null` when the format is `unknown`. |
| `updates` | Later sources that changed the SKU (a delay, a format change...), oldest first, each with `url`, `checked_at` and `fields`. |
| `verified_at` | When the source was last checked. |

Every key is always present; an unknown value is `null`. A fictitious example:

```yaml
- sku_id: "eu-example-game-standard"
  title_id: "example-game"
  region: "EU"
  edition: "standard"
  edition_name: null
  distributor: "Example Distributor"
  release_date: "2026-03-12"
  format: "game_key_card"
  cart_size_gb: null
  download_size_gb: 12.5
  includes_download_code: false
  ean: "0045496123456"
  evidence: "official"
  source_url: "https://example.com/..."
  verified_at: "2026-09-13"
```

For example, to list the Game-Key Cards sold in Europe (with [PyYAML](https://pypi.org/project/PyYAML/)):

```python
import urllib.request

import yaml

URL = "https://raw.githubusercontent.com/rherranzg/isitgamekeycardornot/main/data/skus.yaml"
skus = yaml.safe_load(urllib.request.urlopen(URL))
print([s["sku_id"] for s in skus if s["region"] == "EU" and s["format"] == "game_key_card"])
```

The comment above each entry quotes the exact sentence of the source that backs it, tagged by how the source
was read: `(leída)` (the page was opened and read), `(listado)` (only the title of a search or retailer
result was visible) or `(API)` (a store's data feed). These comments are written in Spanish; the quotes keep the
language of their source.

Each game on the site can be linked with `https://isitgamekeycardornot.com/#<title_id>`. A `title_id` never
changes once published; when two games are merged, the old link still leads to the merged one.

## License

- Code: MIT (see [`LICENSE`](LICENSE)).
- Data: [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), except the IGDB metadata and the quoted
  excerpts (see [`data/LICENSE`](data/LICENSE)).
- Box covers (`docs/covers/`): they belong to their publishers and are not covered by either license; each one
  links to the page it comes from. If you own one and want it removed, open an issue.

Nintendo, Nintendo Switch 2 and Game-Key Card are trademarks of Nintendo. This is an independent project, not
affiliated with or endorsed by Nintendo.

## For maintainers

Setup, the research workflow, data rules and every command are in [`WORKFLOW.md`](WORKFLOW.md).
