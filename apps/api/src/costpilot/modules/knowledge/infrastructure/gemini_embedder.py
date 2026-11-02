import asyncio
from collections.abc import Awaitable, Callable, Sequence

import structlog
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai._common import GoogleGenerativeAIError
from pydantic import SecretStr

from costpilot.modules.knowledge.domain.errors import KnowledgeUnavailableError

logger = structlog.get_logger()

DOCUMENT_TASK = "RETRIEVAL_DOCUMENT"
QUERY_TASK = "RETRIEVAL_QUERY"


class GeminiEmbedder:
    def __init__(
        self,
        api_key: SecretStr,
        model: str,
        dimensions: int,
        batch_size: int,
        retries: int,
        retry_seconds: float,
    ) -> None:
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=model, google_api_key=api_key, output_dimensionality=dimensions
        )
        self._batch_size = batch_size
        self._retries = retries
        self._retry_seconds = retry_seconds

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = list(texts[start : start + self._batch_size])
            vectors += await self._with_retries(
                lambda batch=batch: self._embeddings.aembed_documents(
                    batch, task_type=DOCUMENT_TASK
                )
            )
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        return await self._with_retries(
            lambda: self._embeddings.aembed_query(text, task_type=QUERY_TASK)
        )

    async def _with_retries[T](self, call: Callable[[], Awaitable[T]]) -> T:
        """The free plan allows few requests a minute, so waiting often solves the problem."""
        for attempt in range(1, self._retries + 1):
            try:
                return await call()
            except GoogleGenerativeAIError as error:
                logger.warning("embedding_failed", attempt=attempt, reason=type(error).__name__)
                if attempt == self._retries:
                    raise KnowledgeUnavailableError("Embeddings are unavailable.") from error
                await asyncio.sleep(self._retry_seconds * attempt)
        raise KnowledgeUnavailableError("Embeddings are unavailable.")
