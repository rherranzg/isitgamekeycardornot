# Fuentes de datos de terceros

Catálogo de todas las webs y APIs de terceros que se han probado para rellenar `titles.yaml` y `skus.yaml`: cómo
se consultan, qué devuelven, para qué sirven y dónde fallan.

**Mantenimiento**: cada vez que se pruebe una fuente nueva, o se descubra algo de una existente (un campo, un
bloqueo, un límite, un cambio de endpoint), se actualiza este fichero en la misma sesión, con la fecha de la
prueba. Lo no probado se marca como tal. Las decisiones y el contexto de cada investigación están además en
Notion ("Switch 2 Physical Format DB — Plan de acción" y su subpágina "Fase 0 — Registro de hallazgos").

Leyenda del estado: ✅ probada y útil · ⚠️ probada con limitaciones · ❌ probada e inservible o bloqueada ·
❔ sin probar.

---

## 1. Conclusiones rápidas

- **Ninguna fuente estructurada dice si un juego es game-key card o cartucho completo.** Ni IGDB ni las APIs
  públicas de Nintendo (EU, JP, US, HK). El formato sale de prensa, de fichas o títulos de tiendas y de fotos
  de la caja.
- **Los first-party de Nintendo llevan el juego completo en el cartucho** en todas las regiones, según la prensa
  (Game Rant, Nintendo Life, TheGamer). En Japón lo confirma AUTOMATON. Comprobado región a región con DK
  Bananza, Mario Kart World y Metroid Prime 4: Beyond: **ninguna divergencia regional en first-party**.
- **Las "Nintendo Switch 2 Edition" en caja llevan también el juego base y la mejora en la tarjeta**, por
  declaración de Nintendo (§7, Nintendo Everything / VGC): "they are exclusively Nintendo Switch 2 game cards,
  with no download code". **Ojo: esto es la política general, no una cita por juego.** El mismo artículo
  matiza que no es universal: "some publishers may release Nintendo Switch 2 Edition games as download codes
  in physical packaging, with no game card" (nintendoeverything.com/nintendo-confirms-physical-switch-2-editions-have-everything-on-the-cartridge-no-downloads/,
  leída 16-09-2026). No sirve como cita para el formato de un "Switch 2 Edition" de un publisher concreto:
  hace falta la ficha o la prensa de ESE juego (probado con A-Train de Artdink, §7: ni la ficha oficial ni
  Nintendo Everything ni Nintendo UK dicen el formato, así que quedó `pending`).
- **El tamaño del cartucho (`cart_size_gb`) no tiene fuente pública por juego.** Nintendo no lo publica.
  Solo aparece cuando el publisher lo dice (Cyberpunk: 64 GB, vía Play-Asia blog).
- **Las APIs de Nintendo sí sirven para campos secundarios**: fecha de lanzamiento, maker/publisher, tamaño
  digital, código de producto y si existe versión en caja (solo JP).
- **Las tiendas bloquean la lectura automática (403)**: Play-Asia, HobbyDigi, Japanzon, QVC y otras. De ellas
  solo se puede usar el título del listado que muestra el buscador, marcado como `(listado)`. Muchas de las
  que bloqueaban a WebFetch **sí se leen con curl y un User-Agent de navegador** (§3.1); Play-Asia y GameSpot,
  no.
- **Los códigos de barras**: en NA vía UPCitemdb; en JP, el JAN aparece en la URL de muchas tiendas; en EU y KR
  no se ha encontrado nada.
