"""Public interface of the knowledge module. Other modules may only import from here."""

from collections.abc import Sequence
from typing import Protocol

from costpilot.modules.knowledge.domain.models import Passage, SearchResult

__all__ = ["KnowledgeSearch", "Passage", "SearchResult"]


class KnowledgeSearch(Protocol):
    async def search(self, question: str, providers: Sequence[str]) -> SearchResult:
        """Find trusted passages for these clouds. If search is down, the result says so."""
