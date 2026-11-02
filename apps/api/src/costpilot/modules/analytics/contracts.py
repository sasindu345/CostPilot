"""Public interface of the analytics module. Other modules may only import from here."""

from datetime import date
from typing import Protocol
from uuid import UUID

from costpilot.modules.analytics.application.analytics_service import Overview
from costpilot.modules.analytics.domain.calculations import previous_month
from costpilot.modules.analytics.domain.models import Filters, ServiceComparison, UnusualCost

__all__ = [
    "AnalyticsReader",
    "Filters",
    "Overview",
    "ServiceComparison",
    "UnusualCost",
    "previous_month",
]


class AnalyticsReader(Protocol):
    async def overview(self, workspace_id: UUID, filters: Filters) -> Overview | None: ...

    async def unusual_costs(self, workspace_id: UUID, filters: Filters) -> list[UnusualCost]: ...

    async def compare(
        self, workspace_id: UUID, filters: Filters, first: date, second: date
    ) -> list[ServiceComparison]: ...

    async def has_line_items(self, workspace_id: UUID) -> bool: ...
