"""Whatever way Gemini fails, the rest of the app must get one clear error."""

from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_google_genai._common import GoogleGenerativeAIError
from langchain_google_genai.chat_models import GoogleAPIError
from pydantic import SecretStr

from costpilot.main import create_app
from costpilot.modules.assistant.domain.errors import ModelUnavailableError
from costpilot.modules.assistant.domain.metrics import AnswerMeter
from costpilot.modules.assistant.infrastructure.gemini_chat_model import GeminiChatModel
from costpilot.modules.knowledge.domain.errors import KnowledgeUnavailableError
from costpilot.modules.knowledge.infrastructure.gemini_embedder import GeminiEmbedder
from costpilot.shared.config import get_settings

FAILURES = [
    GoogleGenerativeAIError("failed"),
    GoogleAPIError(503, {"error": {"status": "UNAVAILABLE", "message": "busy"}}),
    httpx.ReadTimeout("slow"),
    httpx.RemoteProtocolError("Server disconnected"),
]


class BrokenAnswers:
    def __init__(self, error):
        self.error = error

    async def astream(self, messages):
        raise self.error
        yield


class BrokenEmbeddings:
    def __init__(self, error):
        self.error = error

    async def aembed_query(self, text, task_type):
        raise self.error


def chat_model(key="test"):
    return GeminiChatModel(SecretStr(key), "test-model", "test-model", 1, 0)


@pytest.mark.parametrize("failure", FAILURES)
async def test_answer_failures_become_one_clear_error(failure):
    model = chat_model()
    model._answers = BrokenAnswers(failure)

    with pytest.raises(ModelUnavailableError):
        [chunk async for chunk in model.stream_answer("system", [], "prompt", AnswerMeter())]


@pytest.mark.parametrize("failure", FAILURES)
async def test_embedding_failures_become_one_clear_error(failure):
    embedder = GeminiEmbedder(SecretStr("test"), "test-model", 8, 2, retries=1, retry_seconds=0)
    embedder._embeddings = BrokenEmbeddings(failure)

    with pytest.raises(KnowledgeUnavailableError):
        await embedder.embed_query("question")


class FlakyAnswers:
    """Fails once, then works, like a stale connection."""

    def __init__(self):
        self.calls = 0

    async def astream(self, messages):
        self.calls += 1
        if self.calls == 1:
            raise httpx.RemoteProtocolError("Server disconnected")
        yield SimpleNamespace(text="Hello")


class FailsAfterFirstWord:
    def __init__(self):
        self.calls = 0

    async def astream(self, messages):
        self.calls += 1
        yield SimpleNamespace(text="Hello")
        raise httpx.ReadTimeout("slow")


async def test_a_stale_connection_is_retried_once():
    model = chat_model()
    model._answers = FlakyAnswers()

    chunks = [chunk async for chunk in model.stream_answer("system", [], "prompt", AnswerMeter())]

    assert chunks == ["Hello"]


async def test_an_answer_is_never_restarted_after_words_were_sent():
    model = chat_model()
    model._answers = answers = FailsAfterFirstWord()

    with pytest.raises(ModelUnavailableError):
        [chunk async for chunk in model.stream_answer("system", [], "prompt", AnswerMeter())]

    assert answers.calls == 1


async def test_without_a_key_the_assistant_reports_it_is_unavailable():
    model = chat_model(key="")

    with pytest.raises(ModelUnavailableError):
        await model.choose_routes("question", AnswerMeter())
    with pytest.raises(ModelUnavailableError):
        [chunk async for chunk in model.stream_answer("system", [], "prompt", AnswerMeter())]


async def test_without_a_key_search_reports_it_is_unavailable():
    embedder = GeminiEmbedder(SecretStr(""), "test-model", 8, 2, retries=1, retry_seconds=0)

    with pytest.raises(KnowledgeUnavailableError):
        await embedder.embed_query("question")


def test_the_app_starts_without_a_gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    try:
        response = TestClient(create_app()).get("/api/health")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
