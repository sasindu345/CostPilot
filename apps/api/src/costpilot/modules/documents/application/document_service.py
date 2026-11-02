"""The steps of uploading and managing documents."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import structlog

from costpilot.modules.audit.contracts import AuditLog
from costpilot.modules.documents.application.ports import DocumentRepository, FileStorage
from costpilot.modules.documents.domain.errors import (
    DocumentBusyError,
    DocumentNotFoundError,
    DuplicateDocumentError,
)
from costpilot.modules.documents.domain.files import check_file_matches_name, safe_file_name
from costpilot.modules.documents.domain.models import Document, DocumentStatus
from costpilot.modules.identity.contracts import CurrentUser

logger = structlog.get_logger()


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        storage: FileStorage,
        audit_log: AuditLog,
        list_limit: int,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._audit_log = audit_log
        self._list_limit = list_limit

    async def upload(
        self,
        user: CurrentUser,
        raw_name: str,
        temporary_file: Path,
        first_bytes: bytes,
        size_bytes: int,
        sha256: str,
    ) -> Document:
        file_name = safe_file_name(raw_name)
        check_file_matches_name(file_name, first_bytes)

        existing = await self._repository.find_by_hash(user.workspace_id, sha256)
        if existing is not None:
            raise DuplicateDocumentError(existing.id)

        document_id = uuid4()
        document = Document(
            id=document_id,
            workspace_id=user.workspace_id,
            uploaded_by=user.user_id,
            file_name=file_name,
            storage_key=f"{user.workspace_id}/{document_id}",
            size_bytes=size_bytes,
            sha256=sha256,
            status=DocumentStatus.QUEUED,
            created_at=datetime.now(UTC),
        )
        await self._storage.put(document.storage_key, temporary_file)
        try:
            await self._repository.create_with_job(document)
        except BaseException:
            await self._storage.delete(document.storage_key)
            raise
        await self._record(user, "document.uploaded", document)
        return document

    async def list_documents(self, user: CurrentUser) -> list[Document]:
        return await self._repository.list_documents(user.workspace_id, self._list_limit)

    async def get(self, user: CurrentUser, document_id: UUID) -> Document:
        document = await self._repository.get(user.workspace_id, document_id)
        if document is None:
            raise DocumentNotFoundError
        return document

    async def delete(self, user: CurrentUser, document_id: UUID) -> None:
        document = await self.get(user, document_id)
        await self._repository.delete(user.workspace_id, document_id)
        await self._record(user, "document.deleted", document)
        try:
            await self._storage.delete(document.storage_key)
        except OSError:
            logger.exception("stored_file_not_deleted", document_id=str(document_id))

    async def reprocess(self, user: CurrentUser, document_id: UUID) -> Document:
        document = await self.get(user, document_id)
        if not await self._repository.queue_again(user.workspace_id, document_id):
            raise DocumentBusyError
        await self._record(user, "document.reprocessed", document)
        return await self.get(user, document_id)

    async def _record(self, user: CurrentUser, action: str, document: Document) -> None:
        await self._audit_log.record(
            action=action,
            workspace_id=user.workspace_id,
            user_id=user.user_id,
            details={"document_id": str(document.id), "file_name": document.file_name},
        )
