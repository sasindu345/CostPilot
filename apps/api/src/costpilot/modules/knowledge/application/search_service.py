"""Finds trusted documentation. If search fails, the AI can still answer bill questions."""

from collections.abc import Sequence

import structlog

from costpilot.modules.knowledge.application.ports import Embedder, VectorIndex
from costpilot.modules.knowledge.domain.errors import KnowledgeUnavailableError
from costpilot.modules.knowledge.domain.models import SearchResult

logger = structlog.get_logger()


class KnowledgeSearchService:
    def __init__(
        self, embedder: Embedder, index: VectorIndex, limit: int, min_score: float
    ) -> None:
        self._embedder = embedder
        self._index = index
        self._limit = limit
        self._min_score = min_score

    async def search(self, question: str, providers: Sequence[str]) -> SearchResult:
        """One embedding call covers every cloud, so more clouds cost no more AI quota."""
        if isinstance(providers, str):
            # A string would be read as single letters and silently match nothing.
            raise TypeError("providers must be a list of cloud names")
        try:
            vector = await self._embedder.embed_query(question)
            passages = await self._index.search(
                vector, list(providers), self._limit, self._min_score
            )
        except KnowledgeUnavailableError as error:
            logger.warning("knowledge_search_unavailable", reason=str(error))
            return SearchResult(passages=[], is_available=False)
        return SearchResult(passages=passages)
