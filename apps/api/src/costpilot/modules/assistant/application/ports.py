from collections.abc import AsyncIterator, Mapping, Sequence
from datetime import date
from typing import Any, Protocol
from uuid import UUID

from costpilot.modules.assistant.application.workspace_tools import WorkspaceTools
from costpilot.modules.assistant.domain.metrics import AnswerMeter
from costpilot.modules.assistant.domain.models import (
    Conversation,
    Evidence,
    Message,
    Role,
    Route,
    SourceLink,
)


class ChatModel(Protocol):
    async def choose_routes(self, question: str, meter: AnswerMeter) -> list[Route]: ...

    def stream_answer(
        self, system: str, history: Sequence[tuple[str, str]], prompt: str, meter: AnswerMeter
    ) -> AsyncIterator[str]: ...


class EvidenceWorkflow(Protocol):
    async def gather(self, question: str, tools: WorkspaceTools, meter: AnswerMeter) -> Evidence:
        """Run the supervisor and its chosen specialists, and return what they found."""


class ConversationStore(Protocol):
    async def create(self, workspace_id: UUID, user_id: UUID, title: str) -> Conversation: ...

    async def list_for_user(
        self, workspace_id: UUID, user_id: UUID, limit: int
    ) -> list[Conversation]: ...

    async def exists(self, workspace_id: UUID, user_id: UUID, conversation_id: UUID) -> bool: ...

    async def messages(
        self, workspace_id: UUID, conversation_id: UUID, limit: int | None = None
    ) -> list[Message]: ...

    async def add_message(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        role: Role,
        content: str,
        sources: Sequence[SourceLink] = (),
        grade: str | None = None,
        trace: Mapping[str, Any] | None = None,
    ) -> Message: ...

    async def set_title_if_new(
        self, workspace_id: UUID, conversation_id: UUID, title: str
    ) -> None: ...


class UsageLimiter(Protocol):
    async def try_consume(self, workspace_id: UUID, day: date, limit: int) -> bool:
        """Count one question. Return False if today's limit is already reached."""
