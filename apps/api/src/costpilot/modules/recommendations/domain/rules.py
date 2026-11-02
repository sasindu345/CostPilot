"""Finds cost opportunities with plain rules, so the same bill always gives the same results."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from costpilot.modules.analytics.contracts import ServiceMonthCost, UsageChange, month_window
from costpilot.modules.recommendations.domain.models import Recommendation
from costpilot.modules.recommendations.domain.profiles import ProviderProfile

CENTS = Decimal("0.01")
STEADY_MONTHS = 3


@dataclass(frozen=True)
class RuleInput:
    costs: Sequence[ServiceMonthCost]
    usage: Sequence[UsageChange]
    month: date
    currency: str
    min_monthly_cost: Decimal
    steady_ratio: Decimal
    docs_url: str


def _month_cost(costs: Iterable[ServiceMonthCost], services: Sequence[str], month: date) -> Decimal:
    return sum(
        (item.cost for item in costs if item.month == month and item.service in services),
        Decimal(0),
    )


def _is_steady(data: RuleInput, services: Sequence[str]) -> bool:
    amounts = [
        _month_cost(data.costs, services, month)
        for month in month_window(data.month, STEADY_MONTHS)
    ]
    if min(amounts) < data.min_monthly_cost:
        return False
    return max(amounts) <= min(amounts) * data.steady_ratio


def find_recommendations(profile: ProviderProfile, data: RuleInput) -> list[Recommendation]:
    found: list[Recommendation] = []
    for rule in profile.price_rules:
        cost = sum(
            (item.second_cost for item in data.usage if rule.usage_marker in item.usage_type),
            Decimal(0),
        )
        if cost >= data.min_monthly_cost:
            saving = (cost * rule.saving_rate).quantize(CENTS, rounding=ROUND_HALF_UP)
            found.append(_build(profile, rule, data, saving))
    for rule in profile.usage_rules:
        cost = sum(
            (item.second_cost for item in data.usage if rule.usage_marker in item.usage_type),
            Decimal(0),
        )
        if cost >= data.min_monthly_cost:
            found.append(_build(profile, rule, data))
    for rule in profile.steady_rules:
        if _is_steady(data, rule.services):
            found.append(_build(profile, rule, data))
    for rule in profile.review_rules:
        if _month_cost(data.costs, rule.services, data.month) >= data.min_monthly_cost:
            found.append(_build(profile, rule, data))
    return found


def _build(
    profile: ProviderProfile, rule: object, data: RuleInput, saving: Decimal | None = None
) -> Recommendation:
    return Recommendation(
        id=rule.id,
        provider=profile.provider,
        title=rule.title,
        reason=rule.reason,
        currency=data.currency,
        monthly_saving=saving,
        source_title=rule.source_title,
        source_url=f"{data.docs_url}{rule.source_path}",
    )
