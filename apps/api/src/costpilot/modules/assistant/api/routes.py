import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from costpilot.modules.assistant.application.assistant_service import AssistantService
from costpilot.modules.assistant.domain.models import ChatEvent, Conversation, Message, Role
from costpilot.modules.identity.contracts import AppSettings, CurrentUser, SignedInUser

router = APIRouter(prefix="/assistant", tags=["assistant"])


def get_assistant(request: Request) -> AssistantService:
    return request.app.state.assistant


Assistant = Annotated[AssistantService, Depends(get_assistant)]


class SourceResponse(BaseModel):
    title: str
    url: str


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime

    @classmethod
    def of(cls, item: Conversation) -> "ConversationResponse":
        return cls(id=item.id, title=item.title, created_at=item.created_at)


class MessageResponse(BaseModel):
    id: UUID
    role: Role
    content: str
    created_at: datetime
    sources: list[SourceResponse]
    grade: str | None
    trace: dict[str, Any]

    @classmethod
    def of(cls, item: Message) -> "MessageResponse":
        return cls(
            id=item.id,
            role=item.role,
            content=item.content,
            created_at=item.created_at,
            sources=[SourceResponse(title=s.title, url=s.url) for s in item.sources],
            grade=item.grade,
            trace=item.trace,
        )


class AssistantInfoResponse(BaseModel):
    suggestions: list[str]
    is_free_tier: bool


class QuestionRequest(BaseModel):
    question: str


@router.get("/info")
async def info(
    _: SignedInUser, assistant: Assistant, settings: AppSettings
) -> AssistantInfoResponse:
    return AssistantInfoResponse(
        suggestions=list(assistant.suggestions()),
        is_free_tier=settings.gemini_tier == "free",
    )


@router.get("/conversations")
async def list_conversations(
    user: SignedInUser, assistant: Assistant
) -> list[ConversationResponse]:
    return [ConversationResponse.of(item) for item in await assistant.conversations(user)]


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def start_conversation(user: SignedInUser, assistant: Assistant) -> ConversationResponse:
    return ConversationResponse.of(await assistant.start_conversation(user))


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: UUID, user: SignedInUser, assistant: Assistant
) -> list[MessageResponse]:
    return [MessageResponse.of(item) for item in await assistant.messages(user, conversation_id)]


def _as_server_sent_event(event: ChatEvent) -> str:
    sources = [{"title": item.title, "url": item.url} for item in event.sources]
    return f"data: {json.dumps({'type': event.type, 'text': event.text, 'sources': sources})}\n\n"


async def _event_stream(
    assistant: AssistantService, user: CurrentUser, conversation_id: UUID, question: str
) -> AsyncIterator[str]:
    async for event in assistant.answer(user, conversation_id, question):
        yield _as_server_sent_event(event)


@router.post("/conversations/{conversation_id}/messages")
async def ask(
    conversation_id: UUID, body: QuestionRequest, user: SignedInUser, assistant: Assistant
) -> StreamingResponse:
    question = await assistant.prepare_question(user, conversation_id, body.question)
    return StreamingResponse(
        _event_stream(assistant, user, conversation_id, question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
