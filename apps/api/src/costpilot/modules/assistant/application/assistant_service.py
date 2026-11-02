"""The steps of answering a question, from limits to the saved answer."""

from collections.abc import AsyncIterator, Callable
from datetime import date
from uuid import UUID

import structlog

from costpilot.modules.analytics.contracts import AnalyticsReader
from costpilot.modules.assistant.application.ports import (
    ChatModel,
    ConversationStore,
    EvidenceWorkflow,
    UsageLimiter,
)
from costpilot.modules.assistant.application.workspace_tools import WorkspaceTools
from costpilot.modules.assistant.domain.errors import (
    ConversationNotFoundError,
    DailyLimitReachedError,
    ModelUnavailableError,
    QuestionRejectedError,
)
from costpilot.modules.assistant.domain.models import (
    ChatEvent,
    Conversation,
    Evidence,
    Message,
    Role,
    Route,
    SourceLink,
)
from costpilot.modules.assistant.domain.placeholders import PlaceholderFiller
from costpilot.modules.assistant.domain.prompts import (
    ANSWER_INSTRUCTIONS,
    evidence_prompt,
    history_lines,
)
from costpilot.modules.audit.contracts import AuditLog
from costpilot.modules.identity.contracts import CurrentUser
from costpilot.modules.knowledge.contracts import KnowledgeSearch

logger = structlog.get_logger()

OUT_OF_SCOPE_ANSWER = (
    "I can only help with cloud costs. Try asking about your spending, "
    "a cost increase, or ways to save money."
)
MODEL_DOWN_ANSWER = (
    "The AI is not available right now. Your dashboard and documents still work, "
    "so please try again in a moment."
)
NEW_TITLE = "New conversation"
TITLE_LENGTH = 60
SUGGESTED_QUESTIONS = (
    "Summarize my cloud spending",
    "Why did my EC2 cost increase?",
    "Give me cost optimization suggestions",
    "Explain AWS Savings Plans",
)


class AssistantService:
    def __init__(
        self,
        store: ConversationStore,
        limiter: UsageLimiter,
        model: ChatModel,
        workflow: EvidenceWorkflow,
        analytics: AnalyticsReader,
        knowledge: KnowledgeSearch,
        audit_log: AuditLog,
        daily_limit: int,
        max_question_length: int,
        history_messages: int,
        conversation_limit: int,
        today: Callable[[], date],
    ) -> None:
        self._store = store
        self._limiter = limiter
        self._model = model
        self._workflow = workflow
        self._analytics = analytics
        self._knowledge = knowledge
        self._audit_log = audit_log
        self._daily_limit = daily_limit
        self._max_question_length = max_question_length
        self._history_messages = history_messages
        self._conversation_limit = conversation_limit
        self._today = today

    def suggestions(self) -> tuple[str, ...]:
        return SUGGESTED_QUESTIONS

    async def conversations(self, user: CurrentUser) -> list[Conversation]:
        return await self._store.list_for_user(
            user.workspace_id, user.user_id, self._conversation_limit
        )

    async def start_conversation(self, user: CurrentUser) -> Conversation:
        return await self._store.create(user.workspace_id, user.user_id, NEW_TITLE)

    async def messages(self, user: CurrentUser, conversation_id: UUID) -> list[Message]:
        await self._require_conversation(user, conversation_id)
        return await self._store.messages(user.workspace_id, conversation_id)

    async def prepare_question(
        self, user: CurrentUser, conversation_id: UUID, question: str
    ) -> str:
        """Do every check before streaming starts, so failures are normal API errors."""
        await self._require_conversation(user, conversation_id)
        cleaned = question.strip()
        if not cleaned:
            raise QuestionRejectedError("Please type a question.")
        if len(cleaned) > self._max_question_length:
            raise QuestionRejectedError(
                f"Please keep your question under {self._max_question_length} characters."
            )
        allowed = await self._limiter.try_consume(
            user.workspace_id, self._today(), self._daily_limit
        )
        if not allowed:
            raise DailyLimitReachedError
        return cleaned

    async def answer(
        self, user: CurrentUser, conversation_id: UUID, question: str
    ) -> AsyncIterator[ChatEvent]:
        workspace_id = user.workspace_id
        history = await self._store.messages(workspace_id, conversation_id, self._history_messages)
        await self._store.add_message(workspace_id, conversation_id, Role.USER, question)
        await self._store.set_title_if_new(workspace_id, conversation_id, question[:TITLE_LENGTH])

        yield ChatEvent("status", "Checking your bills")
        tools = WorkspaceTools(workspace_id, self._analytics, self._knowledge)
        text = ""
        sources: list[SourceLink] = []
        route = None
        try:
            evidence = await self._workflow.gather(question, tools)
            route = evidence.route
            sources = self._unique_sources(evidence)
            if route is Route.OUT_OF_SCOPE:
                text = OUT_OF_SCOPE_ANSWER
                yield ChatEvent("text", text)
            else:
                yield ChatEvent("status", "Writing your answer")
                filler = PlaceholderFiller(evidence.facts)
                prompt = evidence_prompt(question, evidence)
                async for chunk in self._model.stream_answer(
                    ANSWER_INSTRUCTIONS, history_lines(history), prompt
                ):
                    if filled := filler.feed(chunk):
                        text += filled
                        yield ChatEvent("text", filled)
                if rest := filler.finish():
                    text += rest
                    yield ChatEvent("text", rest)
        except ModelUnavailableError:
            logger.warning("assistant_model_unavailable", conversation_id=str(conversation_id))
            text = MODEL_DOWN_ANSWER
            sources = []
            yield ChatEvent("replace", text)

        await self._store.add_message(workspace_id, conversation_id, Role.ASSISTANT, text, sources)
        await self._audit_log.record(
            action="assistant.answered",
            workspace_id=workspace_id,
            user_id=user.user_id,
            details={
                "conversation_id": str(conversation_id),
                "route": route.value if route else "unavailable",
                "sources": [source.url for source in sources],
            },
        )
        yield ChatEvent("done", sources=sources)

    async def _require_conversation(self, user: CurrentUser, conversation_id: UUID) -> None:
        if not await self._store.exists(user.workspace_id, user.user_id, conversation_id):
            raise ConversationNotFoundError

    def _unique_sources(self, evidence: Evidence) -> list[SourceLink]:
        links = {item.url: SourceLink(item.title, item.url) for item in evidence.passages}
        return list(links.values())
