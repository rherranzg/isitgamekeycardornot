# Flujo de trabajo: de un juego nuevo a la web

[English](WORKFLOW.md) · **Español**

Cómo entra un juego en la base de datos, quién hace cada cosa (script o persona) y qué se comprueba en cada
punto. Los comandos sueltos están en `README.md`; las reglas de datos, en la cabecera de cada fichero de `data/`.

## 1. El flujo de un vistazo

```
IGDB (plataforma 508)
   │  [AUTO] scripts.download_igdb_catalog  → descarta DLC, packs, bundles y expansiones
   ▼
data/igdb_catalog.yaml            (local, no se versiona)
   │  [AUTO] scripts.add_titles       → title_id + igdb_id + name + publisher + release_date, status: new
   ▼
data/titles.yaml                  (el único fichero de títulos)
   │  [AUTO] scripts.next_work         → qué falta por investigar
   │  [MANUAL] investigar el formato   → busca según publisher y región,
   │                                     escribe el SKU con su fuente y
   │                                     → título completed, o pending si falta algo
   ▼
data/physical_release.yaml        (¿hay caja? si no, el juego sale como "sin edición física")
data/skus.yaml                    (un SKU por región y edición, con su fuente)
   │  [AUTO] scripts.validate_data     → errores, avisos e informe
   │  [AUTO] scripts.build_site        → docs/index.html
   ▼
docs/  ──[MANUAL] git commit + push──▶  GitHub Pages
```

Regla general: **lo automático trae metadatos y candidatos; la investigación se cierra donde hay fuente**.
Ninguna fuente estructurada dice si un juego es game-key card o cartucho completo, así que cada dato se
respalda con la **cita textual** anotada en el YAML junto a su `source_url`. Sin cita no hay dato; con cita,
el SKU queda escrito, sin revisión intermedia.

**La web publica todos los títulos de `titles.yaml`, sea cual sea su `status`, y todos sus SKUs.** El status
del título solo gobierna la cola de trabajo.

Estados de un título:

| status | Qué significa |
|---|---|
| `new` | lo ha traído `add_titles` del catálogo y no hay nada investigado: se investigan todas las regiones. No puede tener SKUs ni entradas en `physical_release.yaml` |
| `refresh` | se vuelven a investigar todas las regiones. Lo que hay es un punto de partida que se comprueba, no se da por bueno: lo nuevo sustituye a lo antiguo (una fuente que sigue diciendo lo mismo se conserva, con sus `updates`) |
| `pending` | lo que hay se da por bueno: solo se investiga lo que falta (regiones, SKUs sin fuente, campos vacíos) |
| `completed` | no falta nada: cada región respondida (un SKU con fuente o un "sin caja en esta región" con fuente) y cada SKU con todos sus datos, o "sin edición física" con fuente. No hace falta volver a buscar nada |

Investigar un título `new`, `refresh` o `pending` acaba en `completed` si no falta nada y en `pending` si falta
algo. Si `name`, `publisher` o `igdb_id` quedan mal, se corrigen a mano en `titles.yaml`: son datos de
identidad, no evidencias, así que no tienen status propio.

Si un juego no va a tener caja en una región (allí solo sale en digital), se anota en `physical_release.yaml`
con esa `region`, `has_physical_release: false` y su fuente. Con fuente, la región cuenta como respondida.

Un SKU está completo cuando tiene `source_url`, su `format` no es `unknown` y tiene `distributor` y `release_date`, más
`edition_name` si no es la estándar y `download_size_gb` si es game-key card o code in box.
`cart_size_gb`, `includes_download_code` y `ean` se escriben si se conocen, pero no se exigen. Si falta cualquiera de esas cosas, el título se queda en
`pending`. `validate_data` falla si un título `completed` no lo cumple.

