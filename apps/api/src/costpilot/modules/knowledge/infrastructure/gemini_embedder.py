import asyncio
from collections.abc import Awaitable, Callable, Sequence

import httpx
import structlog
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai._common import GoogleGenerativeAIError
from langchain_google_genai.chat_models import GoogleAPIError
from pydantic import SecretStr

from costpilot.modules.knowledge.domain.errors import KnowledgeUnavailableError

logger = structlog.get_logger()

EMBEDDING_FAILURES = (GoogleGenerativeAIError, GoogleAPIError, httpx.HTTPError)
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
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._embeddings: GoogleGenerativeAIEmbeddings | None = None
        self._batch_size = batch_size
        self._retries = retries
        self._retry_seconds = retry_seconds

    def _client(self) -> GoogleGenerativeAIEmbeddings:
        """Made on first use, so the app still starts when no Gemini key is set."""
        if self._embeddings is None:
            if not self._api_key.get_secret_value():
                raise KnowledgeUnavailableError("No Gemini key is set.")
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model=self._model,
                google_api_key=self._api_key,
                output_dimensionality=self._dimensions,
            )
        return self._embeddings

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        client = self._client()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = list(texts[start : start + self._batch_size])
            vectors += await self._with_retries(
                lambda batch=batch: client.aembed_documents(batch, task_type=DOCUMENT_TASK)
            )
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        client = self._client()
        return await self._with_retries(lambda: client.aembed_query(text, task_type=QUERY_TASK))

    async def _with_retries[T](self, call: Callable[[], Awaitable[T]]) -> T:
        """The free plan allows few requests a minute, so waiting often solves the problem."""
        for attempt in range(1, self._retries + 1):
            try:
                return await call()
            except EMBEDDING_FAILURES as error:
                logger.warning("embedding_failed", attempt=attempt, reason=type(error).__name__)
                if attempt == self._retries:
                    raise KnowledgeUnavailableError("Embeddings are unavailable.") from error
                await asyncio.sleep(self._retry_seconds * attempt)
        raise KnowledgeUnavailableError("Embeddings are unavailable.")
