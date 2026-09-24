# Flujo de trabajo: de un juego nuevo a la web

Paso a paso de cómo entra un juego en la base de datos, quién hace cada cosa (script o persona) y qué se
comprueba en cada punto. Los comandos sueltos están en `README.md`; las reglas de datos, en la cabecera de cada fichero
de `data/`.

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
   │                                     escribe la fuente, deja el SKU en reviewed y
   │                                     confirma la edición → título reviewed
   ▼
data/physical_release.yaml        (¿hay caja? si no, el juego se publica como "sin edición física")
data/skus.yaml                    (un SKU por región y edición, con su status)
   │  [AUTO] scripts.validate_data     → errores, avisos e informe
   │  [AUTO] scripts.build_site        → docs/index.html
   ▼
docs/  ──[MANUAL] git commit + push──▶  GitHub Pages
```

Regla que gobierna todo el flujo: **lo automático trae metadatos y candidatos, y la investigación se cierra
donde hay fuente**. Ninguna fuente estructurada dice si un juego es game-key card o cartucho completo,
así que lo que respalda cada dato es la **cita textual** anotada en el YAML con su
`source_url`. Sin cita, el dato no se escribe; con cita, el SKU queda en `reviewed` y se publica, sin paso
intermedio de revisión.

Los tres estados de un título, que son los que gobiernan la cola de trabajo y la web:

| status | Qué significa | ¿Sale en la web? |
|---|---|---|
| `new` | lo ha traído `add_titles` del catálogo y nadie lo ha investigado | **No** |
| `pending` | investigado sin poder confirmar la edición de la caja ni encontrar fuente | **No** |
| `reviewed` | investigado: el `igdb_id` es la edición de la caja y el resto está comprobado | Sí, si tiene algún SKU no-`new` |

El `status` es la única verdad sobre lo investigado: un título `reviewed` o `pending` tiene que haber dejado
SKUs o una entrada en `physical_release.yaml` diciendo que no hay caja, y `validate_data` avisa si no. Si
`name`, `publisher` o `igdb_id` quedan mal (IGDB cambió la entrada, o se eligió mal), se corrigen a mano
directamente en `titles.yaml`: no hay un status para esto, porque no es una evidencia que haya que volver a
comprobar, sino un dato de identidad del título.

Los cuatro estados de un SKU:

| status | Qué significa | ¿Sale en la web? |
|---|---|---|
| `new` | borrador que nadie ha buscado todavía | **No** |
| `pending` | ya se buscó su fuente y no apareció; falta buscarla a fondo | Sí, como formato desconocido |
| `reviewed` | su fuente se ha abierto y dice lo que dice el SKU | Sí |
| `refresh` | hay que volver a buscar evidencias en la web sobre su formato (dato viejo, fuente caída, región nueva) | Sí |

Un SKU `pending` no lleva `source_url` (el modelo lo rechaza) y, por tanto, su `format` es `unknown`: la web
dice que esa región existe pero que aún no se sabe su formato, en vez de esconderla.

La web no muestra distintivos de verificación ni la fecha de comprobación: `verified_at` se guarda en el dato
(y sale en el informe de `validate_data`), pero no se publica.

## 2. Paso a paso

### Paso 1 — Descargar el catálogo de IGDB · AUTOMÁTICO

```bash
uv run --env-file .env python -m scripts.download_igdb_catalog
```

- Busca la plataforma cuyo nombre contiene "Switch 2" (id 508), pagina sobre todos sus juegos (500 por
  petición, 0,25 s de pausa) y escribe `data/igdb_catalog.yaml` ordenado por nombre.
- Cada entrada: `igdb_id`, `name`, `game_type`, `first_release_date`, `publishers`.
- Requiere `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` en `.env`. El fichero está git-ignored: es solo la
  cantera de candidatos, no un dato publicable (licencia IGDB, uso no comercial).
- Reescribe el catálogo entero cada vez. Ejecutarlo cuando haya juegos anunciados nuevos.

### Paso 2 — Añadir títulos · AUTOMÁTICO

```bash
uv run python -m scripts.add_titles --count 10   # los 10 siguientes del catálogo
uv run python -m scripts.add_titles --all        # todos los que queden
uv run python -m scripts.add_titles --dates-only # solo refresca las fechas de salida, no añade nada
```

- **No toca la red**: `name`, `publisher` y `release_date` salen del catálogo local, así que no hacen falta
  credenciales.
- `release_date` es la salida en Switch 2 con la precisión que dé IGDB (`2026-08-20`, `2026-08`, `2026-Q3`,
  `2026`; `null` si es TBD). En los títulos que ya están se refresca en cada ejecución, salvo si ya es un día
  exacto pasado.
- Recorre el catálogo en orden alfabético y coge los juegos cuyo `igdb_id` no esté ya en `titles.yaml` ni en
  `excluded_titles.yaml`.
- Genera el `title_id` como slug del nombre (ascii, minúsculas, guiones) y le añade `-2`, `-3`… si colisiona.
- Escribe cada juego con **`status: new`**: no sale en la web y aparece en `titles_to_research`.
- Reescribe el fichero entero **conservando el `status` de lo que ya estaba**.

Qué queda por revisar a mano, y cuándo:

1. Que el `igdb_id` apunte a **la entrada con el nombre de la caja de Switch 2** ("… Ultimate Edition",
   "… Nintendo Switch 2 Edition") y no al juego base ni a otra plataforma. Eso se comprueba **al investigar el
   juego**, que es cuando el título pasa a `reviewed`; antes no hay que mirar nada.
2. Que el `title_id` autogenerado sea razonable. **Mientras el título esté `new` y no tenga ningún SKU se
   puede cambiar; en cuanto un SKU lo referencia, se congela.**
3. Si un juego resulta no ser un juego con caja propia (un DLC, una edición equivocada que el filtro por
   `game_type` no cazó o un juego que solo se vende en caja dentro de una recopilación), se borra su fila de
   `titles.yaml` y se apunta en `excluded_titles.yaml` con su `igdb_id`, su `name` y el motivo (`reason`).
   Así `add_titles` no lo vuelve a meter.

Fallos que paran la ejecución (y qué hacer):

| Error | Causa | Arreglo |
|---|---|---|
| `titles.yaml tiene N errores` | el fichero se editó a mano y quedó inválido | `scripts.validate_data` y corregir |

### Paso 3 — Elegir qué investigar · AUTOMÁTICO

```bash
uv run python -m scripts.next_work            # toda la cola
uv run python -m scripts.next_work --limit 10 # por lotes
```

Calcula la cola de trabajo leyendo solo los ficheros locales (sin red, sin IGDB):

| Lista | Qué es |
|---|---|
| `titles_to_review` | títulos `pending`: se investigaron sin poder confirmar la edición ni encontrar fuente |
| `titles_to_research` | títulos `new`: nadie los ha mirado. **Por aquí se empieza** |
| `titles_missing_regions` | títulos ya empezados y las regiones que les faltan |
| `new_skus` | SKUs `new`: nadie les ha buscado fuente y no salen en la web |
| `skus_without_source` | SKUs `pending`: buscados sin encontrar fuente; salen como formato desconocido |
| `skus_to_refresh` | SKUs `refresh`: hay que volver a comprobarlos |

### Paso 4 — Investigar el formato · MANUAL

Se busca en fuentes públicas (fichas oficiales, prensa, tiendas, fotos de la caja) y se escribe lo que se
encuentre, con la herramienta que cada cual prefiera.
El método:

1. **Paso cero: ¿existe edición física?** Para la mayoría de los indies del catálogo la respuesta es no. Si no
   hay caja en ninguna región, no se escriben SKUs: se anota en `data/physical_release.yaml`
   (`has_physical_release: false`, con su fuente y su fecha) y el juego no se vuelve a investigar.
2. **Enruta la búsqueda por publisher**, que es lo que mejor predice el formato:
   - Nintendo first-party → casi siempre `full_cart`; listas de "full game on the cart" por región.
   - Third-party japonés → API de Nintendo JP (`icode`, `maker`, `pprice`), luego las webs oficiales
     asiáticas con ese `icode`, VGC/Famitsu/AUTOMATON para el formato y el JAN por el prefijo del publisher.
   - Third-party occidental → listas de game-key card (Nintendo Life, Nintendo Everything), GoNintendo para
     code-in-box, APIs de Nintendo EU/NA para fechas, UPCitemdb para el UPC.
   - Indies → la web y la tienda del distribuidor especializado que saca la edición física.
3. **Exige cita textual** para cada dato: si la fuente no trae la frase, el dato no existe. Sin fuente,
   `null`; sin fuente del formato, `format: unknown`.
4. **Escribe los SKUs con su fuente y en `status: reviewed`**, con todas las claves y con la etiqueta de
   acceso en el comentario: `(leída)`, `(listado)` o `(API)`. `verified_at` es el día en que se abrió la fuente.
   Lo buscado sin encontrar fuente se deja en `pending`, con `format: unknown` y `source_url: null`:
   sale en la web como formato desconocido y queda apuntado para buscarlo a fondo.
5. **Pone el título en `reviewed`** si al investigarlo se confirma que el `igdb_id` es la edición de la caja y que
   nombre y publisher son correctos. Si no se consigue, se deja en `pending`, que también sale de la cola de
   `titles_to_research` pero no se publica.

Lo que **no** se hace nunca: escribir un dato sin la cita que lo respalde, ni marcar `reviewed` algo cuya
fuente no se haya abierto.

### Paso 4 bis — Repasar lo que quede marcado · MANUAL (opcional)

No hay puerta de revisión: lo investigado se publica. Lo que sí queda en la cola de `next_work`:

| Lo que ves | Qué hacer |
|---|---|
| SKU en `new` | nadie lo ha buscado: buscarlo, o dejarlo así (no se publica) |
| SKU en `pending` | se buscó y no había fuente: buscar a fondo (otra región, prensa, caja) y, si aparece, pasarlo a `reviewed` con su `format` |
| SKU en `refresh` | volver a buscar evidencias en la web, actualizar la fuente y `verified_at` |
| un dato que resulta erróneo | corregirlo en `skus.yaml`, o borrar la entrada |

Las reglas de escritura de `skus.yaml` (todas las claves, `null` lo desconocido, `sku_id` canónico,
`source_url` obligatorio salvo `format: unknown`, `evidence` según la fuente y no según el acceso) están en la
cabecera del propio fichero.

### Paso 5 — Validar · AUTOMÁTICO

```bash
uv run python -m scripts.validate_data
```

Valida los cuatro YAML con Pydantic, cruza los ficheros entre sí y saca un informe. **Código de salida distinto
de 0 si hay errores**; los avisos no bloquean.

Errores (hay que arreglarlos):

- `title_id` o `igdb_id` repetidos en `titles.yaml`; `sku_id` repetido en SKUs.
- `igdb_id` repetido en `excluded_titles.yaml`, o un título de `titles.yaml` cuyo `igdb_id` está excluido.
- SKU cuyo `title_id` no está en `titles.yaml`.
- En `physical_release.yaml`: `title_id` repetido, `title_id` que no está en `titles.yaml`, o un juego marcado
  como sin edición física que sin embargo tiene SKUs escritos.
- Cualquier fallo de esquema: slug inválido, `sku_id` no canónico, `format` conocido sin `source_url`,
  EAN/UPC con dígito de control incorrecto, claves de más (`extra="forbid"`), tipos o rangos.

Avisos (revisar, no bloquean):

- Título `reviewed` o `pending` que no ha dejado ni SKUs ni entrada en `physical_release.yaml`: dice estar
  investigado y no hay nada que lo respalde.
- `cart_size_gb` en un SKU que no es `full_cart`.
- `download_size_gb` en un SKU `full_cart` (el juego va en el cartucho: no hay descarga).
- SKUs que no se publican porque su título no está `reviewed`.
- SKUs con `status: new` (no salen en la web, porque no tienen fuente) y SKUs marcados `refresh`.
- Juego con edición física confirmada al que todavía no se le ha escrito ningún SKU.
- Filas de `skus.yaml` que **omiten** una clave opcional en vez de escribirla como `null`.

Informe (`Informe de datos`): recuento de títulos y de SKUs, reparto por status de título, por región,
por formato y por status de SKU, lista de
`pending_review_titles`, `fill_rates` por campo (los condicionales se miden solo donde aplican: `cart_size_gb`
solo sobre `full_cart`), `low_fill_fields` (≤ 60 %, excluyendo `distributor`, que se conserva por decisión del
13-09-2026 aunque no llegue al umbral) y `format_divergences` (juego-edición cuyo formato conocido cambia entre
regiones; los `unknown` se ignoran).

### Paso 6 — Generar la web · AUTOMÁTICO

```bash
uv run python -m scripts.build_site
```

- Renderiza `docs/index.html` (ES/EN, buscador por juego o publisher, filtros de región/formato/edición) desde
  `titles.yaml` + `skus.yaml` + `physical_release.yaml`, y toca `docs/.nojekyll`.
- **Publica los títulos `reviewed` que tengan al menos un SKU publicable** (es decir, que no sea `new`)
  **o que estén confirmados como sin edición física**. Quedan fuera los títulos `new` y `pending`,
  los `reviewed` cuyos SKUs sean todos `new`, y los que tienen caja pero aún no tienen ningún SKU escrito.
- Un juego sin edición física sale como tarjeta con la nota "no salió en caja en ninguna región" y su fuente,
  sin tabla de regiones. En el filtro de formato tiene su propio valor, "Sin edición física": se puede
  esconder o dejar solo, y como la ausencia de caja vale para todas las regiones, cualquier región o edición
  marcada lo deja visible.
- De cada juego publicado saca **los SKUs que no sean `new`**, todos con el mismo aspecto: la web no marca
  niveles de verificación ni muestra `verified_at`. Los `pending` salen como formato desconocido, que es
  justo lo que se sabe de ellos.
- Los SKUs de cada juego se ordenan por región y edición; los juegos, por nombre. Cada juego es enlazable con
  `#<title_id>`.
