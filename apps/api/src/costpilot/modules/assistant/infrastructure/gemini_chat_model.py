from collections.abc import AsyncIterator, Sequence

import httpx
import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai._common import GoogleGenerativeAIError
from langchain_google_genai.chat_models import GoogleAPIError
from pydantic import BaseModel, SecretStr

from costpilot.modules.assistant.domain.errors import ModelUnavailableError
from costpilot.modules.assistant.domain.findings import FindingDraft
from costpilot.modules.assistant.domain.metrics import AnswerMeter
from costpilot.modules.assistant.domain.models import Role, Route, RoutePlan
from costpilot.modules.assistant.domain.prompts import ROUTER_INSTRUCTIONS

logger = structlog.get_logger()

# The supervisor's answer is checked, so a made-up cloud name cannot reach the search filter.
KNOWN_CLOUDS = {"aws", "azure", "gcp", "oci", "digitalocean"}

REASON_LENGTH = 200
# An idle connection can go stale, and a second try opens a fresh one.
ATTEMPTS = 2
# Gemini can fail with its own errors, or the connection itself can drop.
MODEL_FAILURES = (GoogleGenerativeAIError, GoogleAPIError, httpx.HTTPError)


class RouteChoice(BaseModel):
    routes: list[Route]
    providers: list[str] = []


class FindingList(BaseModel):
    findings: list[FindingDraft]


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
        self._api_key = api_key
        self._answer_model = answer_model
        self._router_model = router_model
        self._timeout_seconds = timeout_seconds
        self._retries = retries
        self._answers: ChatGoogleGenerativeAI | None = None
        self._router: ChatGoogleGenerativeAI | None = None

    def _client(self, model: str) -> ChatGoogleGenerativeAI:
        """Made on first use, so the app still starts when no Gemini key is set."""
        if not self._api_key.get_secret_value():
            logger.warning("gemini_key_missing")
            raise ModelUnavailableError
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=self._api_key,
            timeout=self._timeout_seconds,
            retries=self._retries,
        )

    async def choose_routes(self, question: str, meter: AnswerMeter) -> RoutePlan:
        self._router = self._router or self._client(self._router_model)
        messages = [SystemMessage(ROUTER_INSTRUCTIONS), HumanMessage(question)]
        choice = await self._structured(self._router, RouteChoice, messages, "route", meter)
        routes = list(dict.fromkeys(choice.routes)) if choice else []
        named = [name.lower() for name in choice.providers] if choice else []
        return RoutePlan(clean_routes(routes), [name for name in named if name in KNOWN_CLOUDS])

    async def find_findings(
        self, instructions: str, prompt: str, meter: AnswerMeter
    ) -> list[FindingDraft]:
        self._answers = self._answers or self._client(self._answer_model)
        messages = [SystemMessage(instructions), HumanMessage(prompt)]
        result = await self._structured(self._answers, FindingList, messages, "specialist", meter)
        return result.findings if result else []

    async def _structured[T: BaseModel](
        self,
        client: ChatGoogleGenerativeAI,
        schema: type[T],
        messages: list[BaseMessage],
        step: str,
        meter: AnswerMeter,
    ) -> T | None:
        """Pydantic checks the reply. A reply that does not fit the format counts as no reply."""
        structured = client.with_structured_output(schema, include_raw=True)
        for attempt in range(1, ATTEMPTS + 1):
            try:
                result = await structured.ainvoke(messages)
                break
            except MODEL_FAILURES as error:
                self._log_failure(step, attempt, error)
                if attempt == ATTEMPTS:
                    raise ModelUnavailableError from error
        self._record_usage(meter, result["raw"])
        return result["parsed"]

    async def stream_answer(
        self,
        system: str,
        history: Sequence[tuple[str, str]],
        prompt: str,
        meter: AnswerMeter,
    ) -> AsyncIterator[str]:
        self._answers = self._answers or self._client(self._answer_model)
        messages: list[BaseMessage] = [SystemMessage(system)]
        for role, content in history:
            is_user = role == Role.USER.value
            messages.append(HumanMessage(content) if is_user else AIMessage(content))
        messages.append(HumanMessage(prompt))

        for attempt in range(1, ATTEMPTS + 1):
            has_started = False
            input_tokens = output_tokens = 0
            try:
                async for chunk in self._answers.astream(messages):
                    usage = chunk.usage_metadata or {}
                    input_tokens += usage.get("input_tokens", 0)
                    output_tokens += usage.get("output_tokens", 0)
                    if text := chunk.text:
                        has_started = True
                        yield text
                meter.add_ai_call(input_tokens, output_tokens)
                return
            except MODEL_FAILURES as error:
                self._log_failure("answer", attempt, error)
                # Once words have reached the user, starting again would repeat them.
                if has_started or attempt == ATTEMPTS:
                    raise ModelUnavailableError from error

    def _record_usage(self, meter: AnswerMeter, message: object) -> None:
        usage = getattr(message, "usage_metadata", None) or {}
        meter.add_ai_call(usage.get("input_tokens", 0), usage.get("output_tokens", 0))

    def _log_failure(self, step: str, attempt: int, error: Exception) -> None:
        logger.warning(
            "gemini_failed", step=step, attempt=attempt, reason=str(error)[:REASON_LENGTH]
        )
