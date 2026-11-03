"""Tests data export, account deletion and retention on real PostgreSQL. Needs `make up`."""

import json
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from costpilot.modules.audit.domain.retention import RetentionPolicy
from costpilot.modules.audit.infrastructure.postgres_retention import PostgresRetentionStore
from costpilot.modules.billing.application.import_service import BillImportService
from costpilot.modules.billing.infrastructure.postgres_store import PostgresBillingStore
from costpilot.modules.documents.infrastructure.postgres_repository import (
    PostgresDocumentRepository,
)
from costpilot.modules.identity.infrastructure.postgres_repository import (
    PostgresIdentityRepository,
)
from costpilot.shared.config import get_settings
from costpilot.shared.database import Database
from tests.integration.test_billing import CUR_COLUMNS, add_document, cur_row, new_workspace

WORKSPACE_TABLES = (
    "documents",
    "cost_records",
    "document_periods",
    "monthly_summaries",
    "audit_events",
    "conversations",
)


@pytest.fixture
async def database():
    db = Database(get_settings().app_database_url)
    yield db
    await db.close()


@pytest.fixture
def identity(database):
    return PostgresIdentityRepository(database)


async def user_with_a_bill(database, cost="1.0000000001"):
    user = await new_workspace(database)
    document = await add_document(PostgresDocumentRepository(database), user)
    importer = BillImportService(store=PostgresBillingStore(database), batch_size=10)
    await importer.import_bill(
        user.workspace_id, document.id, CUR_COLUMNS, iter([cur_row("2026-10", cost)])
    )
    await importer.refresh(user.workspace_id)
    return user, document


async def count_rows(database, user, table):
    async with database.transaction(user_id=user.user_id, workspace_id=user.workspace_id) as db:
        return (await db.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()  # noqa: S608


async def test_export_holds_only_the_users_own_data_with_exact_money(database, identity):
    owner, owner_document = await user_with_a_bill(database)
    _, stranger_document = await user_with_a_bill(database, cost="999")

    exported = await identity.export_workspace(owner)
    data = json.loads(exported, parse_float=Decimal)

    assert data["user"]["email"] == owner.email
    assert "keycloak_subject" not in data["user"]
    assert [d["id"] for d in data["documents"]] == [str(owner_document.id)]
    assert "storage_key" not in data["documents"][0]
    assert [r["billed_cost"] for r in data["cost_records"]] == [Decimal("1.0000000001")]
    assert str(stranger_document.id) not in exported


async def test_deleting_an_account_removes_all_its_data(database, identity):
    owner, _ = await user_with_a_bill(database)
    stranger, _ = await user_with_a_bill(database)

    await identity.delete_account(owner)

    for table in WORKSPACE_TABLES:
        assert await count_rows(database, owner, table) == 0, table
    async with database.transaction() as db:
        users = text("SELECT count(*) FROM users WHERE id = :id")
        assert (await db.execute(users, {"id": owner.user_id})).scalar_one() == 0
    assert await count_rows(database, stranger, "cost_records") == 1


async def test_a_workspace_the_user_does_not_belong_to_is_never_deleted(database, identity):
    owner = await new_workspace(database)
    stranger, _ = await user_with_a_bill(database)
    forged = owner.__class__(**{**owner.__dict__, "workspace_id": stranger.workspace_id})

    await identity.delete_account(forged)

    assert await count_rows(database, stranger, "cost_records") == 1


async def test_retention_removes_only_records_past_their_limit(database):
    user = await new_workspace(database)
    old_event, new_event = uuid4(), uuid4()
    old_chat, active_chat = uuid4(), uuid4()
    async with database.transaction(user_id=user.user_id, workspace_id=user.workspace_id) as db:
        ids = {"ws": user.workspace_id, "user": user.user_id}
        for event_id, age in ((old_event, 400), (new_event, 10)):
            await db.execute(
                text(
                    "INSERT INTO audit_events (id, workspace_id, user_id, action, created_at) "
                    "VALUES (:id, :ws, :user, 'test', now() - make_interval(days => :age))"
                ),
                {**ids, "id": event_id, "age": age},
            )
        for chat_id, message_age in ((old_chat, 200), (active_chat, 1)):
            await db.execute(
                text(
                    "INSERT INTO conversations (id, workspace_id, user_id, title, created_at) "
                    "VALUES (:id, :ws, :user, 'chat', now() - interval '300 days')"
                ),
                {**ids, "id": chat_id},
            )
            await db.execute(
                text(
                    "INSERT INTO messages (id, conversation_id, workspace_id, role, content, "
                    "created_at) VALUES (:id, :chat, :ws, 'user', 'hi', "
                    "now() - make_interval(days => :age))"
                ),
                {**ids, "id": uuid4(), "chat": chat_id, "age": message_age},
            )

    result = await PostgresRetentionStore(database).apply(
        RetentionPolicy(audit_days=365, conversation_days=180, failed_job_days=30)
    )

    async with database.transaction(user_id=user.user_id, workspace_id=user.workspace_id) as db:
        events = set((await db.execute(text("SELECT id FROM audit_events"))).scalars())
        chats = set((await db.execute(text("SELECT id FROM conversations"))).scalars())
    assert old_event not in events
    assert new_event in events
    assert chats == {active_chat}
    assert result.audit_events >= 1
    assert result.conversations >= 1


def test_retention_refuses_a_limit_below_one_day():
    with pytest.raises(ValueError, match="at least 1"):
        RetentionPolicy(audit_days=0, conversation_days=180, failed_job_days=30)