- Marca el juego como divergente si su formato conocido cambia entre regiones.
- Si algún YAML tiene errores de esquema, no genera nada y sale con 1.

### Paso 7 — Publicar · MANUAL

No hay CI: GitHub Pages sirve `docs/` directamente desde `main`, así que **publicar es commitear y pushear**
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
| 4b. Buscar el formato por región | **MANUAL** (enrutado por publisher) | fuentes → `skus.yaml` en `reviewed` (con cita) |
| 4c. Confirmar la edición del título | **MANUAL** | `titles.yaml` (solo `status`) |
| 5. Validar e informar | **AUTO** `validate_data` | los tres YAML → errores/avisos/informe |
| 6. Generar la web | **AUTO** `build_site` | `titles.yaml` + `skus.yaml` + `physical_release.yaml` → `docs/index.html` |
| 7. Publicar | **MANUAL** | `git commit` + `push` → GitHub Pages |

Quién escribe cada fichero:

| Fichero | Lo escribe | Se edita a mano |
|---|---|---|
| `data/igdb_catalog.yaml` | `download_igdb_catalog` (reescribe todo) | no (y no se versiona) |
| `data/titles.yaml` | `add_titles` (añade al final y reescribe conservando el `status`) | solo el campo `status`; el `title_id` mientras esté `new` y sin SKUs |
| `data/skus.yaml` | a mano, con fuente y en `reviewed` | sí: corregir datos y estados |
| `data/physical_release.yaml` | a mano | sí |
| `docs/index.html` | `build_site` | no |

