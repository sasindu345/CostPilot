"""Public interface of the billing module. Other modules may only import from here."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from costpilot.modules.billing.domain.errors import BillRejectedError

__all__ = ["BillImporter", "BillRejectedError", "ImportResult"]


@dataclass(frozen=True)
class ImportResult:
    record_count: int
    provider_name: str
    first_month: date
    last_month: date


class BillImporter(Protocol):
    async def import_bill(
        self,
        workspace_id: UUID,
        document_id: UUID,
        columns: list[str],
        rows: Iterator[list[str]],
    ) -> ImportResult:
        """Save a bill's records, replacing any earlier import of the same document."""

    async def refresh(self, workspace_id: UUID) -> None:
        """Decide which file counts for each month, then rebuild the monthly summaries."""
