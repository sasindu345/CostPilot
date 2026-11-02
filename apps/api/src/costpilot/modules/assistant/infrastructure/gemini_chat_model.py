from collections.abc import AsyncIterator, Sequence

import httpx
import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai._common import GoogleGenerativeAIError
from langchain_google_genai.chat_models import GoogleAPIError
from pydantic import BaseModel, SecretStr

from costpilot.modules.assistant.domain.errors import ModelUnavailableError
from costpilot.modules.assistant.domain.models import Role, Route
from costpilot.modules.assistant.domain.prompts import ROUTER_INSTRUCTIONS

logger = structlog.get_logger()

REASON_LENGTH = 200
# An idle connection can go stale, and a second try opens a fresh one.
ATTEMPTS = 2
# Gemini can fail with its own errors, or the connection itself can drop.
MODEL_FAILURES = (GoogleGenerativeAIError, GoogleAPIError, httpx.HTTPError)


class RouteChoice(BaseModel):
    routes: list[Route]


def clean_routes(routes: list[Route]) -> list[Route]:
    """Off-topic only stands alone, and no choice at all falls back to showing the costs."""
    useful = [route for route in routes if route is not Route.OUT_OF_SCOPE]
    return useful or routes or [Route.COST]


class GeminiChatModel:
    def __init__(
        self,
        api_key: SecretStr,
        answer_model: str,
        router_model: str,
        timeout_seconds: float,
        retries: int,
    ) -> None:
        settings = {"google_api_key": api_key, "timeout": timeout_seconds, "retries": retries}
        self._answers = ChatGoogleGenerativeAI(model=answer_model, **settings)
        self._router = ChatGoogleGenerativeAI(model=router_model, **settings)

    async def choose_routes(self, question: str) -> list[Route]:
        structured = self._router.with_structured_output(RouteChoice)
        messages = [SystemMessage(ROUTER_INSTRUCTIONS), HumanMessage(question)]
        for attempt in range(1, ATTEMPTS + 1):
            try:
                choice = await structured.ainvoke(messages)
                break
            except MODEL_FAILURES as error:
                self._log_failure("route", attempt, error)
                if attempt == ATTEMPTS:
                    raise ModelUnavailableError from error
        routes = list(dict.fromkeys(choice.routes)) if choice else []
        return clean_routes(routes)

    async def stream_answer(
        self, system: str, history: Sequence[tuple[str, str]], prompt: str
    ) -> AsyncIterator[str]:
        messages: list[BaseMessage] = [SystemMessage(system)]
        for role, content in history:
            is_user = role == Role.USER.value
            messages.append(HumanMessage(content) if is_user else AIMessage(content))
        messages.append(HumanMessage(prompt))

        for attempt in range(1, ATTEMPTS + 1):
            has_started = False
            try:
                async for chunk in self._answers.astream(messages):
                    if text := chunk.text:
                        has_started = True
                        yield text
                return
            except MODEL_FAILURES as error:
                self._log_failure("answer", attempt, error)
                # Once words have reached the user, starting again would repeat them.
                if has_started or attempt == ATTEMPTS:
                    raise ModelUnavailableError from error

    def _log_failure(self, step: str, attempt: int, error: Exception) -> None:
        logger.warning(
            "gemini_failed", step=step, attempt=attempt, reason=str(error)[:REASON_LENGTH]
        )
