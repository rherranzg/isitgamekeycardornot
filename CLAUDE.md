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
- `titles.yaml` lo genera `import_titles` desde IGDB. A mano solo se toca `status`: `pending` (importado sin
  comprobar), `reviewed` (comprobado a mano) o `refresh` (reimportar de IGDB; vuelve a `pending`). Nunca marcar
  `reviewed` en nombre del usuario. La web (`build_site`) solo publica los títulos `reviewed` y sus SKUs.
- En los comentarios del YAML, cada dato lleva `(leída)`, `(listado)` o `(API)`, con la cita que lo respalda.
- Lo propuesto por Claude va bajo una cabecera "PROPUESTOS ... PENDIENTES DE REVISIÓN".

## Herramientas

- uv + ruff + ty (no pipenv). `uv run --env-file .env` cuando haga falta IGDB.
- Antes de dar algo por terminado: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run ty check` y `uv run python -m scripts.validate_data`.
