from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class CostType(StrEnum):
    """Billed matches the invoice. Effective spreads prepaid discounts over the usage."""

    BILLED = "billed"
    EFFECTIVE = "effective"


@dataclass(frozen=True)
class Filters:
    months: int
    cost_type: CostType = CostType.BILLED
    currency: str | None = None
    provider: str | None = None


@dataclass(frozen=True)
class ServiceMonthCost:
    month: date
    service: str
    currency: str
    cost: Decimal


@dataclass(frozen=True)
class MonthCost:
    month: date
    cost: Decimal | None


@dataclass(frozen=True)
class ServiceCost:
    name: str
    cost: Decimal
    share_percent: Decimal


@dataclass(frozen=True)
class MonthChange:
    """`percent` is None when the two periods cannot be fairly compared."""

    percent: Decimal | None
    compared_days: int | None
    previous_cost: Decimal | None


@dataclass(frozen=True)
class ServiceComparison:
    service: str
    first_cost: Decimal
    second_cost: Decimal
    difference: Decimal
    percent: Decimal | None


@dataclass(frozen=True)
class UnusualCost:
    service: str
    month: date
    cost: Decimal
    usual_cost: Decimal
    increase: Decimal
    percent: Decimal | None
