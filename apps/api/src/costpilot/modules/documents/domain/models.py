from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class DocumentStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    REPLACED = "replaced"


@dataclass(frozen=True)
class Document:
    id: UUID
    workspace_id: UUID
    uploaded_by: UUID
    file_name: str
    storage_key: str
    size_bytes: int
    sha256: str
    status: DocumentStatus
    created_at: datetime
    error_message: str | None = None
    row_count: int | None = None
    processed_at: datetime | None = None
    provider_name: str | None = None
    first_month: date | None = None
    last_month: date | None = None


@dataclass(frozen=True)
class Job:
    id: UUID
    document_id: UUID
    workspace_id: UUID
    attempts: int