- **La divergencia región↔formato no siempre es "Occidente game-key, Japón cartucho completo"**: puede ser al
  revés. Confirmado con cita textual (17-09-2026): **Daemon X Machina: Titanic Scion** ("a Game-key card
  release in Japan, but a regular game card release in the West") y **Brigandine Abyss** ("the western release
  from NIS America is a game-key card", con el asiático en cartucho completo). No asumir el patrón habitual sin
  comprobar cada región.
- **La prensa a veces solo especula y lo escribe con matices ("seemingly implying", "expected to be", "could
  also be a placeholder")**: eso no es cita válida del formato, aunque el titular del artículo lo dé por hecho.
  Pasó con Bubsy 4D (Nintendo Life) y Crisis Core Reunion (xeznaff.com): en ambos casos el propio texto
  reconoce que no está confirmado, así que el SKU queda `pending` con `format: unknown` en vez de asumir
  `full_cart`.
- **Una edición cuyo propio nombre dice "Digital Deluxe"/"Digital Ultimate"** (p. ej. Digimon Story Time
  Stranger: Deluxe/Ultimate Edition, Dragon Quest VII: Reimagined - Digital Deluxe Edition) suele ser un
  bundle solo de eShop sin SKU físico propio, distinto de la edición "Standard" del mismo juego que sí puede
  tener cartucho. El nombre no es una cita del formato, pero es una señal fuerte para no perder tiempo
  buscando físico de esas ediciones concretas (17-09-2026).

## 2. Qué fuente usar para cada campo

| Campo | EU | NA | JP | KR | ASIA |
|---|---|---|---|---|---|
| `format` | Prensa (Nintendo Life, VGC) | Prensa (Game Rant, GoNintendo, GameSpot), QVC | Prensa (AUTOMATON, Famitsu, VGC), Tokyo Game Story | Danawa (título del producto) | Play-Asia, PLAYe, GameShop Asia (títulos) |
| `release_date` | API Nintendo EU | API Algolia NA | API Nintendo JP | Web oficial Nintendo KR | Web oficial Nintendo HK |
| `distributor` | — | — | API Nintendo JP (`maker`), tiendas JP | ❔ GRAC | — |
| `ean` | ❌ sin fuente | UPCitemdb | JAN en URLs de tiendas JP | ❌ sin fuente | URL de HobbyDigi |
| `cart_size_gb` | Publisher / prensa puntual | ídem | ídem | ídem | ídem |
| `download_size_gb` (solo key card / code in box) | API Nintendo EU (`datasize_readable_txt`) | ficha de la eShop US | Famitsu, My Nintendo JP vía prensa | — | — |
| `includes_download_code` | Prensa (EventHubs, GoNintendo) | ídem | — | — | — |

`download_size_gb` no se rellena en `full_cart`: ahí el juego va en el cartucho y la web mostraría una descarga
que no existe.

## 3. Receta que funcionó (Donkey Kong Bananza, 15-09-2026)

1. **API de Nintendo JP** con el nombre japonés (`q=`): da `icode` (p. ej. `AAACA`), `sdate`, `maker` y `pprice`
   (si no es null, hay パッケージ版). El nombre japonés sale de Wikipedia o de la web oficial.
2. **Con el `icode`**, abrir las webs oficiales asiáticas, que comparten el patrón de URL:
   `nintendo.com/{jp,kr,hk,sg,my}/games/switch2/{icode en minúsculas}/`. Dan la fecha y el precio de la caja
   por región.
3. **API de Nintendo EU (Solr)** con el nombre en inglés: fecha, tamaño digital, publisher y a veces el código
   de producto.
4. **API Algolia de Nintendo NA**: fecha y publisher.
5. **Formato**:
   - First-party: lista "full game on the cart" de Nintendo Life (EU), Game Rant (NA), AUTOMATON (JP), Danawa
     (KR) y el título de Play-Asia (ASIA).
   - Third-party: VGC, las listas de game-key cards de Nintendo Life y Nintendo Everything, y títulos de
     tiendas.
6. **Códigos de barras**:
   - NA: UPCitemdb, buscando por título.
   - JP: buscar `"<nombre japonés> JAN 4902370"` (prefijo de Nintendo JP) y leer el JAN de las URLs de Rakuten
     Books, AEON o SoftBank Selection.
   - ASIA: el código en la URL de HobbyDigi.
7. **Anotar cada dato** en el YAML con `(leída)`, `(listado)` o `(API)`, y el texto citado.

## 3.1. `curl` con User-Agent de navegador ✅ (probado 16-09-2026)

Casi todas las webs que devolvían 403 a WebFetch **se leen enteras con curl** poniendo un User-Agent de
navegador, y así se trabaja sobre el HTML real en vez de sobre un resumen (§12):

```bash
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
curl -sL -A "$UA" 'https://prod.danawa.com/info/?pcode=88136987'
```

- Funcionan así: `nintendo.com/{jp,kr,hk,sg,my}`, Nintendo Life (guías y fichas de juego), AUTOMATON (también
  su buscador `?s=`), Danawa (y su buscador `search.danawa.com/dsearch.php?k1=`), Nintendo Everything,
  GoNintendo, TheGamer y Deku Deals.
- **Siguen bloqueadas por Cloudflare aun con UA**: Play-Asia y GameSpot (ambas 403 / "Just a moment...").

Para no volcar el HTML entero, `uv run python -m scripts.fetch_quote <url|fichero> '<regex>'` hace esa misma
descarga, quita scripts y etiquetas, y devuelve solo los fragmentos que coinciden (probado 16-09-2026 con la
ficha de Nintendo Life y Famitsu). Las listas que sirven para muchos juegos (game-key cards de Nintendo
Everything, catálogo de la API EU con `fl=title,dates_released_dts,datasize_readable_txt,publisher`, 89 KB
para 587 juegos) se descargan una vez por tanda al scratchpad y se consultan en local.

## 3.2. Buscadores web ❌ (probado 16-09-2026)

DuckDuckGo (`html.duckduckgo.com/html/` y `lite.duckduckgo.com/lite/`) responde 202 con una página de anomalía,
y Mojeek devuelve un captcha. **No se puede buscar con curl**: hay que usar la herramienta WebSearch. Los
buscadores internos de cada web (AUTOMATON, Danawa, Game Rant, Nintendo Everything) sí funcionan y son más
fiables cuando ya se sabe dónde mirar.

## 4. APIs públicas de Nintendo (no oficiales)

No están documentadas: pueden cambiar o romperse sin aviso y su uso puede chocar con los términos de Nintendo.
Sirven para investigar a mano; si se integran en un script, hay que tratarlo como una fuente frágil.

### 4.1 Nintendo Europa — Solr ✅⚠️ (probada 15-09-2026)

```bash
# Por nombre
curl -s 'https://searching.nintendo-europe.com/en/select?q=bananza&fq=type:GAME&rows=5&wt=json'
# Todo el catálogo de Switch 2 (584 juegos el 15-09-2026)
curl -s 'https://searching.nintendo-europe.com/en/select?q=*&fq=type:GAME&fq=playable_on_txt:BEE&rows=1000&wt=json'
```

- Respuesta: `response.docs[]`. Locale `en` (Reino Unido); los demás locales no se han probado.
- Campos útiles:
  - Fecha: `dates_released_dts` (varias fechas si hay bundle o DLC; la primera es la del juego).
  - Tamaño digital: `datasize_readable_txt` (p. ej. `["9.0 GB"]`).
  - Publisher y desarrollo: `publisher`, `developer`.
  - Código de producto: `product_code_txt` / `product_code_ss` (p. ej. `BEE-P-AAGRA`); no todos lo tienen.
  - Identificadores y ficha: `nsuid_txt`, `fs_id`, `url` (ficha en nintendo.com/en-gb), `pretty_agerating_s`.
  - Idiomas: `language_availability`.
- Limitaciones:
  - `physical_version_b` es `False` en los 584 juegos, así que **no indica si existe versión física**.
    `digital_version_b` tampoco es fiable.
  - El filtro `fq=type:GAME AND system_names_txt:"Nintendo Switch 2"` devuelve 0 resultados; hay que usar
    `playable_on_txt:BEE`.
  - Algunos títulos llevan otro nombre: "Metroid Prime 4: Beyond – Nintendo Switch 2 Edition",
    "ELDEN RING Tarnished Edition", "Star Wars Outlaws Gold Edition".

### 4.2 Nintendo Japón — search.nintendo.jp ✅⚠️ (probada 15-09-2026)

```bash
# El término va URL-encoded. Usar siempre --compressed: los errores llegan en gzip.
curl -s --compressed 'https://search.nintendo.jp/nintendo_soft/search.json?q=%E3%83%90%E3%83%8A%E3%83%B3%E3%82%B6&limit=20'
```

- Respuesta: `result.total` y `result.items[]`. Hay que filtrar en cliente por `hard == "05_BEE"` (Switch 2).
- Campos útiles:
  - Código y título: `icode` (código de producto sin prefijo: `AAACA` → `BEE-P-AAACA`), `title`, `nsuid`.
  - Fecha: `sdate` (`"2025.7.17"`).
  - Distribuidora en JP: `maker` (`任天堂`, `セガ`, `カプコン`...).
  - Precios: `pprice` (precio de la パッケージ版; `None` si solo es digital) y `dprice` (digital).
  - Tipo de producto: `sform` / `sform_n` (`BEE_DOWNLOADABLE` = "パッケージ版／ダウンロード版"; `DL_DLC` =
    set digital; `DLC`) y `sctg` (`dl_soft`, `bundle`).
  - Otros: `lang`, `url` (ficha oficial).
- Limitaciones:
  - `sform_n` es idéntico en Yakuza 0 DC (キーカード) y en Cyberpunk (cartucho), así que **no distingue el
    formato**.
  - `fq=hard:05_BEE` y `fq=hard:"05_BEE"` devuelven HTTP 500. Solo funciona `q=`.
  - Sin JAN, tamaño ni idiomas de la caja.

### 4.3 Nintendo of America — Algolia ✅⚠️ (probada 15-09-2026)

```bash
curl -s -X POST 'https://U3B6GR4UA3-dsn.algolia.net/1/indexes/store_game_en_us/query' \
  -H 'X-Algolia-Application-Id: U3B6GR4UA3' \
  -H 'X-Algolia-API-Key: a29c6927638bfd8cee23993e51e721c9' \
  -d '{"query":"donkey kong bananza","hitsPerPage":5,"filters":"corePlatforms:'"'"'Nintendo Switch 2'"'"'"}'
```

- La clave es la de solo búsqueda que usa el frontend de nintendo.com; si deja de funcionar, se saca de nuevo
  del JavaScript de la web.
- Campos útiles:
  - Título y fecha: `title`, `releaseDate`.
  - Compañías: `softwarePublisher` (`softwareDeveloper` suele venir null).
  - Identificadores y ficha: `nsuid`, `sku`, `urlKey` (ficha `nintendo.com/us/store/products/{urlKey}/`).
  - Clasificación: `contentRating`.
  - Tipo de producto: `eshopDetails.productType` (`TITLE` / `BUNDLE`), `dlcType`.
- Limitaciones:
  - `editions` (`Digital`, `Physical`) **no es fiable**: Yakuza 0 DC y Cyberpunk salen solo como `Digital`
    aunque tienen caja en NA.
  - Sin UPC, formato ni tamaño (el tamaño está en la ficha HTML: "File size 9 GB").

### 4.4 Nintendo Hong Kong — JSON ❌ para Switch 2 (probada 15-09-2026)

```bash
curl -sL 'https://www.nintendo.com.hk/data/json/switch_software.json'   # -L: 301 a nintendo.com/hk/...
```

- 544 entradas, **todas de Switch 1**. Tiene `media` (`package` / `eshop`), `product_code`, `release_date`,
  `maker_publisher` y `price`.
- Se probaron `switch2_software.json`, `switch_2_software.json` y `ns2_software.json`: todas dan 404.

### 4.5 Webs oficiales de Nintendo (HTML)

| Web | URL | Qué da | Estado |
|---|---|---|---|
| Japón | `nintendo.com/jp/games/switch2/{icode}/index.html` | Fecha, precio パッケージ版 y ダウンロード版 | ✅ Sin JAN, tamaño ni tipo de tarjeta |
| Corea | `nintendo.com/kr/games/switch2/{icode}/` | 발매일, precio 패키지 버전 | ✅ No indica la distribuidora de forma explícita. **En las "Switch 2 Edition" la ficha no trae ni fecha ni precio** (comprobado con Metroid Prime 4, `BGW5A`, 16-09-2026): la fecha hay que sacarla de Danawa |
| Hong Kong | `nintendo.com/hk/games/switch2/{icode}/index.html` | 發售日, precio de la caja en HKD | ✅ En las "Switch 2 Edition" solo da el precio 盒裝版, sin 發售日 (Metroid Prime 4, 16-09-2026) |
| Singapur / Malasia | `nintendo.com/{sg,my}/games/switch2/{icode}/index.html` | Fecha; enlaza a Shopee/Lazada | ⚠️ Sin precio |
| Reino Unido | `nintendo.com/en-gb/Games/Nintendo-Switch-2-games/{Nombre}-{fs_id}.html` | Fecha, PEGI | ⚠️ WebFetch la trunca; mejor la API Solr |
| EE. UU. | `nintendo.com/us/store/products/{urlKey}/` | Fecha, publisher, tamaño, idiomas | ⚠️ El resumen de WebFetch dijo que no hay versión física (falso). Con `fetch_quote <url> 'Edition \| Digital'` sí sale una cita fiable: el campo "Version \| Nintendo Switch 2 \| Edition \| Digital" marca que la ficha es solo digital (probado con Dream Shogi 4K, 17-09-2026) |
| Japón: キーカード | `nintendo.com/jp/games/switch2/key-card/index.html` | Explica que la caja de una キーカード lo avisa en la portada y la tarjeta lleva un candado arriba a la derecha | ❌ No lista títulos |
| Japón: lineup | `nintendo.com/jp/games/switch2/lineup/index.html` | — | ❔ Sin revisar si marca las キーカード o carga un JSON |

Cuando el juego no se lanzó en esa región, la ficha da 404 (no una página vacía): comprobado con Hitman World
of Assassination – Signature Edition (`icode` `AAM3A`) en `kr`, `hk`, `sg` y `my`, sin ficha en ninguna de las
cuatro (16-09-2026), coincidiendo con que tampoco aparece en Danawa. Es una señal más de "no hay edición en
esa región", no solo de que la URL esté mal construida.

## 5. Códigos de barras

### 5.1 UPCitemdb ✅⚠️ (probada 15-09-2026)

```bash
curl -s 'https://api.upcitemdb.com/prod/trial/lookup?upc=0045496905576'
curl -s 'https://api.upcitemdb.com/prod/trial/search?s=donkey%20kong%20bananza&match_mode=0&type=product'
```

- Plan de prueba sin clave: **100 peticiones al día** (cabecera `X-RateLimit-Limit: 100`); la búsqueda también
  cuenta.
- Devuelve `ean`, `title` y `offers[]` con `domain` y título de cada tienda. Casi todo son tiendas de EE. UU. y
  Canadá (walmart, target, gamestop, walmart.ca), así que **solo sirve para NA**.
- Hay que filtrar: la búsqueda mezcla códigos digitales (`(Digital)`), amiibo y merchandising.
- Puede haber varios UPC para el mismo juego. DK Bananza: `0045496905576` (GameStop, Target, Walmart
  "U.S. Version", Walmart.ca, Dell) y `0045496312763` (solo Walmart). Si se contradicen, se elige el que listan
  más tiendas y se anota el otro.
- Prefijo de Nintendo NA: `045496` (EAN `0045496…`).
- **No todos los juegos están**: de Mario Kart World solo aparece `0045496905460`, titulado
  "(CAN Version)" y listado solo por Walmart US/CA, así que es el SKU canadiense y no vale como EAN de NA
  (16-09-2026). Metroid Prime 4 sí: `0045496905613` en GameStop, Target, Walmart, Dell, GameFly y
  Books-A-Million.

### 5.2 JAN japonés en URLs de tiendas ✅ (13 y 15-09-2026)

- Muchas tiendas japonesas llevan el JAN en la URL o en el título: Rakuten Books, AEON Style Online, SoftBank
  Selection, Japanzon, Tokyo Game Story.
- Búsqueda que funciona: `"<nombre japonés> パッケージ版 JAN 4902370"`. `4902370` es el prefijo de Nintendo JP;
  en juegos de otros publishers se usa el suyo (Sega `4974365`, Spike Chunsoft `4940261`).
- Se anota como `(listado)`: la ficha no suele poder abrirse. Rakuten Books devolvió una página de "no
  encontrado" a WebFetch.

### 5.3 Otras

- **EAN-Search** (`ean-search.org`) ❌: el HTML respondió con cuerpo vacío a curl; la API es de pago.
- **HobbyDigi** (HK) ⚠️: la URL es el propio código de barras (`hobbydigi.com/en_us/4711279510645`, "[Asia Ver]").
  Devuelve 403.
- EU y KR: sin fuente de EAN encontrada.

## 6. Tiendas

| Tienda | Región | Acceso | Qué aporta | Nombres de formato en el título |
|---|---|---|---|---|
| Play-Asia | ASIA / JP | ❌ 403 | Formato, versión de región | "Game Cart" frente a "Game Key Cart"; "(Multi-Language)" suele ser la versión asiática |
| Play-Asia blog | — | ⚠️ solo título/resumen | Tamaño del cartucho (Cyberpunk 64 GB) | — |
| PLAYe | ASIA | ⚠️ solo título | Formato, fecha | "(Asia) (Game-Key Card)" |
| GameShop Asia | ASIA | ⚠️ solo título | Versión Asia | — |
| HobbyDigi | HK | ❌ 403 | Código de barras en la URL | "[Asia Ver]" |
| Japanzon | JP | ❌ 403 | Distribuidora, JAN en la URL | — |
| Tokyo Game Story | JP | ⚠️ solo título | Formato, JAN en la URL | "(KEY CARD)" |
| Rakuten Books / AEON / SoftBank Selection | JP | ⚠️ título y URL | JAN | — |
| Yamada Denki | JP | ❌ timeout de 60 s | — | — |
| QVC | NA | ❌ 403 | Formato | "(Game-Key Card)" |
| Best Buy | NA | ❔ | Aviso "GAME CARD NOT INCLUDED" para code-in-box (vía GoNintendo) | — |
| Danawa | KR | ✅ legible | Formato, fecha | "패키지칩" (chip en caja) |
| univstore | KR | ✅ legible | Formato, precio | "게임 칩 팩" |
| VideoGamesPlus.ca | NA (Canadá) | ⚠️ solo título, vía WebSearch (17-09) | Formato | "[Game-Key Card] - Nintendo Switch 2" en el título del producto, igual que Play-Asia; no probado con curl directo |
| hit.co.uk | UK | ⚠️ legible | Fecha | El resumen afirmó "not a key card" sin cita: no fiable |
| Smyths, Currys, John Lewis, Amazon UK | UK | ❔ | — | — |

Con `User-Agent` de navegador (§3.1) **Danawa y Tokyo Game Story se leen enteras**, pero Play-Asia sigue
devolviendo 403 de Cloudflare: de ella solo se puede usar el título del listado que muestra el buscador.
Formatos vistos en los títulos de Tokyo Game Story: `(GAME CART)` para el cartucho completo frente a
`(KEY CARD)`, y el JAN va en la URL (`...-game-cart-multilingualfps-new-4902370553727.html`).

## 7. Prensa y listas

| Fuente | Región | Estado | Uso |
|---|---|---|---|
| VGC | JP / occidente | ✅ leída (13-09) | Lista de third-party con game-key card en Japón; citas de publishers (CD Projekt: "contained entirely on the cartridge") |
| Nintendo Life: juegos con el juego completo en el cartucho | EU/UK | ✅ leída (16-09) | Formato `full_cart` por título, sin distinción regional. Solo admite confirmaciones oficiales: "we won't be relying on retailer listings alone" |
| Nintendo Life: ficha de cada juego | EU/UK | ⚠️ leída (16-09, 17-09) | Campo **"Physical Release"** con el formato (`Standard Game Card`), fecha y precio en $ y £. URL: `nintendolife.com/games/nintendo-switch-2/{slug}` (el slug no se adivina: hay que sacarlo del buscador). **El campo no siempre está**: en la ficha de AFL 26 solo hay "Release Date", sin "Physical Release". Cuando sí está y el juego es solo digital, el valor literal es `Physical Release \| None (Digital Only)` (confirmado en Arcade Archives 2: Ridge Racer, Air Combat 22, Cyber Commando, Gee Bee, y también en **Drag x Drive**, first-party de Nintendo: la asunción "first-party siempre full_cart" tiene excepciones, hay que comprobar cada juego). Cuando sí está y es un cartucho, el mismo campo (`Physical Release \| Game-Key Card`) suele valer para EU y NA a la vez si la ficha trae precio en $ y en £ con la misma fecha. Sirve como cita `press_report` para `physical_release.yaml`. Su ausencia **no** es cita de "sin físico" (solo pasa a `unconfirmed`) |
| Nintendo Life: slug de fichas con nombre de caja distinto del título base | EU/UK | ⚠️ (17-09) | El slug de la ficha sigue el **nombre comercial de la caja**, no siempre el `name` de IGDB: `devil-may-cry-5-devil-hunter-edition` (no `devil-may-cry-5`), `dragons-dogma-2-dark-arisen` (no `dragons-dogma-ii`), `dragon-quest-i-and-ii-hd-2d-remake` (un solo producto físico para dos títulos separados de IGDB, `dragon-quest-i-hd-2d-remake` y `dragon-quest-ii-hd-2d-remake`) y slugs con guion bajo/final `dragon_quest_heroes_tornekos_mystery_dungeon_-classic_hd-`. **No adivinar el slug a pelo con el nombre de IGDB**: sale 404. Mejor sacarlo del buscador o, si no hay resultado directo, probar variantes razonables con `curl -o /dev/null -w '%{http_code}'` antes de darlo por inexistente |
| Nintendo Life: "Upgrade Path" en vez de "Physical Release" | EU/UK | ✅ (17-09) | En las Switch 2 Edition que son solo una actualización digital gratuita de un juego de Switch 1 (no un producto nuevo), la ficha no trae "Physical Release" sino `Upgrade Path \| Via <Juego> (Switch eShop) \| Free — Free — Free`: pista fuerte (aunque no cita literal de "sin físico") de que no hay SKU propio de Switch 2. Visto en Dinkum, Disney Dreamlight Valley y Disney Speedstorm |
| Nintendo Life: listado de una serie (`games/browse?title=series%3A{slug-de-serie}`) | — | ⚠️ leída (17-09) | Devuelve en el HTML (sin JS) un lote de `games/nintendo-switch-2/{slug}` de la serie, p.ej. `series%3Aarcade-archives-2`: útil para sacar slugs sin adivinarlos ni gastar una búsqueda por juego, pero **no es exhaustivo** — parece limitado a ~46 resultados (¿"load more" por JS?): en dos tandas se quedaron fuera títulos que sí tienen ficha (`ridge-racer`, `rave-racer`). Si un slug obvio no aparece en el listado, **comprobarlo igualmente con un `curl -o /dev/null -w '%{http_code}'` directo** antes de darlo por inexistente. Cuidado también con la ortografía del slug: Nintendo Life a veces omite guiones en compuestos (`rackem-up`, no `rack-em-up`; `rocn-rope`, no `roc-n-rope`). Tres títulos de nuestras tandas (`arkanoid-revenge-of-doh`, `cyber-cycles`, `munch-mobile`, `ninja-emaki`, `pinball-action`) no tienen ficha real en Nintendo Life (404 comprobado): para esos, sin fuente → `unconfirmed` |
| Nintendo Life: juegos con game-key card | EU/UK | ❌ (17-09) | `nintendolife.com/guides/every-nintendo-switch-2-game-key-card-release`: la cabecera y el nav se leen con `fetch_quote`, pero la lista de juegos la pinta JavaScript, igual que Deku Deals — el HTML no trae ningún nombre |
| Nintendo Everything: lista de game-key cards | NA | ✅ leída (16-09) | `nintendoeverything.com/list-of-all-nintendo-switch-2-games-with-a-game-key-card-release/` (la actualizan; revisada el 07-09-2026). Sirve para descartar, no para afirmar: que un juego no salga ahí no es cita |
| Nintendo Everything: Switch 2 Editions enteras en la tarjeta | NA | ✅ leída (16-09) | Cita la declaración de Nintendo: "physical versions of Nintendo Switch 2 Edition games will include the original Nintendo Switch game and its upgrade pack all on the same game card (i.e. they are exclusively Nintendo Switch 2 game cards, with no download code)" |
| TheGamer | NA | ✅ leída (16-09) | "Nintendo's First-Party Switch 2 Games Won't Use Game-Key Cards"; un representante de Nintendo UK dice que no hay "no plans" de usarlas en first-party |
| Nintendo Wire: todos los físicos y su tipo | NA | ❌ 403 | Cartucho / key card / código por juego |
| Deku Deals: lista "Switch 2 Physical Games" | NA/EU | ⚠️ (16-09) | El texto de la lista sirve ("These Switch 2 games are on the game card, and are not a Game-Key Card release") pero **los nombres los pinta JavaScript**: el HTML no trae ninguno. Las fichas `/items/{slug}` tampoco dicen el formato |
| GameSpot | NA | ❌ 403 (16-09) | Su galería "These Nintendo Switch 2 Titles Have The Full Game On The Game Card" sería ideal, pero Cloudflare la bloquea a WebFetch **y a curl con User-Agent** |
| Game Rant | NA | ✅ leída (15-09) | "DK Bananza's physical version is not a Game Key Card". Su buscador (`gamerant.com/search/?q=`) se lee, pero no tiene artículos de formato de Mario Kart World ni de Metroid Prime 4 |
| GoNintendo | NA | ✅ leída (16-09) | El cuerpo del artículo se lee entero con `fetch_quote` (no hace falta quedarse en el título/resumen): AFL 26 — "this physical release will be a Game-Key Card" |
| Limited Run Games (ficha de producto) | NA (tienda propia, "region-free") | ✅ leída (16-09) | `limitedrungames.com/products/{slug}` se lee con `fetch_quote`. Da "Estimated Ship Date" (rango, no fecha fija) y si el producto es "region-free", pero **no dice si es cartucho completo o game-key card**: probado con Alien: Rogue Incursion Evolved Edition |
| EventHubs | NA | ⚠️ resumen | Caducidad del código de DLC de SF6 |
| Gematsu (X) | — | ⚠️ | Divergencias regionales (Daemon X Machina) |
| AUTOMATON | JP | ✅ leída (16-09) | El artículo de las キーカード (24-04-2025) también sirve para Mario Kart World: "任天堂のタイトルなど…通常のゲームカードを採用しているパッケージ版タイトルも存在。たとえば『マリオカート ワールド』はそのひとつ". No cubre Metroid Prime 4. Buscador propio: `automaton-media.com/?s=` |
| Famitsu | JP | ⚠️ resumen | パッケージ版 como キーカード, espacio libre necesario |
| Web oficial del publisher (p.ej. `artdink.co.jp`) | JP | ⚠️ probada (16-09) | Ficha de producto con メディア/価格/発売日, pero **no siempre dice si es キーカード**: la de A-Train (`artdink.co.jp/japanese/title/a-tourism/info/sw2.html`) solo pone "パッケージ（ガイドブックパック）", sin especificar el tipo de cartucho |
| Game*Spark, GameWith, Game8 | JP | ⚠️ resumen | Tamaño digital (DK: de 10 GB a 8,5 GB) |
| RPG Site, Nintendo Insider | — | ❔ | Listas de físicos completos |
| Tom's Hardware, TweakTown | — | ⚠️ | Capacidades de cartucho disponibles en general (rumores), no por juego |

## 8. IGDB (integrada en el código)

- Autenticación por Twitch (`TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` en `.env`), OAuth `client_credentials`.
  El `client_secret` va en el cuerpo del POST, nunca en la URL.
- Consultas en APICalypse, todo por POST; límite de 4 req/s. Switch 2 es la plataforma **508**.
- Da nombre y publisher (`involved_companies`). Las ediciones son entradas separadas: el `igdb_id` de un título
  tiene que apuntar a la del nombre de la caja, y eso se comprueba al investigar el juego.
- **Una sola llamada**: `download_igdb_catalog` pagina toda la plataforma y guarda nombre y publisher en
  `igdb_catalog.yaml`; `add_titles` sale de ahí sin volver a tocar la red.
- `game_type` sirve para filtrar, pero **con los nombres que devuelve la API**: `DLC`, `Pack / Addon`,
  `Expansion`, `Bundle`, `Season`, `Update`, `Episode`, `Mod`. Se descartan al descargar; quedan `Main Game`,
  `Port`, `Remaster`, `Remake`, `Expanded Game` y `Standalone Expansion`. De los 1483 juegos de Switch 2 del
  16-09-2026, 614 se van por tipo y quedan 869 candidatos.
- No distingue físico de digital. `release_dates` solo trae `worldwide` en los juegos de Switch 2 consultados,
  así que no sirve para fechas regionales. **249 de 1483 entradas (17 %) no traen ningún publisher**: el título
  se escribe con `publisher: null`.
- Licencia: gratis solo para uso no comercial (Twitch Developer Service Agreement).

## 9. Rakuten Books API ❔ (pendiente, 13-09-2026)

- Endpoint: `https://openapi.rakuten.co.jp/services/api/BooksGame/Search/20170404` (GET, JSON). El dominio
  antiguo `app.rakuten.co.jp` se apagó el 14-05-2026.
- Requisitos:
  - Credenciales `applicationId` + `accessKey` (`RAKUTEN_*` en `.env.example`).
  - Cabecera `Referer` obligatoria: sin ella da 403 `REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING`. También
    `Origin` desde servidor.
  - Lista de IPs permitidas.
  - Pausa de 1,5 s entre peticiones (si no, 429).
- Parámetros: `title`, `hardware`, `label`, `jan`, `booksGenreId` (Switch 2 = `006519`), `sort`, `hits`,
  `page`. Respuesta: `title`, `hardware`, `label` (distribuidora), `jan`, `makerCode`, `salesDate`.
- Promete JAN, distribuidora y fecha en JP. Las credenciales viajan en la URL: no loguear URLs completas.

## 10. Candidatas sin probar ❔

- **GRAC** (Corea) y **Classification Board** (Australia): publican quién pide la clasificación, así que
  servirían para la distribuidora local.
- **MobyGames**: lanzamientos por país y códigos de producto. API con clave y de pago.
- **Wikidata**: CC0, compatible con ODbL. Poco detalle regional.
- **Amazon Product Advertising API**: EAN; exige cuenta de afiliado con ventas.
- **Locales de la API Solr de Nintendo EU** distintos de `en`.

## 11. Cautelas de licencia y evidencia

- Lo que se copie en bloque debe ser compatible con ODbL: las listas de Wikipedia son CC BY-SA y no lo son.
- `evidence` refleja la fuente, no el método de acceso:
  - `official`: declaración o web oficial de Nintendo o del publisher.
  - `press_report`: prensa.
  - `retailer_listing`: tienda.
  - `box_photo`: foto de la caja.
  - Un dato leído por API nunca se infla a `official` si la API no afirma el formato.
- Etiquetas en los comentarios del YAML:
  - `(leída)`: página abierta y comprobada.
  - `(listado)`: solo título o resumen del buscador.
  - `(API)`: API pública de Nintendo.

## 11.1. Famitsu ✅ (probada 16-09-2026)

Los artículos de anuncio de パッケージ版 traen una ficha con el campo literal
`プラットフォーム：Nintendo Switch 2パッケージ版（キーカード）` (o sin `（キーカード）` si es cartucho completo) y, en las
key cards, una nota aparte: `※本作はキーカードです。`. Sirve como cita directa del formato en JP sin tener que
inferir nada del `sform_n` de la API (que no distingue formato, §4.2). Se lee bien con curl (200 sin User-Agent
especial en la prueba, aunque el resto de la receta usa siempre UA de navegador). Buscador propio:
`famitsu.com` no tiene endpoint de búsqueda probado; se ha llegado al artículo por WebSearch.

## 11.2. Fangamer / Fangamer Europe ✅ (probada 16-09-2026)

Distribuidor boutique (pines, pósters, edición física de coleccionista) que en indies sin edición física
"oficial" de Nintendo saca su propia tirada, a veces con tienda separada por región:

- `fangamer.com` (US, USD) y `fangamer.eu` (envíos desde Países Bajos, EUR) son dos tiendas distintas del
  mismo producto: mismo texto de producto, precios distintos. `fangamer.eu` no repite en su ficha si el
  juego va en cartucho o key card (solo GoNintendo, que cita el anuncio original de Fangamer, lo dice).
- GoNintendo suele cubrir el anuncio con la cita exacta de formato: 1000xRESIST, "it offers the full game on
  a traditional Game Card".
- Nintendo Everything cubre el mismo tipo de anuncios por el lado de la web oficial del juego (VGP, una
  tienda canadiense) con fechas que pueden no coincidir exactamente con las de Fangamer (distribuidores
  distintos, mismo producto).

## 12. Trampas de las herramientas

- **WebFetch resume con un modelo pequeño** y a veces inventa o infiere:
  - Afirmó "Full game (not a key card)" en hit.co.uk sin cita.
  - Dedujo "Distributor: Nintendo Korea".
  - Dijo que la eShop US no lista versión física.
  - Siempre pedir **citas textuales** y descartar lo que venga sin cita.
- **WebSearch también inventa citas cuando resume, no solo WebFetch** (probado 17-09-2026): sobre Attack on
  Titan 3 afirmó literalmente que "the Nintendo Switch 2 physical package will be sold as Game-Key Card version
  only", pero al abrir con `fetch_quote` el artículo que citaba (techtimes.com) esa frase **no existe** — el
  artículo solo habla de una restricción de acceso anticipado, nada de formato de cartucho. La cita real de
  Game-Key Card para ese juego salió de otra fuente (ficha de Nintendo Life). Regla: el resumen de WebSearch
  vale como pista de dónde mirar, nunca como cita — hay que abrir la fuente que menciona y sacar la frase con
  `fetch_quote` antes de escribir nada.
- **WebSearch puede resumir un resultado de un juego completamente distinto al buscado** (probado 17-09-2026):
  al buscar "Dear me, I was... Switch 2 physical edition" devolvió como respuesta una cita de la FAQ de soporte
  de Square Enix que en realidad hablaba de "FINAL FANTASY TACTICS - The Ivalice Chronicles" (la página de
  soporte es genérica y el resumen mezcló el contexto). Al abrir la fuente con `fetch_quote` se ve el encabezado
  real (`FINAL FANTASY TACTICS - The Ivalice Chronicles | About the Game | ...`) y queda claro que no sirve.
  Regla de siempre: abrir la fuente y mirar el contexto inmediato de la frase, no solo el fragmento que coincide.
- WebFetch trunca las páginas largas (ficha de Nintendo UK) y recibe 403 de casi todas las tiendas.
- **Bloquean `fetch_quote`/curl (403), aparte de las ya conocidas**: ResetEra y las fichas de producto de
  Play-Asia (`play-asia.com/en/...`); su blog (`play.asia/blog/...`) sí se lee. `rawfury.com` devuelve 200 pero
  el contenido lo pinta JavaScript (fetch_quote no encuentra nada útil).
- zsh: `echo ====HK` falla ("=cmd" se expande como ruta de un comando). Poner el texto entre comillas.
- `search.nintendo.jp`: los errores llegan en gzip; `curl --compressed`.
- `nintendo.com.hk` redirige con 301 a `nintendo.com/hk`: `curl -L`.
- Las descargas intermedias van al scratchpad de la sesión, no al repo.
