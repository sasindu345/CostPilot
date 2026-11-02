from uuid import UUID

from costpilot.shared.exceptions import AppError


class UnsupportedFileError(AppError):
    status_code = 415
    code = "unsupported_file"

    def __init__(self) -> None:
        super().__init__("Please upload a .csv or .csv.gz file.")


class FileTooLargeError(AppError):
    status_code = 413
    code = "file_too_large"

    def __init__(self) -> None:
        super().__init__("That file is too large.")


class DuplicateDocumentError(AppError):
    status_code = 409
    code = "duplicate_document"

    def __init__(self, existing_id: UUID) -> None:
        super().__init__("You have already uploaded this file.")
        self.existing_id = existing_id


class DocumentNotFoundError(AppError):
    status_code = 404
    code = "document_not_found"

    def __init__(self) -> None:
        super().__init__("We could not find that document.")


class DocumentBusyError(AppError):
    status_code = 409
    code = "document_busy"

    def __init__(self) -> None:
        super().__init__("This document is still being processed.")


class InvalidBillFileError(Exception):
    """The file can never be processed, so retrying will not help. The message is shown to users."""
