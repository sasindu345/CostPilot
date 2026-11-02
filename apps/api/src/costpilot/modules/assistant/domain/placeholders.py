"""The AI writes {{F1}}, and code fills in the real value, so it cannot invent a figure."""

import re
from collections.abc import Iterable

from costpilot.modules.assistant.domain.models import Fact

PLACEHOLDER = re.compile(r"\{\{\s*(F\d+)\s*\}\}")
UNKNOWN_FACT = "[not available]"
OPENING = "{"


class PlaceholderFiller:
    """Works while the answer is streaming, when a placeholder can arrive in two pieces."""

    def __init__(self, facts: Iterable[Fact]) -> None:
        self._values = {fact.id: fact.value for fact in facts}
        self._pending = ""

    def feed(self, chunk: str) -> str:
        text = self._pending + chunk
        self._pending = ""
        cut = self._unfinished_start(text)
        if cut is not None:
            text, self._pending = text[:cut], text[cut:]
        return self._fill(text)

    def finish(self) -> str:
        text, self._pending = self._pending, ""
        return self._fill(text)

    def _fill(self, text: str) -> str:
        return PLACEHOLDER.sub(lambda m: self._values.get(m[1], UNKNOWN_FACT), text)

    def _unfinished_start(self, text: str) -> int | None:
        start = text.rfind(OPENING)
        if start == -1:
            return None
        if start > 0 and text[start - 1] == OPENING:
            start -= 1
        return None if "}}" in text[start:] else start
