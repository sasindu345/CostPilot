"""Builds the knowledge base. Running it twice changes nothing and costs nothing."""

import structlog

from costpilot.modules.knowledge.application.ports import (
    Embedder,
    PageLoader,
    TextSplitter,
    VectorIndex,
)
from costpilot.modules.knowledge.domain.errors import (
    KnowledgeUnavailableError,
    SourceRejectedError,
)
from costpilot.modules.knowledge.domain.models import IndexReport, Source
from costpilot.modules.knowledge.domain.sources import check_sources, content_hash

logger = structlog.get_logger()


class KnowledgeIndexer:
    def __init__(
        self,
        loader: PageLoader,
        splitter: TextSplitter,
        embedder: Embedder,
        index: VectorIndex,
        allowed_hosts: tuple[str, ...],
    ) -> None:
        self._loader = loader
        self._splitter = splitter
        self._embedder = embedder
        self._index = index
        self._allowed_hosts = allowed_hosts

    async def run(self, sources: list[Source]) -> IndexReport:
        check_sources(sources, self._allowed_hosts)
        await self._index.prepare()
        existing = await self._index.indexed_hashes()

        indexed: list[str] = []
        unchanged: list[str] = []
        failed: list[str] = []
        for source in sources:
            try:
                text = await self._loader.load(source)
                text_hash = content_hash(text)
                if existing.get(source.id) == text_hash:
                    unchanged.append(source.id)
                    continue
                chunks = self._splitter.split(text)
                vectors = await self._embedder.embed_documents(chunks)
                await self._index.replace_source(source, text_hash, chunks, vectors)
                indexed.append(source.id)
            except (KnowledgeUnavailableError, SourceRejectedError, OSError) as error:
                logger.warning("source_not_indexed", source=source.id, reason=str(error))
                failed.append(source.id)

        wanted = {source.id for source in sources}
        removed = sorted(set(existing) - wanted)
        for source_id in removed:
            await self._index.remove_source(source_id)
        return IndexReport(indexed, unchanged, removed, failed)