Los SKUs no tienen status. Un SKU con formato conocido lleva siempre un `source_url` que se ha abierto y dice
lo que dice el SKU. Un SKU buscado sin encontrar fuente lleva `source_url: null` y `format: unknown`: sale en
la web como formato desconocido y queda pendiente de una búsqueda a fondo. La web no muestra marcas de verificación ni `verified_at`, que solo sale en el
informe de `validate_data`.

Nada de lo que enseña la web cambia sin su enlace. Una fuente posterior que actualiza un SKU (un retraso, un
cambio de formato) no sustituye a `source_url`: va a la lista `updates` del SKU con los `fields` que actualiza, y
la web la enlaza junto a la fuente. Lo mismo un dato que se rellena desde otra fuente (una fecha que era `null`).
La fecha de un título escrita a mano lleva su fuente en `updates` del título, y `add_titles` ya no la sustituye
por la de IGDB.

## 2. Paso a paso

### Paso 1 — Descargar el catálogo de IGDB · AUTOMÁTICO

```bash
uv run --env-file .env python -m scripts.download_igdb_catalog
```

- Busca la plataforma "Switch 2" (id 508), pagina todos sus juegos (500 por petición, 0,25 s de pausa) y
  escribe `data/igdb_catalog.yaml` ordenado por nombre.
- Cada entrada: `igdb_id`, `name`, `game_type`, `first_release_date`, `publishers`.
- Requiere `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` en `.env`. El fichero está git-ignored: es cantera de
  candidatos, no dato publicable (licencia IGDB, uso no comercial). Se reescribe entero cuando hay juegos nuevos.

### Paso 2 — Añadir títulos · AUTOMÁTICO

```bash
uv run python -m scripts.add_titles --count 10   # los 10 siguientes del catálogo
uv run python -m scripts.add_titles --all        # todos los que queden
uv run python -m scripts.add_titles --dates-only # solo refresca las fechas de salida, no añade nada
```

- **No toca la red** ni necesita credenciales: `name`, `publisher` y `release_date` salen del catálogo local.
- `release_date` es la salida en Switch 2 con la precisión que dé IGDB (`2026-08-20`, `2026-08`, `2026-Q3`,
  `2026`; `null` si es TBD). Se refresca en cada ejecución salvo si ya es un día exacto pasado.
- Recorre el catálogo en orden alfabético y coge los `igdb_id` que no estén en `titles.yaml` ni en
  `excluded_titles.yaml`. Nunca elige bundles y se salta las ediciones (Deluxe, Gold...; IGDB las enlaza con
  `version_parent`) cuyo juego base está en Switch 2.
- Genera el `title_id` como slug del nombre (ascii, minúsculas, guiones), con `-2`, `-3`… si colisiona.
- Escribe cada juego con **`status: new`** (aparece en `titles_to_research`) y reescribe el fichero
  **conservando el `status` de lo que ya estaba**.

Qué queda por revisar a mano:

1. Que el `igdb_id` sea **el del juego, no el de una de sus ediciones**: una edición no es un título, sino un
   SKU del juego base (`edition: deluxe` o `collectors`, con su nombre en `edition_name`). Excepción: si en
   Switch 2 el juego **solo** se vende como esa edición (ELDEN RING Tarnished Edition), el título es la edición
   y el juego base va a `excluded_titles.yaml`. Se comprueba al investigar el juego.
2. Que el `title_id` sea razonable. **Se puede cambiar mientras el título esté `new` y sin SKUs; en cuanto un
   SKU lo referencia, se congela** (es parte del `sku_id` y el ancla `#<title_id>` de la web).
3. Si no es un juego con caja propia (un DLC, una edición solo digital o un juego que solo se vende dentro de
   una recopilación), se borra de `titles.yaml` y se apunta en `excluded_titles.yaml` con `igdb_id`, `name` y
   `reason`, para que `add_titles` no lo vuelva a meter. La recopilación se añade a mano a `titles.yaml` con su
   `igdb_id`. Si el título ya se había publicado, lleva además `former_title_id` y `merged_into`, y la web deja
   su ancla vieja en la ficha nueva.

