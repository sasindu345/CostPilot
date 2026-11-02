"""Tests documents and the job queue against real PostgreSQL. Needs `make up`."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from costpilot.modules.documents.domain.errors import DuplicateDocumentError
from costpilot.modules.documents.domain.models import Document, DocumentStatus
from costpilot.modules.documents.infrastructure.postgres_repository import (
    PostgresDocumentRepository,
)
from costpilot.modules.identity.domain.models import VerifiedIdentity
from costpilot.modules.identity.infrastructure.postgres_repository import (
    PostgresIdentityRepository,
)
from costpilot.shared.config import get_settings
from costpilot.shared.database import Database


@pytest.fixture
async def database():
    db = Database(get_settings().app_database_url)
    async with db.transaction() as session:
        await session.execute(text("DELETE FROM jobs"))
    yield db
    await db.close()


@pytest.fixture
def repository(database):
    return PostgresDocumentRepository(database)


async def new_user(database):
    subject = str(uuid4())
    user, _ = await PostgresIdentityRepository(database).save_identity(
        VerifiedIdentity(subject, f"{subject}@example.test", "Test user", "token")
    )
    return user


def new_document(user, sha256=None):
    document_id = uuid4()
    return Document(
        id=document_id,
        workspace_id=user.workspace_id,
        uploaded_by=user.user_id,
        file_name="bill.csv",
        storage_key=f"{user.workspace_id}/{document_id}",
        size_bytes=10,
        sha256=sha256 or str(uuid4()),
        status=DocumentStatus.QUEUED,
        created_at=datetime.now(UTC),
    )


async def test_one_user_cannot_see_another_users_documents(database, repository):
    owner, stranger = await new_user(database), await new_user(database)
    document = new_document(owner)
    await repository.create_with_job(document)

    assert await repository.get(stranger.workspace_id, document.id) is None
    assert await repository.list_documents(stranger.workspace_id, 10) == []
    assert (await repository.get(owner.workspace_id, document.id)).file_name == "bill.csv"


async def test_one_user_cannot_delete_another_users_document(database, repository):
    owner, stranger = await new_user(database), await new_user(database)
    document = new_document(owner)
    await repository.create_with_job(document)

    await repository.delete(stranger.workspace_id, document.id)

    assert await repository.get(owner.workspace_id, document.id) is not None


async def test_same_file_twice_is_a_duplicate(database, repository):
    user = await new_user(database)
    first = new_document(user, sha256="same")
    await repository.create_with_job(first)

    with pytest.raises(DuplicateDocumentError) as caught:
        await repository.create_with_job(new_document(user, sha256="same"))

    assert caught.value.existing_id == first.id


async def test_two_users_can_upload_the_same_file(database, repository):
    first, second = await new_user(database), await new_user(database)

    await repository.create_with_job(new_document(first, sha256="same"))
    await repository.create_with_job(new_document(second, sha256="same"))


async def test_full_job_journey(database, repository):
    user = await new_user(database)
    document = new_document(user)
    await repository.create_with_job(document)

    job = await repository.claim_next_job()
    assert job.document_id == document.id
    assert job.attempts == 1
    assert await repository.claim_next_job() is None

    processing = await repository.mark_processing(job)
    assert processing.status is DocumentStatus.PROCESSING

    await repository.complete(job, row_count=7)
    done = await repository.get(user.workspace_id, document.id)
    assert done.status is DocumentStatus.PROCESSED
    assert done.row_count == 7
    assert done.processed_at is not None


async def test_two_workers_never_take_the_same_job(database, repository):
    user = await new_user(database)
    for _ in range(5):
        await repository.create_with_job(new_document(user))

    jobs = await asyncio.gather(*(repository.claim_next_job() for _ in range(5)))

    assert len({job.id for job in jobs}) == 5


async def test_a_job_waits_until_its_retry_time(database, repository):
    user = await new_user(database)
    await repository.create_with_job(new_document(user))
    job = await repository.claim_next_job()

    await repository.retry_later(job, timedelta(hours=1), "ConnectionError")

    assert await repository.claim_next_job() is None


async def test_a_job_from_a_crashed_worker_comes_back(database, repository):
    user = await new_user(database)
    await repository.create_with_job(new_document(user))
    await repository.claim_next_job()

    await repository.requeue_stale_jobs(timedelta(seconds=-1))

    job = await repository.claim_next_job()
    assert job.attempts == 2


async def test_failed_document_shows_the_reason_and_can_be_queued_again(database, repository):
    user = await new_user(database)
    document = new_document(user)
    await repository.create_with_job(document)
    job = await repository.claim_next_job()
    await repository.mark_processing(job)

    await repository.fail(job, "This file has no data rows.", "InvalidBillFileError")

    failed = await repository.get(user.workspace_id, document.id)
    assert failed.status is DocumentStatus.FAILED
    assert failed.error_message == "This file has no data rows."

    assert await repository.queue_again(user.workspace_id, document.id) is True
    queued = await repository.get(user.workspace_id, document.id)
    assert queued.status is DocumentStatus.QUEUED
    assert queued.error_message is None


async def test_a_waiting_document_cannot_be_queued_twice(database, repository):
    user = await new_user(database)
    document = new_document(user)
    await repository.create_with_job(document)

    assert await repository.queue_again(user.workspace_id, document.id) is False


async def test_deleting_a_document_removes_its_job(database, repository):
    user = await new_user(database)
    document = new_document(user)
    await repository.create_with_job(document)

    await repository.delete(user.workspace_id, document.id)

    assert await repository.claim_next_job() is None
