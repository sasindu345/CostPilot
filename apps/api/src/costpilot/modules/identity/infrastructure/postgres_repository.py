from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from costpilot.modules.identity.domain.models import CurrentUser, VerifiedIdentity
from costpilot.shared.database import Database, set_context

UPSERT_USER = text(
    "INSERT INTO users (keycloak_subject, email, display_name) "
    "VALUES (:subject, :email, :display_name) "
    "ON CONFLICT (keycloak_subject) DO UPDATE "
    "SET email = EXCLUDED.email, display_name = EXCLUDED.display_name "
    "RETURNING id, (xmax = 0) AS is_new"
)
FIND_WORKSPACE = text(
    "SELECT workspace_id, role FROM memberships WHERE user_id = :user_id "
    "ORDER BY created_at LIMIT 1"
)
FIND_WORKSPACE_NAME = text("SELECT name FROM workspaces WHERE id = :workspace_id")
INSERT_WORKSPACE = text("INSERT INTO workspaces (id, name) VALUES (:id, :name)")
INSERT_MEMBERSHIP = text(
    "INSERT INTO memberships (workspace_id, user_id, role) VALUES (:workspace_id, :user_id, :role)"
)
DELETE_EXPIRED_SESSIONS = text("DELETE FROM sessions WHERE expires_at <= now()")
INSERT_SESSION = text(
    "INSERT INTO sessions (token_hash, user_id, sealed_id_token, expires_at) "
    "VALUES (:token_hash, :user_id, :sealed_id_token, :expires_at)"
)
FIND_SESSION = text(
    "SELECT s.sealed_id_token, u.id, u.email, u.display_name "
    "FROM sessions s JOIN users u ON u.id = s.user_id "
    "WHERE s.token_hash = :token_hash AND s.expires_at > :now"
)
DELETE_SESSION = text("DELETE FROM sessions WHERE token_hash = :token_hash")
FIND_SUBJECT = text("SELECT keycloak_subject FROM users WHERE id = :user_id")
COUNT_MEMBERS = text(
    "SELECT count(*) AS members, count(*) FILTER (WHERE user_id = :user_id) AS mine "
    "FROM memberships WHERE workspace_id = :workspace_id"
)
DELETE_WORKSPACE = text("DELETE FROM workspaces WHERE id = :workspace_id")
DELETE_USER = text("DELETE FROM users WHERE id = :user_id")


def _rows(table: str, hidden: str = "", order: str = "created_at") -> str:
    """All of one table's rows in the workspace, as a JSON list. Internal columns are left out."""
    # Only called below, with fixed table and column names.
    columns = f"to_jsonb(t) - 'workspace_id'{hidden}"
    query = f"SELECT coalesce(jsonb_agg({columns} ORDER BY t.{order}), '[]') FROM {table} t"  # noqa: S608  # nosec B608
    return f"({query} WHERE t.workspace_id = :workspace_id)"


# One statement, so the export is a consistent snapshot. Numbers stay exact, because
# PostgreSQL writes NUMERIC values straight into the JSON text.
EXPORT_WORKSPACE = text(f"""
    SELECT jsonb_build_object(
        'format', 'costpilot-export-1',
        'exported_at', now(),
        'user', (SELECT to_jsonb(u) - 'keycloak_subject' FROM users u WHERE u.id = :user_id),
        'workspace', (SELECT to_jsonb(w) FROM workspaces w WHERE w.id = :workspace_id),
        'documents', {_rows("documents", " - 'storage_key'")},
        'document_periods', {_rows("document_periods", order="billing_month")},
        'cost_records', {_rows("cost_records", order="id")},
        'monthly_summaries', {_rows("monthly_summaries", order="billing_month")},
        'conversations', {_rows("conversations")},
        'messages', {_rows("messages")},
        'assistant_usage', {_rows("assistant_usage", order="day")},
        'audit_events', {_rows("audit_events")}
    )::text
""")  # noqa: S608  # nosec B608 - the table and column names are fixed in this file

OWNER_ROLE = "owner"
DEFAULT_WORKSPACE_NAME = "My workspace"


class PostgresIdentityRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def save_identity(self, identity: VerifiedIdentity) -> tuple[CurrentUser, bool]:
        async with self._database.transaction() as db:
            row = (
                await db.execute(
                    UPSERT_USER,
                    {
                        "subject": identity.subject,
                        "email": identity.email,
                        "display_name": identity.display_name,
                    },
                )
            ).one()
            user_id = row.id
            await set_context(db, user_id=user_id)
            membership = (await db.execute(FIND_WORKSPACE, {"user_id": user_id})).first()
            if membership is None:
                workspace_id, role = await self._create_workspace(db, user_id)
            else:
                workspace_id, role = membership.workspace_id, membership.role
            user = await self._load_user(
                db, user_id, identity.email, identity.display_name, workspace_id, role
            )
            return user, row.is_new

    async def create_session(
        self, token_hash: bytes, user: CurrentUser, sealed_id_token: str, expires_at: datetime
    ) -> None:
        async with self._database.transaction(user_id=user.user_id) as db:
            await db.execute(DELETE_EXPIRED_SESSIONS)
            await db.execute(
                INSERT_SESSION,
                {
                    "token_hash": token_hash,
                    "user_id": user.user_id,
                    "sealed_id_token": sealed_id_token,
                    "expires_at": expires_at,
                },
            )

    async def find_session(
        self, token_hash: bytes, now: datetime
    ) -> tuple[CurrentUser, str] | None:
        async with self._database.transaction() as db:
            row = (await db.execute(FIND_SESSION, {"token_hash": token_hash, "now": now})).first()
            if row is None:
                return None
            await set_context(db, user_id=row.id)
            membership = (await db.execute(FIND_WORKSPACE, {"user_id": row.id})).one()
            user = await self._load_user(
                db, row.id, row.email, row.display_name, membership.workspace_id, membership.role
            )
            return user, row.sealed_id_token

    async def delete_session(self, token_hash: bytes) -> None:
        async with self._database.transaction() as db:
            await db.execute(DELETE_SESSION, {"token_hash": token_hash})

    async def export_workspace(self, user: CurrentUser) -> str:
        async with self._database.transaction(
            user_id=user.user_id, workspace_id=user.workspace_id
        ) as db:
            params = {"user_id": user.user_id, "workspace_id": user.workspace_id}
            return (await db.execute(EXPORT_WORKSPACE, params)).scalar_one()

    async def find_subject(self, user: CurrentUser) -> str:
        async with self._database.transaction(user_id=user.user_id) as db:
            return (await db.execute(FIND_SUBJECT, {"user_id": user.user_id})).scalar_one()

    async def delete_account(self, user: CurrentUser) -> None:
        async with self._database.transaction(
            user_id=user.user_id, workspace_id=user.workspace_id
        ) as db:
            params = {"workspace_id": user.workspace_id, "user_id": user.user_id}
            counts = (await db.execute(COUNT_MEMBERS, params)).one()
            if counts.members == 1 and counts.mine == 1:
                # Deleting the workspace removes its bills, chats and audit events too.
                await db.execute(DELETE_WORKSPACE, params)
            await db.execute(DELETE_USER, {"user_id": user.user_id})

    async def _create_workspace(self, db: AsyncSession, user_id: UUID) -> tuple[UUID, str]:
        workspace_id = uuid4()
        await set_context(db, user_id=user_id, workspace_id=workspace_id)
        await db.execute(INSERT_WORKSPACE, {"id": workspace_id, "name": DEFAULT_WORKSPACE_NAME})
        await db.execute(
            INSERT_MEMBERSHIP,
            {"workspace_id": workspace_id, "user_id": user_id, "role": OWNER_ROLE},
        )
        return workspace_id, OWNER_ROLE

    async def _load_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        email: str,
        display_name: str,
        workspace_id: UUID,
        role: str,
    ) -> CurrentUser:
        await set_context(db, user_id=user_id, workspace_id=workspace_id)
        name = (await db.execute(FIND_WORKSPACE_NAME, {"workspace_id": workspace_id})).scalar_one()
        return CurrentUser(
            user_id=user_id,
            email=email,
            display_name=display_name,
            workspace_id=workspace_id,
            workspace_name=name,
            role=role,
        )
