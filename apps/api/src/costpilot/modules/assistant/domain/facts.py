"""Turns analytics results into facts. Only these approved summary values ever reach the AI.

Account IDs, resource names and tags are never read here, so they cannot reach Gemini.
"""

import re
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from costpilot.modules.analytics.contracts import (
    Overview,
    ServiceComparison,
    UnusualCost,
    UsageChange,
)
from costpilot.modules.assistant.domain.models import DocumentPassage, Fact, Finding
from costpilot.modules.recommendations.contracts import Recommendation

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

    def add(self, label: str, value: str, subject: str = "") -> str:
        fact_id = f"F{len(self.facts) + 1}"
        self.facts.append(Fact(fact_id, label, value, subject))
        return fact_id

    def add_latest(self, overview: Overview) -> None:
        """A short summary, for specialists that do not need the whole history."""
        latest = month_name(overview.latest_month)
        self.add(f"Cost in {latest}", money(overview.latest_cost, overview.currency))
        for service in overview.top_services:
            name = safe_label(service.name)
            self.add(f"{name} cost in {latest}", money(service.cost, overview.currency), name)

    def add_usage_changes(
        self, changes: Iterable[UsageChange], first: date, second: date, currency: str
    ) -> None:
        """Usage types and regions may reach the AI. Resource names never do, only a count."""
        for change in changes:
            name = safe_label(change.service)
            detail = f"{name} {safe_label(change.usage_type)} in {safe_label(change.region)}"
            self.add(f"{detail}, {month_name(first)}", money(change.first_cost, currency), name)
            self.add(f"{detail}, {month_name(second)}", money(change.second_cost, currency), name)
            self.add(f"{detail}, number of resources", f"{change.resources} resources", name)

    def add_recommendations(self, items: Iterable[Recommendation]) -> list[DocumentPassage]:
        """Provable savings become facts. Rule reasons become evidence, with their source."""
        passages = []
        for item in items:
            ids: tuple[str, ...] = ()
            if item.monthly_saving is not None:
                label = f"Provable monthly saving: {item.title}"
                ids = (self.add(label, money(item.monthly_saving, item.currency)),)
            note = "" if ids else " (saving needs usage data)"
            urls = (item.source_url,) if item.source_url else ()
            self.findings.append(Finding(f"{item.title}{note}", ids, urls))
            if item.source_url:
                passages.append(
                    DocumentPassage(item.source_title or item.title, item.source_url, item.reason)
                )
        return passages

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
            self.add(f"{name} cost in {latest}", money(service.cost, currency), name)
            self.add(f"{name} share of {latest}", percent(service.share_percent), name)

    def add_unusual(self, items: Iterable[UnusualCost], currency: str) -> None:
        for item in items:
            name = safe_label(item.service)
            month = month_name(item.month)
            ids = (
                self.add(
                    f"{name} cost in {month}, flagged as unusual",
                    money(item.cost, currency),
                    name,
                ),
                self.add(f"{name} usual monthly cost", money(item.usual_cost, currency), name),
                self.add(f"{name} increase over usual", money(item.increase, currency), name),
            )
            self.findings.append(Finding(f"{name} is above its usual level in {month}", ids))

    def add_comparison(
        self, rows: Iterable[ServiceComparison], first: date, second: date, currency: str
    ) -> None:
        for row in rows:
            name = safe_label(row.service)
            self.add(f"{name} cost in {month_name(first)}", money(row.first_cost, currency), name)
            self.add(f"{name} cost in {month_name(second)}", money(row.second_cost, currency), name)
            self.add(f"{name} change", money(row.difference, currency), name)
            if row.percent is not None:
                self.add(f"{name} percent change", percent(row.percent), name)
