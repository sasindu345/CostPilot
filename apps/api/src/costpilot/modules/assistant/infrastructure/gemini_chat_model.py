from collections.abc import AsyncIterator, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai._common import GoogleGenerativeAIError
from pydantic import BaseModel, SecretStr

from costpilot.modules.assistant.domain.errors import ModelUnavailableError
from costpilot.modules.assistant.domain.models import Role, Route
from costpilot.modules.assistant.domain.prompts import ROUTER_INSTRUCTIONS


class RouteChoice(BaseModel):
    route: Route


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

    async def choose_route(self, question: str) -> Route:
        structured = self._router.with_structured_output(RouteChoice)
        try:
            choice = await structured.ainvoke(
                [SystemMessage(ROUTER_INSTRUCTIONS), HumanMessage(question)]
            )
        except GoogleGenerativeAIError as error:
            raise ModelUnavailableError from error
        return choice.route if choice else Route.COST

    async def stream_answer(
        self, system: str, history: Sequence[tuple[str, str]], prompt: str
    ) -> AsyncIterator[str]:
        messages: list[BaseMessage] = [SystemMessage(system)]
        for role, content in history:
            is_user = role == Role.USER.value
            messages.append(HumanMessage(content) if is_user else AIMessage(content))
        messages.append(HumanMessage(prompt))
        try:
            async for chunk in self._answers.astream(messages):
                if text := chunk.text:
                    yield text
        except GoogleGenerativeAIError as error:
            raise ModelUnavailableError from error
