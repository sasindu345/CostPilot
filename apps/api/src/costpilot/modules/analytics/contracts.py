"""Public interface of the analytics module. Other modules may only import from here."""

from datetime import date
from typing import Protocol
from uuid import UUID

from costpilot.modules.analytics.application.analytics_service import Overview
from costpilot.modules.analytics.domain.calculations import month_window, previous_month
from costpilot.modules.analytics.domain.models import (
    Filters,
    ServiceComparison,
    ServiceMonthCost,
    UnusualCost,
    UsageChange,
)

__all__ = [
    "AnalyticsReader",
    "Filters",
    "Overview",
    "ServiceComparison",
    "ServiceMonthCost",
    "UnusualCost",
    "UsageChange",
    "month_window",
    "previous_month",
]


class AnalyticsReader(Protocol):
    async def overview(self, workspace_id: UUID, filters: Filters) -> Overview | None: ...

    async def unusual_costs(self, workspace_id: UUID, filters: Filters) -> list[UnusualCost]: ...

    async def compare(
        self, workspace_id: UUID, filters: Filters, first: date, second: date
    ) -> list[ServiceComparison]: ...

    async def has_line_items(self, workspace_id: UUID) -> bool: ...

    async def service_costs(
        self, workspace_id: UUID, filters: Filters
    ) -> list[ServiceMonthCost]: ...

    async def usage_changes(
        self, workspace_id: UUID, filters: Filters, currency: str, first: date, second: date
    ) -> list[UsageChange]: ...
