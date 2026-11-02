from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from costpilot.modules.documents.application.job_runner import GENERAL_FAILURE, JobRunner
from costpilot.modules.documents.domain.models import Document, DocumentStatus, Job

GOOD_FILE = b"Service,Cost\nEC2,1.00\n"


def document():
    return Document(
        id=uuid4(),
        workspace_id=uuid4(),
        uploaded_by=uuid4(),
        file_name="bill.csv",
        storage_key="key",
        size_bytes=1,
        sha256="hash",
        status=DocumentStatus.QUEUED,
        created_at=datetime.now(UTC),
    )


class FakeQueue:
    def __init__(self, attempts=1, deleted=False):
        self.job = Job(uuid4(), uuid4(), uuid4(), attempts)
        self.deleted = deleted
        self.outcome = None

    async def requeue_stale_jobs(self, stale_after):
        pass

    async def claim_next_job(self):
        job, self.job = self.job, None
        return job

    async def mark_processing(self, job):
        return None if self.deleted else document()

    async def complete(self, job, row_count):
        self.outcome = ("complete", row_count)

    async def retry_later(self, job, delay, reason):
        self.outcome = ("retry", delay)

    async def fail(self, job, message, reason):
        self.outcome = ("fail", message)


class FakeStorage:
    def __init__(self, content=GOOD_FILE, error=None):
        self.content = content
        self.error = error

    async def put(self, key: str, source: Path) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def fetch(self, key: str, destination: Path) -> None:
        if self.error:
            raise self.error
        destination.write_bytes(self.content)


def runner(queue, storage):
    return JobRunner(
        repository=queue,
        storage=storage,
        max_unpacked_bytes=1_000_000,
        max_attempts=3,
        retry_delay=timedelta(seconds=30),
        stale_after=timedelta(minutes=15),
    )


async def test_a_good_file_completes():
    queue = FakeQueue()

    assert await runner(queue, FakeStorage()).run_once() is True
    assert queue.outcome == ("complete", 1)


async def test_nothing_to_do():
    queue = FakeQueue()
    queue.job = None

    assert await runner(queue, FakeStorage()).run_once() is False


async def test_a_bad_file_fails_at_once_with_a_clear_reason():
    queue = FakeQueue()

    await runner(queue, FakeStorage(content=b"")).run_once()

    assert queue.outcome == ("fail", "This file has no column headings.")


async def test_a_temporary_problem_is_retried_with_a_longer_wait():
    queue = FakeQueue(attempts=2)

    await runner(queue, FakeStorage(error=ConnectionError("secret detail"))).run_once()

    assert queue.outcome == ("retry", timedelta(seconds=60))


async def test_it_gives_up_after_the_last_attempt_without_showing_internal_details():
    queue = FakeQueue(attempts=3)

    await runner(queue, FakeStorage(error=ConnectionError("secret detail"))).run_once()

    assert queue.outcome == ("fail", GENERAL_FAILURE)


async def test_a_document_deleted_while_waiting_is_skipped():
    queue = FakeQueue(deleted=True)

    assert await runner(queue, FakeStorage()).run_once() is True
    assert queue.outcome is None


@pytest.mark.parametrize("attempts", [1, 2])
async def test_retry_wait_grows_with_each_attempt(attempts):
    queue = FakeQueue(attempts=attempts)

    await runner(queue, FakeStorage(error=OSError())).run_once()

    assert queue.outcome == ("retry", timedelta(seconds=30 * attempts))
