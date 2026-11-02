"""The steps of turning a bill's rows into saved FOCUS records."""

import asyncio
from collections.abc import Iterator
from datetime import date
from itertools import islice
from uuid import UUID

from costpilot.modules.billing.application.ports import BillingStore
from costpilot.modules.billing.contracts import ImportResult
from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.readers import find_reader
from costpilot.modules.billing.domain.records import CostRecord

MULTIPLE_PROVIDERS = "multiple"


class BillImportService:
    def __init__(self, store: BillingStore, batch_size: int) -> None:
        self._store = store
        self._batch_size = batch_size

    async def import_bill(
        self,
        workspace_id: UUID,
        document_id: UUID,
        columns: list[str],
        rows: Iterator[list[str]],
    ) -> ImportResult:
        records = find_reader(columns).read(columns, rows)
        count = 0
        providers: set[str] = set()
        months: set[date] = set()
        async with self._store.replace_document(workspace_id, document_id) as writer:
            while batch := await asyncio.to_thread(self._next_batch, records):
                await writer.add(batch)
                count += len(batch)
                providers.update(record.provider_name for record in batch)
                months.update(record.charge_period_start.date().replace(day=1) for record in batch)
            if count == 0:
                raise BillRejectedError("This file has no costs in it.")
        return ImportResult(
            record_count=count,
            provider_name=providers.pop() if len(providers) == 1 else MULTIPLE_PROVIDERS,
            first_month=min(months),
            last_month=max(months),
        )

    async def refresh(self, workspace_id: UUID) -> None:
        await self._store.refresh(workspace_id)

    def _next_batch(self, records: Iterator[CostRecord]) -> list[CostRecord]:
        return list(islice(records, self._batch_size))
