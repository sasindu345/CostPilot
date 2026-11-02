import hashlib
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, UploadFile, status
from pydantic import BaseModel

from costpilot.modules.documents.application.document_service import DocumentService
from costpilot.modules.documents.domain.errors import FileTooLargeError
from costpilot.modules.documents.domain.models import Document, DocumentStatus
from costpilot.modules.identity.contracts import AppSettings, SignedInUser

router = APIRouter(prefix="/documents", tags=["documents"])

READ_CHUNK_BYTES = 1024 * 1024
SNIFF_BYTES = 8
MEGABYTE = 1024 * 1024


def get_documents(request: Request) -> DocumentService:
    return request.app.state.documents


Documents = Annotated[DocumentService, Depends(get_documents)]


class DocumentResponse(BaseModel):
    id: UUID
    file_name: str
    size_bytes: int
    status: DocumentStatus
    created_at: datetime
    error_message: str | None
    row_count: int | None
    processed_at: datetime | None
    provider_name: str | None
    first_month: date | None
    last_month: date | None

    @classmethod
    def of(cls, document: Document) -> "DocumentResponse":
        return cls(
            id=document.id,
            file_name=document.file_name,
            size_bytes=document.size_bytes,
            status=document.status,
            created_at=document.created_at,
            error_message=document.error_message,
            row_count=document.row_count,
            processed_at=document.processed_at,
            provider_name=document.provider_name,
            first_month=document.first_month,
            last_month=document.last_month,
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile, user: SignedInUser, documents: Documents, settings: AppSettings
) -> DocumentResponse:
    max_bytes = settings.max_upload_mb * MEGABYTE
    digest = hashlib.sha256()
    size_bytes = 0
    first_bytes = b""
    with tempfile.TemporaryDirectory() as folder:
        temporary_file = Path(folder) / "upload"
        with temporary_file.open("wb") as output:
            while chunk := await file.read(READ_CHUNK_BYTES):
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise FileTooLargeError
                first_bytes = first_bytes or chunk[:SNIFF_BYTES]
                digest.update(chunk)
                output.write(chunk)
        document = await documents.upload(
            user, file.filename or "", temporary_file, first_bytes, size_bytes, digest.hexdigest()
        )
    return DocumentResponse.of(document)


@router.get("")
async def list_documents(user: SignedInUser, documents: Documents) -> list[DocumentResponse]:
    return [DocumentResponse.of(document) for document in await documents.list_documents(user)]


@router.get("/{document_id}")
async def get_document(
    document_id: UUID, user: SignedInUser, documents: Documents
) -> DocumentResponse:
    return DocumentResponse.of(await documents.get(user, document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID, user: SignedInUser, documents: Documents) -> Response:
    await documents.delete(user, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(
    document_id: UUID, user: SignedInUser, documents: Documents
) -> DocumentResponse:
    return DocumentResponse.of(await documents.reprocess(user, document_id))
