from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

from httpx import HTTPError
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ApiException
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from costpilot.modules.knowledge.domain.errors import KnowledgeUnavailableError
from costpilot.modules.knowledge.domain.models import Passage, Source

SCROLL_PAGE = 256
SEARCH_FAILURES = (ApiException, HTTPError, OSError, ValueError)


def _matches(field: str, value: str) -> Filter:
    return Filter(must=[FieldCondition(key=field, match=MatchValue(value=value))])


class QdrantVectorIndex:
    def __init__(self, client: AsyncQdrantClient, collection: str, dimensions: int) -> None:
        self._client = client
        self._collection = collection
        self._dimensions = dimensions

    async def prepare(self) -> None:
        if await self._client.collection_exists(self._collection):
            return
        await self._client.create_collection(
            self._collection,
            vectors_config=VectorParams(size=self._dimensions, distance=Distance.COSINE),
        )
        for field in ("provider", "source_id"):
            await self._client.create_payload_index(
                self._collection, field, field_schema=PayloadSchemaType.KEYWORD
            )

    async def indexed_hashes(self) -> dict[str, str]:
        hashes: dict[str, str] = {}
        offset = None
        while True:
            points, offset = await self._client.scroll(
                self._collection, limit=SCROLL_PAGE, offset=offset, with_payload=True
            )
            for point in points:
                hashes[point.payload["source_id"]] = point.payload["text_hash"]
            if offset is None:
                return hashes

    async def replace_source(
        self,
        source: Source,
        text_hash: str,
        chunks: Sequence[str],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        await self.remove_source(source.id)
        points = [
            PointStruct(
                id=str(uuid5(NAMESPACE_URL, f"{source.id}:{text_hash}:{position}")),
                vector=list(vector),
                payload={
                    "source_id": source.id,
                    "provider": source.provider,
                    "topic": source.topic,
                    "title": source.title,
                    "url": source.url,
                    "text": chunk,
                    "text_hash": text_hash,
                },
            )
            for position, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
        ]
        await self._client.upsert(self._collection, points=points)

    async def remove_source(self, source_id: str) -> None:
        await self._client.delete(
            self._collection,
            points_selector=FilterSelector(filter=_matches("source_id", source_id)),
        )

    async def search(
        self, vector: Sequence[float], providers: Sequence[str], limit: int, min_score: float
    ) -> list[Passage]:
        try:
            response = await self._client.query_points(
                self._collection,
                query=list(vector),
                query_filter=Filter(
                    must=[FieldCondition(key="provider", match=MatchAny(any=list(providers)))]
                ),
                limit=limit,
                score_threshold=min_score,
                with_payload=True,
            )
        except SEARCH_FAILURES as error:
            raise KnowledgeUnavailableError("Documentation search is unavailable.") from error
        return [
            Passage(
                source_id=point.payload["source_id"],
                provider=point.payload["provider"],
                title=point.payload["title"],
                url=point.payload["url"],
                text=point.payload["text"],
                score=point.score,
            )
            for point in response.points
        ]
