"""Takes one job from the queue and does the work.

`process` knows nothing about the queue, so it could run somewhere else later, such as in Lambda.
"""

import asyncio
import tempfile
from datetime import timedelta
from pathlib import Path

import structlog

from costpilot.modules.documents.application.ports import FileStorage, JobQueue
from costpilot.modules.documents.domain.errors import InvalidBillFileError
from costpilot.modules.documents.domain.files import count_bill_rows
from costpilot.modules.documents.domain.models import Document, Job

logger = structlog.get_logger()

GENERAL_FAILURE = "We could not process this file. Please try again."


class JobRunner:
    def __init__(
        self,
        repository: JobQueue,
        storage: FileStorage,
        max_unpacked_bytes: int,
        max_attempts: int,
        retry_delay: timedelta,
        stale_after: timedelta,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._max_unpacked_bytes = max_unpacked_bytes
        self._max_attempts = max_attempts
        self._retry_delay = retry_delay
        self._stale_after = stale_after

    async def run_once(self) -> bool:
        """Return True if a job was handled."""
        await self._repository.requeue_stale_jobs(self._stale_after)
        job = await self._repository.claim_next_job()
        if job is None:
            return False

        document = await self._repository.mark_processing(job)
        if document is None:
            return True

        try:
            row_count = await self.process(document)
        except InvalidBillFileError as error:
            await self._repository.fail(job, str(error), type(error).__name__)
        except Exception as error:
            logger.exception("job_failed", job_id=str(job.id), attempts=job.attempts)
            await self._retry_or_fail(job, type(error).__name__)
        else:
            await self._repository.complete(job, row_count)
        return True

    async def process(self, document: Document) -> int:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bill"
            await self._storage.fetch(document.storage_key, path)
            return await asyncio.to_thread(count_bill_rows, path, self._max_unpacked_bytes)

    async def _retry_or_fail(self, job: Job, reason: str) -> None:
        if job.attempts >= self._max_attempts:
            await self._repository.fail(job, GENERAL_FAILURE, reason)
        else:
            await self._repository.retry_later(job, self._retry_delay * job.attempts, reason)
