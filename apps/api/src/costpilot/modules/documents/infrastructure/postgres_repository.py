from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Row, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from costpilot.modules.billing.contracts import ImportResult
from costpilot.modules.documents.domain.errors import DuplicateDocumentError
from costpilot.modules.documents.domain.models import Document, DocumentStatus, Job
from costpilot.shared.database import Database

FIND_BY_HASH = text("SELECT * FROM documents WHERE sha256 = :sha256")
FIND_BY_ID = text("SELECT * FROM documents WHERE id = :id")
LIST_DOCUMENTS = text("SELECT * FROM documents ORDER BY created_at DESC LIMIT :limit")
INSERT_DOCUMENT = text(
    "INSERT INTO documents (id, workspace_id, uploaded_by, file_name, storage_key, size_bytes, "
    "sha256, status, created_at) VALUES (:id, :workspace_id, :uploaded_by, :file_name, "
    ":storage_key, :size_bytes, :sha256, :status, :created_at)"
)
INSERT_JOB = text(
    "INSERT INTO jobs (id, document_id, workspace_id) VALUES (:id, :document_id, :workspace_id)"
)
LIST_STORAGE_KEYS = text("SELECT storage_key FROM documents")
DELETE_DOCUMENT = text("DELETE FROM documents WHERE id = :id")
QUEUE_AGAIN = text(
    "UPDATE documents SET status = 'queued', error_message = NULL, row_count = NULL, "
    "processed_at = NULL WHERE id = :id AND status IN ('processed', 'failed', 'replaced') "
    "RETURNING id"
)
REQUEUE_STALE = text(
    "UPDATE jobs SET status = 'queued', locked_at = NULL "
    "WHERE status = 'running' AND locked_at < :cutoff"
)
CLAIM_JOB = text(
    "UPDATE jobs SET status = 'running', locked_at = now(), attempts = attempts + 1 "
    "WHERE id = (SELECT id FROM jobs WHERE status = 'queued' AND run_after <= now() "
    "ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) "
    "RETURNING id, document_id, workspace_id, attempts"
)
SET_PROCESSING = text("UPDATE documents SET status = 'processing' WHERE id = :id RETURNING *")
SET_PROCESSED = text(
    "UPDATE documents SET status = 'processed', row_count = :row_count, "
    "provider_name = :provider_name, first_month = :first_month, last_month = :last_month, "
    "processed_at = now() WHERE id = :id"
)
SET_FAILED = text("UPDATE documents SET status = 'failed', error_message = :message WHERE id = :id")
DELETE_JOB = text("DELETE FROM jobs WHERE id = :id")
RETRY_JOB = text(
    "UPDATE jobs SET status = 'queued', locked_at = NULL, run_after = :run_after, "
    "last_error = :reason WHERE id = :id"
)
FAIL_JOB = text("UPDATE jobs SET status = 'failed', last_error = :reason WHERE id = :id")


def _to_document(row: Row) -> Document:
    return Document(
        id=row.id,
        workspace_id=row.workspace_id,
        uploaded_by=row.uploaded_by,
        file_name=row.file_name,
        storage_key=row.storage_key,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        status=DocumentStatus(row.status),
        created_at=row.created_at,
        error_message=row.error_message,
        row_count=row.row_count,
        processed_at=row.processed_at,
        provider_name=row.provider_name,
        first_month=row.first_month,
        last_month=row.last_month,
    )


async def _add_job(db: AsyncSession, document_id: UUID, workspace_id: UUID) -> None:
    await db.execute(
        INSERT_JOB,
        {"id": uuid4(), "document_id": document_id, "workspace_id": workspace_id},
    )


class PostgresDocumentRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def find_by_hash(self, workspace_id: UUID, sha256: str) -> Document | None:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            row = (await db.execute(FIND_BY_HASH, {"sha256": sha256})).first()
            return _to_document(row) if row else None

    async def create_with_job(self, document: Document) -> None:
        try:
            async with self._database.transaction(workspace_id=document.workspace_id) as db:
                await db.execute(
                    INSERT_DOCUMENT,
                    {
                        "id": document.id,
                        "workspace_id": document.workspace_id,
                        "uploaded_by": document.uploaded_by,
                        "file_name": document.file_name,
                        "storage_key": document.storage_key,
                        "size_bytes": document.size_bytes,
                        "sha256": document.sha256,
                        "status": document.status.value,
                        "created_at": document.created_at,
                    },
                )
                await _add_job(db, document.id, document.workspace_id)
        except IntegrityError as error:
            existing = await self.find_by_hash(document.workspace_id, document.sha256)
            if existing is None:
                raise
            raise DuplicateDocumentError(existing.id) from error

    async def list_documents(self, workspace_id: UUID, limit: int) -> list[Document]:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            rows = (await db.execute(LIST_DOCUMENTS, {"limit": limit})).all()
            return [_to_document(row) for row in rows]

    async def list_storage_keys(self, workspace_id: UUID) -> list[str]:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            return list((await db.execute(LIST_STORAGE_KEYS)).scalars())

    async def get(self, workspace_id: UUID, document_id: UUID) -> Document | None:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            row = (await db.execute(FIND_BY_ID, {"id": document_id})).first()
            return _to_document(row) if row else None

    async def delete(self, workspace_id: UUID, document_id: UUID) -> None:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            await db.execute(DELETE_DOCUMENT, {"id": document_id})

    async def queue_again(self, workspace_id: UUID, document_id: UUID) -> bool:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            updated = (await db.execute(QUEUE_AGAIN, {"id": document_id})).first()
            if updated is None:
                return False
            await _add_job(db, document_id, workspace_id)
            return True

    async def requeue_stale_jobs(self, stale_after: timedelta) -> None:
        async with self._database.transaction() as db:
            await db.execute(REQUEUE_STALE, {"cutoff": datetime.now(UTC) - stale_after})

    async def claim_next_job(self) -> Job | None:
        async with self._database.transaction() as db:
            row = (await db.execute(CLAIM_JOB)).first()
            if row is None:
                return None
            return Job(row.id, row.document_id, row.workspace_id, row.attempts)

    async def mark_processing(self, job: Job) -> Document | None:
        async with self._database.transaction(workspace_id=job.workspace_id) as db:
            row = (await db.execute(SET_PROCESSING, {"id": job.document_id})).first()
            return _to_document(row) if row else None

    async def mark_processed(self, job: Job, result: ImportResult) -> None:
        async with self._database.transaction(workspace_id=job.workspace_id) as db:
            await db.execute(
                SET_PROCESSED,
                {
                    "id": job.document_id,
                    "row_count": result.record_count,
                    "provider_name": result.provider_name,
                    "first_month": result.first_month,
                    "last_month": result.last_month,
                },
            )

    async def finish(self, job: Job) -> None:
        async with self._database.transaction(workspace_id=job.workspace_id) as db:
            await db.execute(DELETE_JOB, {"id": job.id})

    async def retry_later(self, job: Job, delay: timedelta, reason: str) -> None:
        async with self._database.transaction(workspace_id=job.workspace_id) as db:
            await db.execute(
                RETRY_JOB,
                {"id": job.id, "run_after": datetime.now(UTC) + delay, "reason": reason},
            )

    async def fail(self, job: Job, message: str, reason: str) -> None:
        async with self._database.transaction(workspace_id=job.workspace_id) as db:
            await db.execute(SET_FAILED, {"id": job.document_id, "message": message})
            await db.execute(FAIL_JOB, {"id": job.id, "reason": reason})
