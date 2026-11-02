"""Tests saved chats, daily limits and privacy on real PostgreSQL. Needs `make up`."""

from datetime import date
from uuid import uuid4

import pytest

from costpilot.modules.assistant.domain.models import Role, SourceLink
from costpilot.modules.assistant.infrastructure.postgres_store import (
    PostgresConversationStore,
    PostgresUsageLimiter,
)
from costpilot.modules.identity.domain.models import VerifiedIdentity
from costpilot.modules.identity.infrastructure.postgres_repository import (
    PostgresIdentityRepository,
)
from costpilot.shared.config import get_settings
from costpilot.shared.database import Database

DAY = date(2026, 10, 1)


@pytest.fixture
async def database():
    db = Database(get_settings().app_database_url)
    yield db
    await db.close()


@pytest.fixture
def store(database):
    return PostgresConversationStore(database)


async def new_user(database):
    subject = str(uuid4())
    user, _ = await PostgresIdentityRepository(database).save_identity(
        VerifiedIdentity(subject, f"{subject}@example.test", "Test user", "token")
    )
    return user


async def test_a_conversation_keeps_its_messages_in_order(database, store):
    user = await new_user(database)
    chat = await store.create(user.workspace_id, user.user_id, "New")

    await store.add_message(user.workspace_id, chat.id, Role.USER, "Question")
    await store.add_message(
        user.workspace_id,
        chat.id,
        Role.ASSISTANT,
        "Answer",
        [SourceLink("Doc", "https://docs.test")],
    )

    messages = await store.messages(user.workspace_id, chat.id)
    assert [message.content for message in messages] == ["Question", "Answer"]
    assert messages[1].sources[0].title == "Doc"


async def test_history_limit_returns_the_newest_messages(database, store):
    user = await new_user(database)
    chat = await store.create(user.workspace_id, user.user_id, "New")
    for number in range(5):
        await store.add_message(user.workspace_id, chat.id, Role.USER, str(number))

    recent = await store.messages(user.workspace_id, chat.id, limit=2)

    assert [message.content for message in recent] == ["3", "4"]


async def test_the_title_comes_from_the_first_question_only(database, store):
    user = await new_user(database)
    chat = await store.create(user.workspace_id, user.user_id, "New")

    await store.set_title_if_new(user.workspace_id, chat.id, "First question")
    await store.add_message(user.workspace_id, chat.id, Role.ASSISTANT, "Answer")
    await store.set_title_if_new(user.workspace_id, chat.id, "Second question")

    chats = await store.list_for_user(user.workspace_id, user.user_id, 10)
    assert chats[0].title == "First question"


async def test_another_user_cannot_see_a_conversation(database, store):
    owner, stranger = await new_user(database), await new_user(database)
    chat = await store.create(owner.workspace_id, owner.user_id, "Private")
    await store.add_message(owner.workspace_id, chat.id, Role.USER, "Secret")

    assert not await store.exists(stranger.workspace_id, stranger.user_id, chat.id)
    assert await store.messages(stranger.workspace_id, chat.id) == []
    assert await store.list_for_user(stranger.workspace_id, owner.user_id, 10) == []


async def test_the_daily_limit_stops_at_the_exact_number(database):
    user = await new_user(database)
    limiter = PostgresUsageLimiter(database)

    results = [await limiter.try_consume(user.workspace_id, DAY, 2) for _ in range(3)]

    assert results == [True, True, False]


async def test_the_daily_limit_resets_the_next_day(database):
    user = await new_user(database)
    limiter = PostgresUsageLimiter(database)
    await limiter.try_consume(user.workspace_id, DAY, 1)

    assert await limiter.try_consume(user.workspace_id, date(2026, 10, 2), 1)