Lo que no se hace nunca: escribir un dato sin la cita que lo respalde, ni dejar en `reviewed` un SKU sin
`source_url`.

## 4. Rutas rápidas

**El ciclo normal de trabajo**

```bash
uv run python -m scripts.next_work --limit 10   # qué toca
# investigar esos juegos                       → SKUs con fuente en reviewed (+ physical_release.yaml)
uv run python -m scripts.validate_data
uv run python -m scripts.build_site
# a mano: commit + push de data/ y docs/
```

**Un juego nuevo, de cero a la web**

```bash
uv run --env-file .env python -m scripts.download_igdb_catalog   # si el juego no está en el catálogo
uv run python -m scripts.add_titles --all                        # o añadir la fila a mano en titles.yaml
# investigar el formato, escribir sus SKUs con su fuente y poner el título en reviewed
uv run python -m scripts.validate_data && uv run python -m scripts.build_site
```

**Lote de juegos nuevos**

```bash
uv run --env-file .env python -m scripts.download_igdb_catalog
uv run python -m scripts.add_titles --count 20   # entran como status: new
# luego el ciclo normal de arriba: next_work los saca en titles_to_research
```

**Corregir los metadatos de un juego que ya estaba**: editar `name`, `publisher` o `igdb_id` a mano
directamente en `titles.yaml` (por ejemplo, tras descargar de nuevo el catálogo con
`download_igdb_catalog` si estaba viejo). Si la corrección deja en duda la edición confirmada, bajar el
`status` a `pending` a mano para que vuelva a la cola de `titles_to_review`.

**Volver a comprobar un dato viejo**: poner `status: refresh` en ese SKU. Sigue publicándose igual y aparece en
`skus_to_refresh` de `next_work`.

**Corregir un `igdb_id` mal elegido**: cambiarlo a mano en `titles.yaml`. Los SKUs no se tocan: cuelgan del
`title_id`, no del `igdb_id`.

**Un juego ya investigado que no sale en la web**: casi siempre es que su título sigue en `new` o en
`pending`, o que todos sus SKUs están en `status: new` por no tener fuente. `validate_data` avisa de las dos
cosas.

**Un juego que resultó ser solo digital**: no se le escriben SKUs; se anota en `physical_release.yaml` y su
título pasa a `reviewed` (investigado y sin caja). Sale de `titles_to_research` y **se publica en la web** como
"sin edición física", con la fuente que lo respalda: es una respuesta, no un hueco.
