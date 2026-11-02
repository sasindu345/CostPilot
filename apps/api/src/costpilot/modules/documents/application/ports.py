"""What the document use cases need from the outside world."""

from datetime import timedelta
from pathlib import Path
from typing import Protocol
from uuid import UUID

from costpilot.modules.billing.contracts import ImportResult
from costpilot.modules.documents.domain.models import Document, Job


class FileStorage(Protocol):
    async def put(self, key: str, source: Path) -> None: ...

    async def fetch(self, key: str, destination: Path) -> None: ...

    async def delete(self, key: str) -> None: ...


class DocumentRepository(Protocol):
    async def find_by_hash(self, workspace_id: UUID, sha256: str) -> Document | None: ...

    async def create_with_job(self, document: Document) -> None:
        """Save the document and its job together. Raises DuplicateDocumentError."""

    async def list_documents(self, workspace_id: UUID, limit: int) -> list[Document]: ...

    async def get(self, workspace_id: UUID, document_id: UUID) -> Document | None: ...

    async def delete(self, workspace_id: UUID, document_id: UUID) -> None: ...

    async def queue_again(self, workspace_id: UUID, document_id: UUID) -> bool:
        """Return False if the document is still waiting or being processed."""


class JobQueue(Protocol):
    async def requeue_stale_jobs(self, stale_after: timedelta) -> None:
        """Put back jobs left running by a worker that crashed."""

    async def claim_next_job(self) -> Job | None: ...

    async def mark_processing(self, job: Job) -> Document | None:
        """Return None if the document was deleted while it waited."""

    async def mark_processed(self, job: Job, result: ImportResult) -> None: ...

    async def finish(self, job: Job) -> None:
        """Remove a job whose work is fully done."""

    async def retry_later(self, job: Job, delay: timedelta, reason: str) -> None: ...

    async def fail(self, job: Job, message: str, reason: str) -> None: ...
