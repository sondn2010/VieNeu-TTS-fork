"""Strip an HTML chapter to plain text: one line per block element.

Inline elements (such as a drop-cap `<span>M</span>ặt nước`) are concatenated
without added whitespace, so the drop-cap letter rejoins its word.
"""
from __future__ import annotations

from html.parser import HTMLParser

_BLOCK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "section", "article", "header", "footer", "tr", "table", "hr", "pre",
}
_SKIP_TAGS = {"script", "style", "noscript", "template", "head", "nav"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):  # noqa: ARG002 - HTMLParser signature
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")
            if tag == "hr":
                self.parts.append("***\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth:
            # Source newlines inside a block are layout, not paragraph breaks.
            self.parts.append(" ".join(data.splitlines()) if "\n" in data else data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)