Si para con `titles.yaml tiene N errores`, el fichero se editó a mano y quedó inválido: pasar
`scripts.validate_data` y corregir.

### Paso 3 — Elegir qué investigar · AUTOMÁTICO

```bash
uv run python -m scripts.next_work            # toda la cola
uv run python -m scripts.next_work --limit 10 # por lotes
```

Calcula la cola leyendo solo los ficheros locales (sin red):

| Lista | Qué es |
|---|---|
| `titles_to_research` | títulos `new`: nadie los ha mirado. **Por aquí se empieza** |
| `titles_to_refresh` | títulos `refresh`: se vuelven a investigar desde cero |
| `titles_to_complete` | títulos `pending`: solo falta lo que no hay, del comprobado hace más tiempo al más reciente |
| `titles_missing_regions` | títulos ya empezados y las regiones sin SKU ni "sin caja" con fuente |
| `skus_without_source` | SKUs sin `source_url`: buscados sin fuente, pendientes de búsqueda a fondo |

### Paso 4 — Investigar el formato · MANUAL

Se busca en fuentes públicas (fichas oficiales, prensa, tiendas, fotos de la caja):

1. **Paso cero: ¿existe edición física?** En la mayoría de los indies, no. Si no hay caja en ninguna región,
   no se escriben SKUs: se anota en `data/physical_release.yaml` (`has_physical_release: false`, con fuente y
   fecha) y el juego no se vuelve a investigar. Si solo faltan cajas en algunas regiones, una entrada por
   región (`region: KR`...), con fuente.
2. **Enruta la búsqueda por publisher**, que es lo que mejor predice el formato:
   - Nintendo first-party → casi siempre `full_cart`; listas de "full game on the cart" por región.
   - Third-party japonés → API de Nintendo JP (`icode`, `maker`, `pprice`), las webs oficiales asiáticas con
     ese `icode`, VGC/Famitsu/AUTOMATON para el formato y el JAN por el prefijo del publisher.
   - Third-party occidental → listas de game-key card (Nintendo Life, Nintendo Everything), GoNintendo para
     code-in-box, APIs de Nintendo EU/NA para fechas, UPCitemdb para el UPC.
   - Indies → la web y la tienda del distribuidor especializado que saca la edición física.
3. **Exige cita textual** para cada dato: si la fuente no trae la frase, el dato no existe. Sin fuente, `null`;
   sin fuente del formato, `format: unknown`.
