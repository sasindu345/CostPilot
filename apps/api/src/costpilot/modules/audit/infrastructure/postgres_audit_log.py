from typing import Any
from uuid import UUID

from opentelemetry import metrics
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.expression import bindparam

from costpilot.shared.database import Database

INSERT_EVENT = text(
    "INSERT INTO audit_events (workspace_id, user_id, action, details) "
    "VALUES (:workspace_id, :user_id, :action, :details)"
).bindparams(bindparam("details", type_=JSONB))


# Every audited action is also counted, so dashboards show uploads, sign-ins and answer grades.
EVENTS = metrics.get_meter("costpilot.audit").create_counter(
    "costpilot.events", description="Audited actions, such as uploads and answers"
)


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
        attributes = {"action": action}
        if isinstance(grade := details.get("grade"), str):
            attributes["grade"] = grade
        EVENTS.add(1, attributes)
