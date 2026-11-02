"""Turns analytics results into facts. Only these approved summary values ever reach the AI.

Account IDs, resource names and tags are never read here, so they cannot reach Gemini.
"""

import re
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from costpilot.modules.analytics.contracts import Overview, ServiceComparison, UnusualCost
from costpilot.modules.assistant.domain.models import Fact, Finding

MAX_LABEL_LENGTH = 60
UNSAFE_CHARACTERS = re.compile(r"[^\w .,()/&+:-]")


def safe_label(text: str) -> str:
    """Service names come from the uploaded bill, so they are untrusted text."""
    return UNSAFE_CHARACTERS.sub("", text)[:MAX_LABEL_LENGTH].strip() or "Unnamed service"


def money(amount: Decimal, currency: str) -> str:
    return f"{amount:,.2f} {currency}"


def percent(value: Decimal) -> str:
    return f"{value}%"


def month_name(month: date) -> str:
    return month.strftime("%B %Y")


class FactList:
    """Hands out ids in order: F1, F2, F3."""

    def __init__(self) -> None:
        self.facts: list[Fact] = []
        self.findings: list[Finding] = []

    def add(self, label: str, value: str) -> str:
        fact_id = f"F{len(self.facts) + 1}"
        self.facts.append(Fact(fact_id, label, value))
        return fact_id

    def add_overview(self, overview: Overview, months: int) -> None:
        currency = overview.currency
        latest = month_name(overview.latest_month)
        suffix = " so far" if overview.latest_is_partial else ""
        self.add(f"Total cost, last {months} months", money(overview.total, currency))
        self.add(f"Cost in {latest}{suffix}", money(overview.latest_cost, currency))
        if overview.previous_cost is not None:
            self.add("Cost in the month before", money(overview.previous_cost, currency))
        if overview.change.percent is not None:
            self.add("Change from the month before", percent(overview.change.percent))
        for point in overview.trend:
            if point.cost is not None:
                self.add(f"Cost in {month_name(point.month)}", money(point.cost, currency))
        for service in overview.top_services:
            name = safe_label(service.name)
            self.add(f"{name} cost in {latest}", money(service.cost, currency))
            self.add(f"{name} share of {latest}", percent(service.share_percent))

    def add_unusual(self, items: Iterable[UnusualCost], currency: str) -> None:
        for item in items:
            name = safe_label(item.service)
            month = month_name(item.month)
            ids = (
                self.add(f"{name} cost in {month}, flagged as unusual", money(item.cost, currency)),
                self.add(f"{name} usual monthly cost", money(item.usual_cost, currency)),
                self.add(f"{name} increase over usual", money(item.increase, currency)),
            )
            self.findings.append(Finding(f"{name} is above its usual level in {month}", ids))

    def add_comparison(
        self, rows: Iterable[ServiceComparison], first: date, second: date, currency: str
    ) -> None:
        for row in rows:
            name = safe_label(row.service)
            self.add(f"{name} cost in {month_name(first)}", money(row.first_cost, currency))
            self.add(f"{name} cost in {month_name(second)}", money(row.second_cost, currency))
            self.add(f"{name} change", money(row.difference, currency))
            if row.percent is not None:
                self.add(f"{name} percent change", percent(row.percent))
