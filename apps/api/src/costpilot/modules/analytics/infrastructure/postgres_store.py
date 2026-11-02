from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from costpilot.modules.analytics.domain.models import CostType, ServiceMonthCost
from costpilot.shared.database import Database

BILLED_COSTS = text("""
    SELECT billing_month, service_name, billing_currency, sum(billed_cost) AS cost
    FROM monthly_summaries
    WHERE (CAST(:provider AS text) IS NULL OR provider_name = :provider)
    GROUP BY 1, 2, 3
""")
EFFECTIVE_COSTS = text("""
    SELECT billing_month, service_name, billing_currency, sum(effective_cost) AS cost
    FROM monthly_summaries
    WHERE (CAST(:provider AS text) IS NULL OR provider_name = :provider)
    GROUP BY 1, 2, 3
""")
PROVIDERS = text("SELECT DISTINCT provider_name FROM monthly_summaries ORDER BY 1")
LAST_USAGE_DAY = text("""
    SELECT max(c.charge_period_end) - interval '1 second' AS last_moment
    FROM cost_records c
    JOIN document_periods p
        ON p.document_id = c.document_id
        AND p.provider_name = c.provider_name
        AND p.billing_account_id = c.billing_account_id
        AND p.billing_month = c.billing_month
    WHERE p.is_active AND c.billing_month = :month AND c.detail_level = 'line_item'
""")
BILLED_THROUGH_DAY = text("""
    SELECT coalesce(sum(c.billed_cost), 0) AS cost
    FROM cost_records c
    JOIN document_periods p
        ON p.document_id = c.document_id
        AND p.provider_name = c.provider_name
        AND p.billing_account_id = c.billing_account_id
        AND p.billing_month = c.billing_month
    WHERE p.is_active AND c.billing_month = :month AND c.billing_currency = :currency
        AND extract(day FROM c.charge_period_start AT TIME ZONE 'UTC') <= :day
        AND (CAST(:provider AS text) IS NULL OR c.provider_name = :provider)
""")
EFFECTIVE_THROUGH_DAY = text("""
    SELECT coalesce(sum(c.effective_cost), 0) AS cost
    FROM cost_records c
    JOIN document_periods p
        ON p.document_id = c.document_id
        AND p.provider_name = c.provider_name
        AND p.billing_account_id = c.billing_account_id
        AND p.billing_month = c.billing_month
    WHERE p.is_active AND c.billing_month = :month AND c.billing_currency = :currency
        AND extract(day FROM c.charge_period_start AT TIME ZONE 'UTC') <= :day
        AND (CAST(:provider AS text) IS NULL OR c.provider_name = :provider)
""")


class PostgresAnalyticsStore:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def service_month_costs(
        self, workspace_id: UUID, cost_type: CostType, provider: str | None
    ) -> list[ServiceMonthCost]:
        query = BILLED_COSTS if cost_type is CostType.BILLED else EFFECTIVE_COSTS
        async with self._database.transaction(workspace_id=workspace_id) as db:
            rows = await db.execute(query, {"provider": provider})
            return [
                ServiceMonthCost(
                    row.billing_month, row.service_name, row.billing_currency, row.cost
                )
                for row in rows
            ]

    async def providers(self, workspace_id: UUID) -> list[str]:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            return list((await db.execute(PROVIDERS)).scalars())

    async def last_usage_day(self, workspace_id: UUID, month: date) -> date | None:
        async with self._database.transaction(workspace_id=workspace_id) as db:
            moment = (await db.execute(LAST_USAGE_DAY, {"month": month})).scalar_one()
            return moment.date() if moment else None

    async def cost_through_day(
        self,
        workspace_id: UUID,
        month: date,
        day: int,
        cost_type: CostType,
        currency: str,
        provider: str | None,
    ) -> Decimal:
        query = BILLED_THROUGH_DAY if cost_type is CostType.BILLED else EFFECTIVE_THROUGH_DAY
        async with self._database.transaction(workspace_id=workspace_id) as db:
            result = await db.execute(
                query, {"month": month, "day": day, "currency": currency, "provider": provider}
            )
            return result.scalar_one()
