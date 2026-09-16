import html
import re
from pathlib import Path

import requests

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120 Safari/537.36"
)
REQUEST_TIMEOUT_SECONDS = 30
NON_CONTENT_TAGS = re.compile(r"<(script|style|noscript|svg)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
BLOCK_TAGS = re.compile(
    r"</?(p|div|li|dd|dt|tr|td|th|h[1-6]|br|ul|ol|section|article)\b[^>]*>", re.IGNORECASE
)
ANY_TAG = re.compile(r"<[^>]+>")
WHITESPACE = re.compile(r"\s+")


def read_source(source: str) -> str:
    """Devuelve el contenido de una URL (con User-Agent de navegador) o de un fichero local ya descargado."""
    if not source.startswith(("http://", "https://")):
        return Path(source).read_text(encoding="utf-8", errors="ignore")
    response = requests.get(
        source, headers={"User-Agent": BROWSER_USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    return response.text


def html_to_text(page: str) -> str:
    """Quita scripts, estilos y etiquetas; los bloques quedan separados por ' | ' para no pegar celdas."""
    without_code = NON_CONTENT_TAGS.sub(" ", page)
    with_separators = BLOCK_TAGS.sub(" | ", without_code)
    text = html.unescape(ANY_TAG.sub(" ", with_separators))
    return re.sub(r"(\s*\|\s*)+", " | ", WHITESPACE.sub(" ", text)).strip(" |")


def find_quotes(text: str, pattern: str, context: int, max_quotes: int) -> list[str]:
    """Devuelve fragmentos distintos alrededor de cada coincidencia (regex, sin distinguir mayúsculas)."""
    quotes: list[str] = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        quote = text[max(0, match.start() - context) : match.end() + context].strip()
        if quote not in quotes:
            quotes.append(quote)
        if len(quotes) == max_quotes:
            break
    return quotes
