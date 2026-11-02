"""Public interface of the knowledge module. Other modules may only import from here."""

from typing import Protocol

from costpilot.modules.knowledge.domain.models import Passage, SearchResult

__all__ = ["KnowledgeSearch", "Passage", "SearchResult"]


class KnowledgeSearch(Protocol):
    async def search(self, question: str, provider: str) -> SearchResult:
        """Find trusted passages. This never fails: if search is down, the result says so."""
