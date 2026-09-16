---
name: investigar-juego
description: TRIGGER cuando se pida investigar el formato físico de uno o varios juegos de Switch 2 de este repo ("investiga donkey-kong-bananza", "busca los SKUs de los pendientes", "qué formato tiene X"). Enruta la búsqueda por publisher y región con un presupuesto fijo por juego, escribe los SKUs con su fuente y deja el trabajo terminado: lo que tiene fuente queda en reviewed y lo buscado sin fuente, en pending.
---

# Investigar el formato físico de un juego

Busca en qué formato salió un juego en cada región y deja el trabajo terminado: los SKUs escritos, con su
fuente citada. La garantía la da **la cita textual**: un dato sin la frase que lo respalda no se escribe.

Hay cientos de juegos: se prima **ir rápido y gastar poco**. Un SKU difícil se deja en `pending` para un
refresh posterior; no se insiste.

## Reglas que no se saltan

1. **Nunca inventar.** Sin fuente, el campo va a `null`. Sin fuente para el formato, `format: unknown` y
   `source_url: null`.
2. **Cita textual obligatoria.** Un dato solo vale si puedes copiar la frase que lo dice. El resumen de
   WebFetch y el de WebSearch no son cita (`SOURCES.md` §12): la frase se saca con `fetch_quote`, o es el
   título literal de un resultado del buscador, marcado `(listado)`.
3. **Con fuente comprobada, `status: reviewed`.** `verified_at` es la fecha en que la has abierto.
4. **Buscado sin fuente, `status: pending`**, con `format: unknown`, `evidence: unconfirmed` y
   `source_url: null` (sale en la web como formato desconocido). Nunca `reviewed` sin `source_url`.
5. **El título también sale de `new`.** `reviewed` si el `igdb_id` es la edición de la caja y `name` y
   `publisher` cuadran; `pending` si no se puede confirmar. Que el juego no haya salido no impide
   `reviewed` si el formato anunciado tiene cita. Solo se toca
   `status` (y el `title_id` de un título `new` sin SKUs).
6. **`SOURCES.md` se actualiza en la misma sesión** si una fuente cambia o se prueba una nueva, con la fecha.
7. Hallazgos de la tanda: **un único comentario** al final en Notion, "Fase 0 — Registro de hallazgos".

## Presupuesto

| Límite | Valor |
|---|---|
| Herramientas por juego | **~8** (sin contar escribir el YAML ni validar) |
| WebSearch por juego | **máximo 3** |
| Intentos por región | **1 fuente**; si no da la cita, el SKU queda `pending` |
| Regiones fuera de la ruta (tabla del paso 3) | **no se buscan ni se escriben** |
| Campos secundarios (EAN, `cart_size_gb`, distribuidora, descarga) | solo si ya salen en lo abierto; **nunca se buscan aparte** |

Cómo no gastar tokens:

- **Nunca volcar HTML ni JSON.** Páginas: `uv run python -m scripts.fetch_quote <url> '<regex>'` (devuelve solo
  los fragmentos; `--raw` para JSON, `--context`, `--max`). APIs: filtrar con `jq` a los campos que hacen falta.
- **No adivinar URLs**: sacarlas del resultado del buscador.
- Si el primer resultado ya responde (no hay caja), **parar ahí**. Que no haya salido no es motivo para parar.

## Paso 0: preparar la tanda

```bash
uv run python -m scripts.next_work --limit 10
```

Empieza por `titles_to_research` (títulos `new`). Antes del primer juego, descarga **una vez por tanda** las
fuentes compartidas al scratchpad y consúltalas con `fetch_quote <fichero>`:

```bash
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
S=<scratchpad>
# Lista de game-key cards (Nintendo Everything): que el juego salga es cita; que no salga, no.
curl -sL -A "$UA" 'https://nintendoeverything.com/list-of-all-nintendo-switch-2-games-with-a-game-key-card-release/' -o $S/gkc.html
# Catálogo de Switch 2 de Nintendo EU: fecha y tamaño de descarga de todos los juegos.
curl -s 'https://searching.nintendo-europe.com/en/select?q=*&fq=type:GAME&fq=playable_on_txt:BEE&rows=2000&wt=json&fl=title,dates_released_dts,datasize_readable_txt,publisher' -o $S/eu.json
jq -c '.response.docs[] | select(.title|test("<nombre>";"i"))' $S/eu.json
```

## Paso 1: triaje (1 WebSearch)

Busca `"<nombre>" Switch 2 physical edition` y decide con los resultados:

- **No hay caja en ninguna región**: entrada en `data/physical_release.yaml`, título `reviewed`. Siguiente.
- **Hay caja (o se ha anunciado)**: apunta las URLs que ya dan formato y sigue al paso 2 por la ruta de su
  publisher.
