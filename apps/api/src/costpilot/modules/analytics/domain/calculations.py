"""All money calculations. Everything here is exact, and the AI only ever reads the results."""

from collections.abc import Iterable, Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from costpilot.modules.analytics.domain.models import (
    MonthCost,
    ServiceComparison,
    ServiceCost,
    ServiceMonthCost,
)

PERCENT_PLACES = Decimal("0.1")
HUNDRED = Decimal(100)
OTHER_SERVICES = "Other"


def percent_of(part: Decimal, whole: Decimal) -> Decimal:
    return (part / whole * HUNDRED).quantize(PERCENT_PLACES, rounding=ROUND_HALF_UP)


def percent_change(previous: Decimal, current: Decimal) -> Decimal | None:
    """There is no fair percentage from a starting point of zero, or from a net credit."""
    if previous <= 0:
        return None
    return percent_of(current - previous, previous)


def month_window(latest: date, months: int) -> list[date]:
    """The last `months` calendar months, oldest first, ending at `latest`."""
    position = latest.year * 12 + (latest.month - 1)
    return [
        date(index // 12, index % 12 + 1, 1) for index in range(position - months + 1, position + 1)
    ]


def previous_month(month: date) -> date:
    return month_window(month, 2)[0]


def monthly_totals(costs: Iterable[ServiceMonthCost]) -> dict[date, Decimal]:
    totals: dict[date, Decimal] = {}
    for item in costs:
        totals[item.month] = totals.get(item.month, Decimal(0)) + item.cost
    return totals


def build_trend(totals: dict[date, Decimal], window: Sequence[date]) -> list[MonthCost]:
    """A month with no bill stays empty. It is not the same as a month that cost $0."""
    return [MonthCost(month, totals.get(month)) for month in window]


def top_services(costs: Iterable[ServiceMonthCost], month: date, limit: int) -> list[ServiceCost]:
    """The biggest services, plus an Other row, so the list always adds up to the month's total."""
    by_service: dict[str, Decimal] = {}
    for item in costs:
        if item.month == month:
            by_service[item.service] = by_service.get(item.service, Decimal(0)) + item.cost
    total = sum(by_service.values(), Decimal(0))
    if total <= 0:
        return []

    # A bill may have its own service called Other, so it joins the Other row at the end.
    already_other = by_service.pop(OTHER_SERVICES, Decimal(0))
    ranked = sorted(by_service.items(), key=lambda pair: (-pair[1], pair[0]))
    shown = ranked[:limit]
    rest = already_other + sum((cost for _, cost in ranked[limit:]), Decimal(0))
    if rest != 0:
        shown.append((OTHER_SERVICES, rest))
    return [ServiceCost(name, cost, percent_of(cost, total)) for name, cost in shown]


def compare_services(
    costs: Iterable[ServiceMonthCost], first: date, second: date
) -> list[ServiceComparison]:
    """Every service in either month, with the biggest change first."""
    amounts: dict[str, dict[date, Decimal]] = {}
    for item in costs:
        if item.month in (first, second):
            service = amounts.setdefault(item.service, {})
            service[item.month] = service.get(item.month, Decimal(0)) + item.cost

    rows = []
    for service, months in amounts.items():
        first_cost = months.get(first, Decimal(0))
        second_cost = months.get(second, Decimal(0))
        rows.append(
            ServiceComparison(
                service=service,
                first_cost=first_cost,
                second_cost=second_cost,
                difference=second_cost - first_cost,
                percent=percent_change(first_cost, second_cost),
            )
        )
    return sorted(rows, key=lambda row: (-abs(row.difference), row.service))
