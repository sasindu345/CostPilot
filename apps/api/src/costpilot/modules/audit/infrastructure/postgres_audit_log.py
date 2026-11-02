from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.expression import bindparam

from costpilot.shared.database import Database

INSERT_EVENT = text(
    "INSERT INTO audit_events (workspace_id, user_id, action, details) "
    "VALUES (:workspace_id, :user_id, :action, :details)"
).bindparams(bindparam("details", type_=JSONB))


class PostgresAuditLog:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def record(
        self, *, action: str, workspace_id: UUID, user_id: UUID, details: dict[str, Any]
    ) -> None:
        async with self._database.transaction(user_id=user_id, workspace_id=workspace_id) as db:
            await db.execute(
                INSERT_EVENT,
                {
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "action": action,
                    "details": details,
                },
            )