- **Aún no ha salido**: se busca igual, con el mismo presupuesto. A menudo el anuncio, la reserva de una
  tienda o la prensa ya dicen si será key card o cartucho completo. `release_date` es la fecha anunciada si la
  hay (si no, `null`). Si no aparece el formato, el título queda `pending` sin SKUs, para el refresh.

```yaml
- title_id: "age-twisters"
  has_physical_release: false
  evidence: "official"       # unconfirmed si es "he buscado y no he encontrado nada"
  source_url: "https://..."  # obligatorio salvo evidence: unconfirmed
  checked_at: "2026-09-16"
```

Señales rápidas de "no hay caja": `pprice: null` en la API de Nintendo JP, ninguna tienda con listado físico.

## Paso 2: ruta por publisher

Solo se buscan las regiones de la ruta. Las demás no se escriben (`next_work` ya las lista como pendientes).

| Tipo | Regiones | Fuente de formato por región (1 intento) |
|---|---|---|
| **Nintendo** | EU, NA, JP, KR, ASIA | Se da `full_cart` con la lista de Nintendo Life (EU), Game Rant (NA), AUTOMATON (JP), Danawa (KR) y el título de Play-Asia (ASIA) |
| **Japonés** (Capcom, Sega, Square Enix, Bandai Namco, Koei Tecmo...) | JP, EU, NA; KR y ASIA solo si salen en una búsqueda ya hecha | JP: Famitsu (`パッケージ版（キーカード）`) o AUTOMATON · EU: ficha de Nintendo Life · NA: lista de Nintendo Everything |
| **Occidental** (EA, Ubisoft, IOI, CDPR, Warner...) | EU, NA; JP y ASIA solo si salen en una búsqueda ya hecha | EU: ficha de Nintendo Life (`Physical Release`) · NA: lista de Nintendo Everything o GoNintendo · JP: Famitsu · ASIA: título de Play-Asia |
| **Indie** (Fangamer, Limited Run, Super Rare, Silver Lining...) | Solo las del anuncio del distribuidor | La nota del anuncio (GoNintendo, Nintendo Everything) |

Ficha de Nintendo Life: `https://www.nintendolife.com/games/nintendo-switch-2/<slug>` (el slug con guiones;
si no está en el buscador, no se adivina). Patrón: `fetch_quote <url> 'physical release'`.

Fechas y distribuidora, sin búsqueda extra:

- EU: `eu.json` del paso 0.
- NA: API Algolia (`SOURCES.md` §4.3), con `jq '.hits[] | {title, releaseDate}'`.
- JP: API de Nintendo JP (`SOURCES.md` §4.2), filtrada a `hard == "05_BEE"` y `sform != "DLC"`, campos `title`,
  `icode`, `sdate`, `maker` y `pprice`.

## Paso 3: escribir el SKU

Al final de `data/skus.yaml`, bajo un comentario con el juego. Todas las claves, `null` lo desconocido, y en
cada dato su etiqueta con la cita: `(leída)` página abierta, `(listado)` solo el título del buscador, `(API)`
API pública de Nintendo.

```yaml
# Absolum: cartucho completo; edición física de Silver Lining Interactive.
- sku_id: "eu-absolum-standard"
  title_id: "absolum"
  region: "EU"
  edition: "standard"
  distributor: "Silver Lining Interactive"  # (leída) la nota del anuncio lo firma
  release_date: "2026-03-12"
  format: "full_cart"
  cart_size_gb: null
  download_size_gb: null
  includes_download_code: null
  ean: null
  evidence: "press_report"  # (leída) "full-cartridge physical edition"
  source_url: "https://..."
  verified_at: "2026-09-16"
  status: "reviewed"
```

Recordatorios del modelo (los valida `validate_data`):

- `sku_id` = `{region en minúsculas}-{title_id}-{edition}`; `edition` es `standard` salvo que haya varias.
- `source_url` obligatorio salvo `format: unknown`, y prohibido en los SKUs `pending`.
- `cart_size_gb` solo con `full_cart`; `download_size_gb` nunca con `full_cart`.
- `evidence` describe la fuente: prensa (Nintendo Life, Famitsu, GoNintendo) es `press_report`, aunque cite al
  publisher; `official` solo para la web o la nota del propio Nintendo o publisher.
- El EAN entre comillas; el dígito de control se comprueba solo.

## Paso 4: cerrar la tanda

```bash
uv run python -m scripts.validate_data
```

Resumen breve: qué títulos pasan a `reviewed` y cuáles a `pending`, qué SKUs quedan en `pending` para el
refresh, y cualquier fuente nueva o cambiada (ya anotada en `SOURCES.md`). Después, el comentario en Notion.
