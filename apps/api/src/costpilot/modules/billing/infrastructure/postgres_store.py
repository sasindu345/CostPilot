from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from costpilot.modules.billing.domain.records import CostRecord
from costpilot.shared.database import Database

DELETE_RECORDS = text("DELETE FROM cost_records WHERE document_id = :document_id")
DELETE_PERIODS = text("DELETE FROM document_periods WHERE document_id = :document_id")
INSERT_RECORD = text("""
    INSERT INTO cost_records (
        workspace_id, document_id, billing_month, provider_name, billing_account_id,
        sub_account_id, charge_period_start, charge_period_end, service_name, service_category,
        charge_category, billed_cost, effective_cost, list_cost, billing_currency, region_id,
        resource_id, sku_id, consumed_quantity, consumed_unit, tags, detail_level
    ) VALUES (
        :workspace_id, :document_id, :billing_month, :provider_name, :billing_account_id,
        :sub_account_id, :charge_period_start, :charge_period_end, :service_name,
        :service_category, :charge_category, :billed_cost, :effective_cost, :list_cost,
        :billing_currency, :region_id, :resource_id, :sku_id, :consumed_quantity,
        :consumed_unit, :tags, :detail_level
    )
""").bindparams(bindparam("tags", type_=JSONB))
INSERT_PERIODS = text("""
    INSERT INTO document_periods (
        workspace_id, document_id, provider_name, billing_account_id, billing_month, detail_level
    )
    SELECT DISTINCT workspace_id, document_id, provider_name, billing_account_id, billing_month,
        detail_level
    FROM cost_records WHERE document_id = :document_id
""")
# For each account and month, the most detailed file wins. If two are equal, the newest wins.
CHOOSE_ACTIVE_PERIODS = text("""
    WITH ranked AS (
        SELECT p.document_id, p.provider_name, p.billing_account_id, p.billing_month,
            row_number() OVER (
                PARTITION BY p.provider_name, p.billing_account_id, p.billing_month
                ORDER BY (p.detail_level = 'line_item') DESC, d.created_at DESC, d.id
            ) AS position
        FROM document_periods p
        JOIN documents d ON d.id = p.document_id
        WHERE d.status IN ('processed', 'replaced')
    )
    UPDATE document_periods p
    SET is_active = EXISTS (
        SELECT 1 FROM ranked r
        WHERE r.position = 1
            AND r.document_id = p.document_id
            AND r.provider_name = p.provider_name
            AND r.billing_account_id = p.billing_account_id
            AND r.billing_month = p.billing_month
    )
""")
# A summary file names no account, so any file for a known account replaces it for that month.
DROP_SUMMARY_FILES_COVERED_BY_DETAIL = text("""
    UPDATE document_periods summary
    SET is_active = false
    WHERE summary.billing_account_id = ''
        AND summary.is_active
        AND EXISTS (
            SELECT 1 FROM document_periods detail
            WHERE detail.is_active
                AND detail.billing_account_id <> ''
                AND detail.provider_name = summary.provider_name
                AND detail.billing_month = summary.billing_month
        )
""")
MARK_REPLACED = text("""
    UPDATE documents d SET status = 'replaced'
    WHERE d.status = 'processed'
        AND EXISTS (SELECT 1 FROM document_periods p WHERE p.document_id = d.id)
        AND NOT EXISTS (
            SELECT 1 FROM document_periods p WHERE p.document_id = d.id AND p.is_active
        )
""")
MARK_PROCESSED = text("""
    UPDATE documents d SET status = 'processed'
    WHERE d.status = 'replaced'
        AND EXISTS (SELECT 1 FROM document_periods p WHERE p.document_id = d.id AND p.is_active)
""")
DELETE_SUMMARIES = text("DELETE FROM monthly_summaries")
INSERT_SUMMARIES = text("""
    INSERT INTO monthly_summaries (
        workspace_id, billing_month, provider_name, billing_currency, service_name,
        service_category, charge_category, billed_cost, effective_cost
    )
    SELECT c.workspace_id, c.billing_month, c.provider_name, c.billing_currency, c.service_name,
        c.service_category, c.charge_category, sum(c.billed_cost), sum(c.effective_cost)
    FROM cost_records c
    JOIN document_periods p
        ON p.document_id = c.document_id
        AND p.provider_name = c.provider_name
        AND p.billing_account_id = c.billing_account_id
        AND p.billing_month = c.billing_month
    WHERE p.is_active
    GROUP BY c.workspace_id, c.billing_month, c.provider_name, c.billing_currency,
        c.service_name, c.service_category, c.charge_category
""")


class _PostgresRecordWriter:
    def __init__(self, db: AsyncSession, workspace_id: UUID, document_id: UUID) -> None:
        self._db = db
        self._workspace_id = workspace_id
        self._document_id = document_id

    async def add(self, records: Sequence[CostRecord]) -> None:
        await self._db.execute(INSERT_RECORD, [self._row(record) for record in records])

    def _row(self, record: CostRecord) -> dict[str, object]:
        return {
            "workspace_id": self._workspace_id,
            "document_id": self._document_id,
            "billing_month": record.charge_period_start.date().replace(day=1),
            "provider_name": record.provider_name,
            "billing_account_id": record.billing_account_id,
            "sub_account_id": record.sub_account_id,
            "charge_period_start": record.charge_period_start,
            "charge_period_end": record.charge_period_end,
            "service_name": record.service_name,
            "service_category": record.service_category,
            "charge_category": record.charge_category.value,
            "billed_cost": record.billed_cost,
            "effective_cost": record.effective_cost,
            "list_cost": record.list_cost,
            "billing_currency": record.billing_currency,
            "region_id": record.region_id,
            "resource_id": record.resource_id,
            "sku_id": record.sku_id,
            "consumed_quantity": record.consumed_quantity,
            "consumed_unit": record.consumed_unit,
            "tags": record.tags,
            "detail_level": record.detail_level.value,
        }


class PostgresBillingStore:
    def __init__(self, database: Database) -> None:
        self._database = database

    @asynccontextmanager
    async def replace_document(
        self, workspace_id: UUID, document_id: UUID
    ) -> AsyncIterator[_PostgresRecordWriter]:
        ids = {"document_id": document_id}
        async with self._database.transaction(workspace_id=workspace_id) as db:
            await db.execute(DELETE_PERIODS, ids)
            await db.execute(DELETE_RECORDS, ids)
            yield _PostgresRecordWriter(db, workspace_id, document_id)
            await db.execute(INSERT_PERIODS, ids)

    async def refresh(self, workspace_id: UUID) -> None:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            await db.execute(CHOOSE_ACTIVE_PERIODS)
            await db.execute(DROP_SUMMARY_FILES_COVERED_BY_DETAIL)
            await db.execute(MARK_REPLACED)
            await db.execute(MARK_PROCESSED)
            await db.execute(DELETE_SUMMARIES)
            await db.execute(INSERT_SUMMARIES)
