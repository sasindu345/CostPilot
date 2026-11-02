from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Row as SqlRow
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from costpilot.modules.assistant.domain.models import Conversation, Message, Role, SourceLink
from costpilot.shared.database import Database

INSERT_CONVERSATION = text(
    "INSERT INTO conversations (id, workspace_id, user_id, title) "
    "VALUES (:id, :workspace_id, :user_id, :title) RETURNING id, title, created_at"
)
LIST_CONVERSATIONS = text(
    "SELECT id, title, created_at FROM conversations WHERE user_id = :user_id "
    "ORDER BY created_at DESC LIMIT :limit"
)
CONVERSATION_EXISTS = text(
    "SELECT EXISTS (SELECT 1 FROM conversations WHERE id = :id AND user_id = :user_id)"
)
SET_TITLE = text(
    "UPDATE conversations SET title = :title WHERE id = :id AND NOT EXISTS "
    "(SELECT 1 FROM messages WHERE conversation_id = :id AND role = 'assistant')"
)
LAST_MESSAGES = text(
    "SELECT * FROM (SELECT id, role, content, sources, grade, trace, created_at FROM messages "
    "WHERE conversation_id = :id ORDER BY created_at DESC, id LIMIT :limit) recent "
    "ORDER BY created_at, id"
)
INSERT_MESSAGE = text(
    "INSERT INTO messages "
    "(id, conversation_id, workspace_id, role, content, sources, grade, trace) "
    "VALUES (:id, :conversation_id, :workspace_id, :role, :content, :sources, :grade, :trace) "
    "RETURNING id, role, content, sources, grade, trace, created_at"
).bindparams(bindparam("sources", type_=JSONB), bindparam("trace", type_=JSONB))
CONSUME_QUESTION = text(
    "INSERT INTO assistant_usage (workspace_id, day, questions) VALUES (:workspace_id, :day, 1) "
    "ON CONFLICT (workspace_id, day) DO UPDATE SET questions = assistant_usage.questions + 1 "
    "WHERE assistant_usage.questions < :limit RETURNING questions"
)
ALL_MESSAGES = 1_000_000


def _to_message(row: SqlRow) -> Message:
    return Message(
        id=row.id,
        role=Role(row.role),
        content=row.content,
        created_at=row.created_at,
        sources=[SourceLink(item["title"], item["url"]) for item in row.sources],
        grade=row.grade,
        trace=row.trace,
    )


class PostgresConversationStore:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, workspace_id: UUID, user_id: UUID, title: str) -> Conversation:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            row = (
                await db.execute(
                    INSERT_CONVERSATION,
                    {
                        "id": uuid4(),
                        "workspace_id": workspace_id,
                        "user_id": user_id,
                        "title": title,
                    },
                )
            ).one()
            return Conversation(row.id, row.title, row.created_at)

    async def list_for_user(
        self, workspace_id: UUID, user_id: UUID, limit: int
    ) -> list[Conversation]:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            rows = await db.execute(LIST_CONVERSATIONS, {"user_id": user_id, "limit": limit})
            return [Conversation(row.id, row.title, row.created_at) for row in rows]

    async def exists(self, workspace_id: UUID, user_id: UUID, conversation_id: UUID) -> bool:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            query = await db.execute(
                CONVERSATION_EXISTS, {"id": conversation_id, "user_id": user_id}
            )
            return query.scalar_one()

    async def messages(
        self, workspace_id: UUID, conversation_id: UUID, limit: int | None = None
    ) -> list[Message]:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            rows = await db.execute(
                LAST_MESSAGES, {"id": conversation_id, "limit": limit or ALL_MESSAGES}
            )
            return [_to_message(row) for row in rows]

    async def add_message(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        role: Role,
        content: str,
        sources: Sequence[SourceLink] = (),
        grade: str | None = None,
        trace: Mapping[str, Any] | None = None,
    ) -> Message:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            row = (
                await db.execute(
                    INSERT_MESSAGE,
                    {
                        "id": uuid4(),
                        "conversation_id": conversation_id,
                        "workspace_id": workspace_id,
                        "role": role.value,
                        "content": content,
                        "sources": [{"title": s.title, "url": s.url} for s in sources],
                        "grade": grade,
                        "trace": dict(trace or {}),
                    },
                )
            ).one()
            return _to_message(row)

    async def set_title_if_new(self, workspace_id: UUID, conversation_id: UUID, title: str) -> None:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            await db.execute(SET_TITLE, {"id": conversation_id, "title": title})


class PostgresUsageLimiter:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def try_consume(self, workspace_id: UUID, day: date, limit: int) -> bool:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            result = await db.execute(
                CONSUME_QUESTION, {"workspace_id": workspace_id, "day": day, "limit": limit}
            )
            return result.first() is not None
