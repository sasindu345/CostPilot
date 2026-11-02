from collections.abc import Sequence
from typing import Protocol

from costpilot.modules.knowledge.domain.models import Passage, Source


class PageLoader(Protocol):
    async def load(self, source: Source) -> str:
        """Return the page's readable text."""


class TextSplitter(Protocol):
    def split(self, text: str) -> list[str]: ...


class Embedder(Protocol):
    """Turns text into lists of numbers, so similar meanings sit close together."""

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class VectorIndex(Protocol):
    async def prepare(self) -> None: ...

    async def indexed_hashes(self) -> dict[str, str]:
        """Return each indexed source's id and the hash of the text it was built from."""

    async def replace_source(
        self,
        source: Source,
        text_hash: str,
        chunks: Sequence[str],
        vectors: Sequence[Sequence[float]],
    ) -> None: ...

    async def remove_source(self, source_id: str) -> None: ...

    async def search(
        self, vector: Sequence[float], provider: str, limit: int, min_score: float
    ) -> list[Passage]: ...