4. **Escribe los SKUs con su fuente**, con todas las claves y la etiqueta de acceso en
   el comentario: `(leída)`, `(listado)` o `(API)`. `verified_at` es el día en que se abrió la fuente. Lo
   buscado sin fuente queda con `format: unknown` y `source_url: null`, apuntado para buscarlo a fondo. Cada edición con caja (Deluxe, Collector's, SteelBook...) es su propio SKU.
5. **Pone el título en `completed`** si no falta nada, o en `pending` si falta algo, con `last_checked_at`
   al momento actual (fecha, hora y zona horaria: `2026-10-09T19:42:10+02:00`). Un `pending` pasa de `titles_to_research` a `titles_to_complete`.

### Paso 4 bis — Repasar lo que quede marcado · MANUAL (opcional)

No hay puerta de revisión: todo se publica. Lo que queda en la cola de `next_work`:

| Lo que ves | Qué hacer |
|---|---|
| SKU sin `source_url` | buscar a fondo (otra región, prensa, caja) y, si aparece, escribir su `source_url` y su `format` |
| un dato erróneo | corregirlo en `skus.yaml`, o borrar la entrada |

Las reglas de escritura de `skus.yaml` (todas las claves, `null` lo desconocido, `sku_id` canónico,
`source_url` obligatorio salvo `format: unknown`, `evidence` según la fuente y no según el acceso) están en la
cabecera del fichero.

### Paso 5 — Validar · AUTOMÁTICO

```bash
uv run python -m scripts.validate_data
```

Valida los cuatro YAML con Pydantic, los cruza entre sí y saca un informe. **Sale con código distinto de 0 si
hay errores**; los avisos no bloquean.

Errores:

- `title_id` o `igdb_id` repetidos en `titles.yaml`; `sku_id` repetido en SKUs.
- `igdb_id` repetido en `excluded_titles.yaml`, o un título de `titles.yaml` cuyo `igdb_id` está excluido.
- SKU cuyo `title_id` no está en `titles.yaml`.
- En `physical_release.yaml`: entrada repetida (por título y región) o con `title_id` inexistente, un juego
  sin edición física que tiene SKUs, una región "sin caja" con un SKU en esa región o junto a una entrada del
  juego entero.
- Título `new` con SKUs o entradas en `physical_release.yaml` (debería ser `refresh`).
- Título `completed` al que le falta una región, el `source_url` de un SKU o un dato (ver "Estados de un título").
- Fallos de esquema: slug inválido, `sku_id` no canónico, `format` conocido sin `source_url`, EAN/UPC con
  dígito de control incorrecto, claves de más (`extra="forbid"`), tipos o rangos.

Avisos:

- `cart_size_gb` en un SKU que no es `full_cart`, o `download_size_gb` en uno que no es `game_key_card` ni `code_in_box` (el tamaño de la eShop es el de la versión digital: solo es la descarga de la caja cuando esta es key card o code in box).
- SKUs sin `source_url`.
- Juego con edición física confirmada sin ningún SKU.
- Filas de `skus.yaml` que **omiten** una clave opcional en vez de escribirla como `null`.

Informe (`Informe de datos`): recuento de títulos y SKUs; reparto por status de título, región y
formato de SKU; `fill_rates` por campo (los condicionales solo donde aplican:
`cart_size_gb` sobre `full_cart`); `low_fill_fields` (≤ 60 %, salvo `distributor`, que se conserva por
decisión del 13-09-2026) y `format_divergences` (juego-edición cuyo formato conocido cambia entre regiones,
ignorando los `unknown`).

### Paso 6 — Generar la web · AUTOMÁTICO

```bash
uv run python -m scripts.build_site
```

- Renderiza `docs/index.html` (ES/EN, buscador por juego o publisher, filtros de región/formato/edición) desde
  `titles.yaml` + `skus.yaml` + `physical_release.yaml`, y toca `docs/.nojekyll`.
- **Publica todos los títulos de `titles.yaml`, sea cual sea su `status`, con todos sus SKUs**: los que no
  tienen fuente, como formato desconocido. A la derecha del título va `release_date` como etiqueta, con su
  precisión ("20 ago 2026", "T3 2026"), y nada si es `null`.
- Un juego confirmado sin edición física y sin SKUs sale con la nota "no salió en caja en ninguna región" y su
  fuente, sin tabla, y tiene su valor en el filtro de formato, "Sin edición física". Un título sin ningún SKU
  sale con la tabla vacía y el valor "Sin SKUs todavía". Cualquier filtro de región o edición deja visibles
  a ambos.
- Los SKUs, todos con el mismo aspecto, van ordenados por región y edición, y las ediciones se muestran con
  su `edition_name`. Los juegos van por nombre, enlazables con `#<title_id>` (y con las anclas viejas de los
  títulos fusionados en ellos), y se marcan como divergentes si su formato conocido cambia entre regiones.
- Si algún YAML tiene errores de esquema, no genera nada y sale con 1.

### Paso 7 — Publicar · MANUAL

No hay CI: GitHub Pages sirve `docs/` desde `main`, así que **publicar es commitear y pushear**
`docs/index.html` junto con los datos.

Antes de dar algo por terminado:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python -m scripts.validate_data
```

## 3. Resumen: automático vs. manual

| Paso | Quién | Entrada → salida |
|---|---|---|
| 1. Catálogo de IGDB | **AUTO** `download_igdb_catalog` | IGDB → `igdb_catalog.yaml` (sin DLC ni packs) |
| 2. Añadir títulos y generar slugs | **AUTO** `add_titles` | `igdb_catalog.yaml` → `titles.yaml` (`new`) |
| 3. Cola de trabajo | **AUTO** `next_work` | los ficheros de datos → qué falta |
| 4a. ¿Existe edición física? | **MANUAL** | fuentes → `physical_release.yaml` |
| 4b. Buscar el formato por región | **MANUAL** (enrutado por publisher) | fuentes → `skus.yaml` (con cita) |
| 4c. Confirmar la edición del título | **MANUAL** | `titles.yaml` (solo `status` y `last_checked_at`) |
| 5. Validar e informar | **AUTO** `validate_data` | los YAML → errores/avisos/informe |
| 6. Generar la web | **AUTO** `build_site` | `titles.yaml` + `skus.yaml` + `physical_release.yaml` → `docs/index.html` |
| 7. Publicar | **MANUAL** | `git commit` + `push` → GitHub Pages |

Quién escribe cada fichero:

| Fichero | Lo escribe | Se edita a mano |
|---|---|---|
| `data/igdb_catalog.yaml` | `download_igdb_catalog` (reescribe todo) | no (y no se versiona) |
| `data/titles.yaml` | `add_titles` (añade al final y reescribe conservando el `status`) | solo `status` y `last_checked_at`; el `title_id` mientras esté `new` y sin SKUs |
| `data/skus.yaml` | a mano, con fuente | sí: corregir datos |
| `data/physical_release.yaml` | a mano | sí |
| `docs/index.html` | `build_site` | no |

Lo que no se hace nunca: escribir un dato sin la cita que lo respalde, ni un `format` conocido sin
`source_url`.

## 4. Rutas rápidas

**El ciclo normal de trabajo**

```bash
uv run python -m scripts.next_work --limit 10   # qué toca
# investigar esos juegos                       → SKUs con fuente (+ physical_release.yaml)
uv run python -m scripts.validate_data
uv run python -m scripts.build_site
# a mano: commit + push de data/ y docs/
```

**Juegos nuevos, de cero a la web**

```bash
uv run --env-file .env python -m scripts.download_igdb_catalog   # si no están en el catálogo
uv run python -m scripts.add_titles --count 20                   # o --all; entran como status: new
# luego el ciclo normal: next_work los saca en titles_to_research
```

**Ponerse al día con las noticias** de los últimos días (retrasos, cajas nuevas, cambios de formato):

```bash
uv run python -m scripts.news_candidates --days 7          # noticias que nombran un título conocido
uv run python -m scripts.check_store_dates --days 7 --save # qué ha cambiado en las tiendas de Nintendo
# leer cada pista; un cambio confirmado va a `updates` del SKU con su cita
uv run python -m scripts.validate_data
uv run python -m scripts.build_site
```

Los dos scripts solo señalan qué mirar: los datos se cambian a mano, con cita, como cualquier otra
actualización. Los juegos que aún no están en `titles.yaml` se ignoran; entran con la siguiente importación
del catálogo.

**Corregir los metadatos de un juego**: editar `name`, `publisher` o `igdb_id` a mano en `titles.yaml`. Si
eso pone en duda lo investigado, pasar el `status` a `refresh` para que se vuelva a investigar.
Los SKUs no se tocan: cuelgan del `title_id`, no del `igdb_id`.

**Un juego que resultó ser solo digital**: sin SKUs; se anota en `physical_release.yaml` y el título pasa a
`completed` si la entrada tiene fuente, o a `pending` si no. Sale de `titles_to_research` y en la web pasa de la tabla vacía a "sin edición física", con su
fuente: es una respuesta, no un hueco.
