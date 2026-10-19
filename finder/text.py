import html
import re


def html_to_text(h: str) -> str:
    h = re.sub(r"(?is)<(script|style|noscript|svg|head)\b.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)<br\s*/?>|</(p|li|div|h\d|tr)>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h)
    h = re.sub(r"[ \t\r\f\v]+", " ", h)
    return re.sub(r"\n\s*\n+", "\n", h).strip()
