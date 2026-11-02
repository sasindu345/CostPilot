"""Proves PostgreSQL itself keeps workspaces apart. Needs the local database (`make up`)."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from costpilot.modules.audit.infrastructure.postgres_audit_log import PostgresAuditLog
from costpilot.modules.identity.domain.models import VerifiedIdentity
from costpilot.modules.identity.infrastructure.postgres_repository import (
    PostgresIdentityRepository,
)
from costpilot.shared.config import get_settings
from costpilot.shared.database import Database

COUNT_AUDIT = text("SELECT count(*) FROM audit_events")
COUNT_WORKSPACES = text("SELECT count(*) FROM workspaces")


@pytest.fixture
async def database():
    db = Database(get_settings().app_database_url)
    yield db
    await db.close()


@pytest.fixture
async def repository(database):
    return PostgresIdentityRepository(database)


def identity():
    subject = str(uuid4())
    return VerifiedIdentity(subject, f"{subject}@example.test", "Test user", "token")


@pytest.fixture
async def two_users(database, repository):
    audit_log = PostgresAuditLog(database)
    users = []
    for _ in range(2):
        user, _ = await repository.save_identity(identity())
        await audit_log.record(
            action="test.event",
            workspace_id=user.workspace_id,
            user_id=user.user_id,
            details={},
        )
        users.append(user)
    return users


async def test_first_login_creates_one_workspace(repository):
    details = identity()

    first, first_is_new = await repository.save_identity(details)
    second, second_is_new = await repository.save_identity(details)

    assert first_is_new is True
    assert second_is_new is False
    assert first.workspace_id == second.workspace_id
    assert first.role == "owner"


async def test_user_only_sees_their_own_audit_events(database, two_users):
    first, _ = two_users

    async with database.transaction(user_id=first.user_id, workspace_id=first.workspace_id) as db:
        assert (await db.execute(COUNT_AUDIT)).scalar_one() == 1
        assert (await db.execute(COUNT_WORKSPACES)).scalar_one() == 1


async def test_nothing_is_visible_without_a_workspace(database, two_users):
    async with database.transaction() as db:
        assert (await db.execute(COUNT_AUDIT)).scalar_one() == 0
        assert (await db.execute(COUNT_WORKSPACES)).scalar_one() == 0


async def test_user_cannot_write_into_another_workspace(database, two_users):
    first, second = two_users

    with pytest.raises(DBAPIError, match="row-level security"):
        async with database.transaction(
            user_id=first.user_id, workspace_id=first.workspace_id
        ) as db:
            await db.execute(
                text(
                    "INSERT INTO audit_events (workspace_id, user_id, action) "
                    "VALUES (:workspace_id, :user_id, 'attack')"
                ),
                {"workspace_id": second.workspace_id, "user_id": first.user_id},
            )


async def test_app_user_cannot_turn_off_row_level_security(database):
    with pytest.raises(DBAPIError):
        async with database.transaction() as db:
            await db.execute(text("ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY"))


async def test_audit_events_cannot_be_deleted(database, two_users):
    first, _ = two_users

    with pytest.raises(DBAPIError, match="permission denied"):
        async with database.transaction(
            user_id=first.user_id, workspace_id=first.workspace_id
        ) as db:
            await db.execute(text("DELETE FROM audit_events"))
