# CLAUDE.md

Base de datos abierta del formato físico (cartucho completo, game-key card, code in box) de los juegos de Nintendo
Switch 2 por región. Flujos y comandos en `README.md`.

## Antes de buscar datos de un juego

- Lee `SOURCES.md`: es el catálogo de fuentes de terceros ya probadas. Recoge APIs de Nintendo, tiendas, prensa y
  códigos de barras, con los comandos que funcionan, los campos que devuelven, los bloqueos (403) y la receta
  usada con Donkey Kong Bananza. No repitas pruebas que ya están documentadas ahí.
- Si pruebas una fuente nueva o descubres algo de una existente (un campo, un bloqueo, un límite, un endpoint
  cambiado), **actualiza `SOURCES.md` en la misma sesión**, con la fecha. Lo que no funcione también se documenta.
- Los hallazgos y decisiones van además a Notion: página "Switch 2 Physical Format DB — Plan de acción" y su
  subpágina "Fase 0 — Registro de hallazgos".

## Datos

- Nunca se inventa: sin fuente, el campo queda `null`.
- `skus.yaml` son SKUs curados a mano: los datos de un SKU se escriben directamente ahí (no hay overrides).
- Cada SKU lleva su `status`: `new` (borrador que nadie ha buscado todavía; **sale en la web como formato
  desconocido**), `pending` (ya se ha buscado la fuente y no aparece: sale en la web como formato desconocido
  y queda pendiente de una búsqueda a fondo), `reviewed` (tiene fuente abierta y comprobada) y `refresh` (tiene
  fuente, pero hay que volver a buscar evidencias en la web sobre si el juego es game-key card o no; sale
  igual que `reviewed` mientras tanto). **Un SKU con `source_url` comprobado se escribe directamente como
  `reviewed`**: la garantía la da la cita textual, no una segunda revisión. Un SKU `pending` no lleva
  `source_url` (lo valida el modelo), y nunca hay `reviewed` sin `source_url`.
- `titles.yaml` es **el único fichero de títulos**: lo llena `add_titles` desde `igdb_catalog.yaml` (sin red;
  la única llamada a IGDB es `download_igdb_catalog`, que ya descarta DLC, packs, bundles y expansiones).
  `name` y `publisher` vienen del catálogo, y `publisher` es `null` si IGDB no marca ninguno. A mano (o al
  investigar) solo se toca `status`: `new` (del catálogo, sin investigar), `pending` (investigado sin poder
  confirmar la edición ni encontrar fuente) o `reviewed` (confirmado que el `igdb_id` es la edición de la
  caja y que nombre y publisher son correctos). Al investigar un juego, si se confirma su edición, el título
  pasa a `reviewed`. Si `name`, `publisher` o `igdb_id` quedan mal por un cambio en IGDB, se corrigen a mano
  directamente en `titles.yaml` (no hay un status para esto: es un dato de identidad del título, no una
  evidencia por comprobar). La web (`build_site`) publica **todos** los títulos de `titles.yaml`, con
  independencia de su `status`, y de cada uno todos sus SKUs (incluidos los `new`, que salen como formato
  desconocido); un título sin ningún SKU sale con la tabla vacía. La web no muestra marcas de verificación ni
  la fecha de comprobación.
- El `title_id` lo genera `add_titles` como slug del nombre. Se puede corregir mientras el título esté `new` y
  sin ningún SKU; en cuanto un SKU lo referencia, no se cambia.
- `physical_release.yaml` guarda si un juego llegó a tener edición en caja, con su fuente: es lo que respalda
  un "solo digital". Quién lo ha mirado y quién no lo dice el `status` del título, no este fichero. Un juego
  confirmado sin caja y sin SKUs **se publica** como "sin edición física" con su fuente, así que investigar un
  "no" también produce web.
- En `skus.yaml` se escriben todas las claves; lo desconocido va como `null` explícito (`validate_data` avisa
  si falta alguna).
- En los comentarios del YAML, cada dato lleva `(leída)`, `(listado)` o `(API)`, con la cita que lo respalda.
- Para investigar el formato de un juego: skill `investigar-juego` (enruta por publisher y región).
- Qué queda por hacer: `uv run python -m scripts.next_work`.

## Herramientas

- uv + ruff + ty (no pipenv). `uv run --env-file .env` cuando haga falta IGDB.
- Antes de dar algo por terminado: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run ty check` y `uv run python -m scripts.validate_data`.
