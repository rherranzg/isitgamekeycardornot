import argparse

from aws_lambda_powertools import Logger

from switch2db.quote import find_quotes, html_to_text, read_source

logger = Logger(service="switch2db-fetch-quote")


def parse_args() -> argparse.Namespace:
    """Define y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description=(
            "Descarga una página (o lee un fichero ya descargado) y muestra solo los fragmentos que "
            "coinciden con el patrón, para citar sin volcar el HTML entero."
        )
    )
    parser.add_argument("source", help="URL o ruta de un fichero local")
    parser.add_argument(
        "pattern", help="Expresión regular, sin distinguir mayúsculas (p. ej. 'key.?card|cart')"
    )
    parser.add_argument("--context", type=int, default=120, help="Caracteres alrededor de cada coincidencia")
    parser.add_argument("--max", type=int, default=5, dest="max_quotes", help="Máximo de fragmentos")
    parser.add_argument("--raw", action="store_true", help="No convertir HTML a texto (JSON, texto plano)")
    args = parser.parse_args()
    if args.context < 0 or args.max_quotes <= 0:
        parser.error("--context no puede ser negativo y --max debe ser mayor que 0")
    return args


def main() -> None:
    """Muestra los fragmentos citables de una fuente."""
    args = parse_args()
    content = read_source(args.source)
    text = content if args.raw else html_to_text(content)
    quotes = find_quotes(text, args.pattern, args.context, args.max_quotes)
    logger.info(
        "Fragmentos encontrados",
        extra={"source": args.source, "pattern": args.pattern, "match_count": len(quotes), "quotes": quotes},
    )


if __name__ == "__main__":
    main()
