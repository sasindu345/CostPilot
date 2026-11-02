"""Builds the numbers behind the Overview and Analytics pages."""

import calendar
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from costpilot.modules.analytics.application.ports import AnalyticsStore, UnusualCostDetector
from costpilot.modules.analytics.domain.calculations import (
    build_trend,
    compare_services,
    month_window,
    monthly_totals,
    percent_change,
    previous_month,
    top_services,
)
from costpilot.modules.analytics.domain.models import (
    Filters,
    MonthChange,
    MonthCost,
    ServiceComparison,
    ServiceCost,
    ServiceMonthCost,
    UnusualCost,
)


@dataclass(frozen=True)
class Overview:
    currency: str
    currencies: list[str]
    providers: list[str]
    total: Decimal
    latest_month: date
    latest_cost: Decimal
    latest_is_partial: bool
    days_covered: int | None
    previous_cost: Decimal | None
    change: MonthChange
    trend: list[MonthCost]
    top_services: list[ServiceCost]


class AnalyticsService:
    def __init__(
        self,
        store: AnalyticsStore,
        detector: UnusualCostDetector,
        top_service_limit: int,
        today: Callable[[], date],
    ) -> None:
        self._store = store
        self._detector = detector
        self._top_service_limit = top_service_limit
        self._today = today

    async def overview(self, workspace_id: UUID, filters: Filters) -> Overview | None:
        """Return None if this workspace has no costs yet."""
        selected, currencies = await self._selected_costs(workspace_id, filters)
        if not selected:
            return None

        totals = monthly_totals(selected)
        latest = max(totals)
        window = month_window(latest, filters.months)
        previous = previous_month(latest)
        last_day = await self._store.last_usage_day(workspace_id, latest)
        is_partial, days_covered = self._coverage(latest, last_day)
        change = await self._change(
            workspace_id, filters, selected[0].currency, totals, latest, is_partial, days_covered
        )
        return Overview(
            currency=selected[0].currency,
            currencies=currencies,
            providers=await self._store.providers(workspace_id),
            total=sum((totals.get(month, Decimal(0)) for month in window), Decimal(0)),
            latest_month=latest,
            latest_cost=totals[latest],
            latest_is_partial=is_partial,
            days_covered=days_covered,
            previous_cost=totals.get(previous),
            change=change,
            trend=build_trend(totals, window),
            top_services=top_services(selected, latest, self._top_service_limit),
        )

    async def compare(
        self, workspace_id: UUID, filters: Filters, first: date, second: date
    ) -> list[ServiceComparison]:
        selected, _ = await self._selected_costs(workspace_id, filters)
        return compare_services(selected, first, second)

    async def unusual_costs(self, workspace_id: UUID, filters: Filters) -> list[UnusualCost]:
        selected, _ = await self._selected_costs(workspace_id, filters)
        if not selected:
            return []
        latest = max(item.month for item in selected)
        last_day = await self._store.last_usage_day(workspace_id, latest)
        is_partial, _ = self._coverage(latest, last_day)
        checked_month = previous_month(latest) if is_partial else latest
        return self._detector.find(selected, checked_month)

    async def has_line_items(self, workspace_id: UUID) -> bool:
        return await self._store.has_line_items(workspace_id)

    async def _selected_costs(
        self, workspace_id: UUID, filters: Filters
    ) -> tuple[list[ServiceMonthCost], list[str]]:
        costs = await self._store.service_month_costs(
            workspace_id, filters.cost_type, filters.provider
        )
        if not costs:
            return [], []
        counts = Counter(item.currency for item in costs)
        currencies = sorted(counts, key=lambda currency: (-counts[currency], currency))
        currency = filters.currency if filters.currency in currencies else currencies[0]
        return [item for item in costs if item.currency == currency], currencies

    def _coverage(self, month: date, last_day: date | None) -> tuple[bool, int | None]:
        days_in_month = calendar.monthrange(month.year, month.month)[1]
        if last_day is not None:
            return last_day.day < days_in_month, last_day.day
        today = self._today()
        is_current_month = (today.year, today.month) == (month.year, month.month)
        return is_current_month, None

    async def _change(
        self,
        workspace_id: UUID,
        filters: Filters,
        currency: str,
        totals: dict[date, Decimal],
        latest: date,
        is_partial: bool,
        days_covered: int | None,
    ) -> MonthChange:
        previous = previous_month(latest)
        previous_cost = totals.get(previous)
        if previous_cost is None:
            return MonthChange(None, None, None)
        if not is_partial:
            return MonthChange(percent_change(previous_cost, totals[latest]), None, previous_cost)
        if days_covered is None:
            return MonthChange(None, None, previous_cost)
        same_days_cost = await self._store.cost_through_day(
            workspace_id, previous, days_covered, filters.cost_type, currency, filters.provider
        )
        return MonthChange(
            percent_change(same_days_cost, totals[latest]), days_covered, same_days_cost
        )
