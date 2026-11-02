from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from costpilot.modules.analytics.domain.models import (
    CostType,
    ServiceMonthCost,
    UnusualCost,
    UsageChange,
)


class AnalyticsStore(Protocol):
    async def service_month_costs(
        self, workspace_id: UUID, cost_type: CostType, provider: str | None
    ) -> list[ServiceMonthCost]: ...

    async def providers(self, workspace_id: UUID) -> list[str]: ...

    async def has_line_items(self, workspace_id: UUID) -> bool:
        """Do any counted files have line-by-line detail, or only monthly totals?"""

    async def usage_changes(
        self,
        workspace_id: UUID,
        first: date,
        second: date,
        cost_type: CostType,
        currency: str,
        provider: str | None,
        limit: int,
    ) -> list[UsageChange]:
        """The biggest changes by usage type and region. Needs line-item files."""

    async def last_usage_day(self, workspace_id: UUID, month: date) -> date | None:
        """The last day of a month that has usage. None if the file only has monthly totals."""

    async def cost_through_day(
        self,
        workspace_id: UUID,
        month: date,
        day: int,
        cost_type: CostType,
        currency: str,
        provider: str | None,
    ) -> Decimal: ...


class UnusualCostDetector(Protocol):
    def find(self, costs: list[ServiceMonthCost], latest_month: date) -> list[UnusualCost]: ...
