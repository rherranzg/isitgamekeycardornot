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
  (GameSpot, Game Rant, Nintendo Life). En Japón lo confirma AUTOMATON, al menos para DK Bananza.
- **El tamaño del cartucho (`cart_size_gb`) no tiene fuente pública por juego.** Nintendo no lo publica.
  Solo aparece cuando el publisher lo dice (Cyberpunk: 64 GB, vía Play-Asia blog).
- **Las APIs de Nintendo sí sirven para campos secundarios**: fecha de lanzamiento, maker/publisher, tamaño
  digital, código de producto y si existe versión en caja (solo JP).
- **Las tiendas bloquean la lectura automática (403)**: Play-Asia, HobbyDigi, Japanzon, QVC y otras. De ellas
  solo se puede usar el título del listado que muestra el buscador, marcado como `(listado)`.
- **Los códigos de barras**: en NA vía UPCitemdb; en JP, el JAN aparece en la URL de muchas tiendas; en EU y KR
  no se ha encontrado nada.

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
| Corea | `nintendo.com/kr/games/switch2/{icode}/` | 발매일, precio 패키지 버전 | ✅ No indica la distribuidora de forma explícita |
| Hong Kong | `nintendo.com/hk/games/switch2/{icode}/index.html` | 發售日, precio de la caja en HKD | ✅ |
| Singapur / Malasia | `nintendo.com/{sg,my}/games/switch2/{icode}/index.html` | Fecha; enlaza a Shopee/Lazada | ⚠️ Sin precio |
| Reino Unido | `nintendo.com/en-gb/Games/Nintendo-Switch-2-games/{Nombre}-{fs_id}.html` | Fecha, PEGI | ⚠️ WebFetch la trunca; mejor la API Solr |
| EE. UU. | `nintendo.com/us/store/products/{urlKey}/` | Fecha, publisher, tamaño, idiomas | ⚠️ El resumen de WebFetch dijo que no hay versión física (falso) |
| Japón: キーカード | `nintendo.com/jp/games/switch2/key-card/index.html` | Explica que la caja de una キーカード lo avisa en la portada y la tarjeta lleva un candado arriba a la derecha | ❌ No lista títulos |
| Japón: lineup | `nintendo.com/jp/games/switch2/lineup/index.html` | — | ❔ Sin revisar si marca las キーカード o carga un JSON |

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
| hit.co.uk | UK | ⚠️ legible | Fecha | El resumen afirmó "not a key card" sin cita: no fiable |
| Smyths, Currys, John Lewis, Amazon UK | UK | ❔ | — | — |

No se ha probado curl con `User-Agent` de navegador contra las tiendas que dan 403 a WebFetch.

## 7. Prensa y listas

| Fuente | Región | Estado | Uso |
|---|---|---|---|
| VGC | JP / occidente | ✅ leída (13-09) | Lista de third-party con game-key card en Japón; citas de publishers (CD Projekt: "contained entirely on the cartridge") |
| Nintendo Life: juegos con el juego completo en el cartucho | EU/UK | ✅ leída (15-09) | Formato `full_cart` por título, sin distinción regional |
| Nintendo Life: juegos con game-key card | EU/UK | ❔ | Lista inversa |
| Nintendo Everything: lista de game-key cards | NA | ❔ | Lista de game-key cards |
| Nintendo Wire: todos los físicos y su tipo | NA | ❌ 403 | Cartucho / key card / código por juego |
| Deku Deals: guía y listas de key card y juego completo | NA/EU | ❔ (fetch interrumpido) | Listas autoactualizadas |
| GameSpot | NA | ✅ | Guías de compra; galería de juegos con el juego en la tarjeta |
| Game Rant | NA | ✅ leída (15-09) | "DK Bananza's physical version is not a Game Key Card" |
| GoNintendo | NA | ⚠️ título/resumen | Key card, code-in-box, códigos incluidos |
| EventHubs | NA | ⚠️ resumen | Caducidad del código de DLC de SF6 |
| Gematsu (X) | — | ⚠️ | Divergencias regionales (Daemon X Machina) |
| AUTOMATON | JP | ✅ leída (15-09) | "同じくゲームカードを採用した『ドンキーコング バナンザ』": Nintendo usa tarjeta normal |
| Famitsu | JP | ⚠️ resumen | パッケージ版 como キーカード, espacio libre necesario |
| Game*Spark, GameWith, Game8 | JP | ⚠️ resumen | Tamaño digital (DK: de 10 GB a 8,5 GB) |
| RPG Site, Nintendo Insider | — | ❔ | Listas de físicos completos |
| Tom's Hardware, TweakTown | — | ⚠️ | Capacidades de cartucho disponibles en general (rumores), no por juego |

## 8. IGDB (integrada en el código)

- Autenticación por Twitch (`TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` en `.env`), OAuth `client_credentials`.
  El `client_secret` va en el cuerpo del POST, nunca en la URL.
- Consultas en APICalypse, todo por POST; límite de 4 req/s. Switch 2 es la plataforma **508**.
- Da nombre y publisher (`involved_companies`). Las ediciones son entradas separadas: la semilla apunta a la del
  nombre de la caja.
- No distingue físico de digital. `release_dates` solo trae `worldwide` en los juegos de Switch 2 consultados,
  así que no sirve para fechas regionales. Hay entradas sin publisher.
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

## 12. Trampas de las herramientas

- **WebFetch resume con un modelo pequeño** y a veces inventa o infiere:
  - Afirmó "Full game (not a key card)" en hit.co.uk sin cita.
  - Dedujo "Distributor: Nintendo Korea".
  - Dijo que la eShop US no lista versión física.
  - Siempre pedir **citas textuales** y descartar lo que venga sin cita.
- WebFetch trunca las páginas largas (ficha de Nintendo UK) y recibe 403 de casi todas las tiendas.
- zsh: `echo ====HK` falla ("=cmd" se expande como ruta de un comando). Poner el texto entre comillas.
- `search.nintendo.jp`: los errores llegan en gzip; `curl --compressed`.
- `nintendo.com.hk` redirige con 301 a `nintendo.com/hk`: `curl -L`.
- Las descargas intermedias van al scratchpad de la sesión, no al repo.
