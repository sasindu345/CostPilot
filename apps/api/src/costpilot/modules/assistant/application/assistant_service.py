"""The steps of answering a question, from limits to the saved answer."""

from collections.abc import AsyncIterator, Callable, Sequence
from datetime import date
from typing import Any
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
from costpilot.modules.assistant.domain.findings import validate_evidence
from costpilot.modules.assistant.domain.grades import grade_answer
from costpilot.modules.assistant.domain.guardrails import check_answer, looks_like_injection
from costpilot.modules.assistant.domain.metrics import AnswerMeter
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
    CORRECTION,
    evidence_prompt,
    history_lines,
)
from costpilot.modules.assistant.domain.templates import template_answer
from costpilot.modules.audit.contracts import AuditLog
from costpilot.modules.identity.contracts import CurrentUser
from costpilot.modules.knowledge.contracts import KnowledgeSearch
from costpilot.modules.recommendations.contracts import RecommendationReader

logger = structlog.get_logger()

OUT_OF_SCOPE_ANSWER = (
    "I can only help with cloud costs. Try asking about your spending, "
    "a cost increase, or ways to save money."
)
MODEL_DOWN_ANSWER = (
    "The AI is not available right now. Your dashboard and documents still work, "
    "so please try again in a moment."
)
BLOCKED_ANSWER = "I cannot do that. I can help with your cloud costs and saving money."
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
        recommendations: RecommendationReader,
        audit_log: AuditLog,
        daily_limit: int,
        max_question_length: int,
        history_messages: int,
        conversation_limit: int,
        answer_attempts: int,
        ai_call_limit: int,
        today: Callable[[], date],
    ) -> None:
        self._store = store
        self._limiter = limiter
        self._model = model
        self._workflow = workflow
        self._analytics = analytics
        self._knowledge = knowledge
        self._recommendations = recommendations
        self._audit_log = audit_log
        self._daily_limit = daily_limit
        self._max_question_length = max_question_length
        self._history_messages = history_messages
        self._conversation_limit = conversation_limit
        self._answer_attempts = answer_attempts
        self._ai_call_limit = ai_call_limit
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

        if looks_like_injection(question):
            async for event in self._refuse(user, conversation_id):
                yield event
            return

        yield ChatEvent("status", "Checking your bills")
        meter = AnswerMeter(ai_call_limit=self._ai_call_limit)
        tools = WorkspaceTools(
            workspace_id, self._analytics, self._knowledge, self._recommendations
        )
        try:
            gathered = await self._workflow.gather(question, tools, meter)
            has_line_detail = await tools.has_line_detail()
        except ModelUnavailableError:
            logger.warning("assistant_model_unavailable", conversation_id=str(conversation_id))
            async for event in self._finish(
                user, conversation_id, MODEL_DOWN_ANSWER, None, None, {}, meter
            ):
                yield event
            return

        evidence, dropped = validate_evidence(gathered)
        if evidence.routes == (Route.OUT_OF_SCOPE,):
            async for event in self._finish(
                user, conversation_id, OUT_OF_SCOPE_ANSWER, None, evidence, {}, meter
            ):
                yield event
            return

        yield ChatEvent("status", "Writing and checking your answer")
        text, attempts, used_template = await self._checked_answer(
            question, evidence, history, meter
        )
        used_evidence = bool(evidence.passages or evidence.findings) or any(
            fact.value in text for fact in evidence.facts
        )
        grade = grade_answer(
            evidence,
            used_template=used_template,
            has_line_detail=has_line_detail,
            used_evidence=used_evidence,
        )
        checks = {
            "evidence_dropped": dropped,
            "answer_attempts": attempts,
            "used_template": used_template,
        }
        async for event in self._finish(
            user, conversation_id, text, grade.value, evidence, checks, meter
        ):
            yield event

    async def _checked_answer(
        self,
        question: str,
        evidence: Evidence,
        history: Sequence[Message],
        meter: AnswerMeter,
    ) -> tuple[str, int, bool]:
        """Nothing reaches the user until it passes, so a wrong number is never shown."""
        prompt = evidence_prompt(question, evidence)
        lines = history_lines(history)
        for attempt in range(1, self._answer_attempts + 1):
            if attempt > 1 and not meter.can_retry():
                return template_answer(evidence), attempt - 1, True
            try:
                with meter.step("write_answer"):
                    chunks = self._model.stream_answer(ANSWER_INSTRUCTIONS, lines, prompt, meter)
                    raw = "".join([chunk async for chunk in chunks])
            except ModelUnavailableError:
                return template_answer(evidence), attempt, True
            check = check_answer(raw, evidence.facts)
            if check.passed:
                filler = PlaceholderFiller(evidence.facts)
                return filler.feed(raw) + filler.finish(), attempt, False
            logger.warning(
                "answer_rejected",
                typed=check.typed[:5],
                unknown_ids=check.unknown_ids[:5],
                misplaced=check.misplaced[:5],
            )
            prompt = f"{prompt}\n\n{CORRECTION}"
        return template_answer(evidence), self._answer_attempts, True

    async def _refuse(self, user: CurrentUser, conversation_id: UUID) -> AsyncIterator[ChatEvent]:
        checks = {"blocked_by_guardrail": True}
        async for event in self._finish(
            user, conversation_id, BLOCKED_ANSWER, None, None, checks, AnswerMeter()
        ):
            yield event

    async def _finish(
        self,
        user: CurrentUser,
        conversation_id: UUID,
        text: str,
        grade: str | None,
        evidence: Evidence | None,
        checks: dict[str, Any],
        meter: AnswerMeter,
    ) -> AsyncIterator[ChatEvent]:
        sources = self._unique_sources(evidence) if evidence else []
        trace = {
            "routes": [route.value for route in evidence.routes] if evidence else [],
            "facts": [
                {"label": fact.label, "value": fact.value}
                for fact in (evidence.facts if evidence else [])
                if fact.value in text
            ],
            "limitations": evidence.limitations if evidence else [],
            "checks": checks,
            "metrics": meter.summary(),
        }
        yield ChatEvent("text", text)
        await self._store.add_message(
            user.workspace_id, conversation_id, Role.ASSISTANT, text, sources, grade, trace
        )
        await self._audit_log.record(
            action="assistant.answered",
            workspace_id=user.workspace_id,
            user_id=user.user_id,
            details={
                "conversation_id": str(conversation_id),
                "routes": trace["routes"],
                "grade": grade,
                "sources": [source.url for source in sources],
                "checks": checks,
                "metrics": trace["metrics"],
            },
        )
        yield ChatEvent("done", sources=sources)

    async def _require_conversation(self, user: CurrentUser, conversation_id: UUID) -> None:
        if not await self._store.exists(user.workspace_id, user.user_id, conversation_id):
            raise ConversationNotFoundError

    def _unique_sources(self, evidence: Evidence) -> list[SourceLink]:
        links = {item.url: SourceLink(item.title, item.url) for item in evidence.passages}
        return list(links.values())
