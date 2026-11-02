from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from typing import Protocol
from uuid import UUID

from costpilot.modules.billing.domain.records import CostRecord


class RecordWriter(Protocol):
    async def add(self, records: Sequence[CostRecord]) -> None: ...


class BillingStore(Protocol):
    def replace_document(
        self, workspace_id: UUID, document_id: UUID
    ) -> AbstractAsyncContextManager[RecordWriter]:
        """Everything written inside is saved together, or not at all."""

    async def refresh(self, workspace_id: UUID) -> None: ...
