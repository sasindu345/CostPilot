"""Builds recommendations on request. It uses no AI, so opening the dashboard costs nothing."""

from collections.abc import Mapping
from decimal import Decimal
from uuid import UUID

from costpilot.modules.analytics.contracts import AnalyticsReader, Filters, previous_month
from costpilot.modules.recommendations.domain.models import Recommendation
from costpilot.modules.recommendations.domain.profiles import PROFILES
from costpilot.modules.recommendations.domain.rules import RuleInput, find_recommendations

HISTORY_MONTHS = 6


class RecommendationService:
    def __init__(
        self,
        analytics: AnalyticsReader,
        min_monthly_cost: Decimal,
        steady_ratio: Decimal,
        docs_urls: Mapping[str, str],
    ) -> None:
        self._analytics = analytics
        self._min_monthly_cost = min_monthly_cost
        self._steady_ratio = steady_ratio
        self._docs_urls = docs_urls

    async def for_workspace(self, workspace_id: UUID) -> list[Recommendation]:
        filters = Filters(months=HISTORY_MONTHS)
        overview = await self._analytics.overview(workspace_id, filters)
        if overview is None:
            return []
        month = (
            previous_month(overview.latest_month)
            if overview.latest_is_partial
            else overview.latest_month
        )
        found: list[Recommendation] = []
        for provider in overview.providers:
            profile = PROFILES.get(provider)
            docs_url = self._docs_urls.get(provider)
            if profile is None or docs_url is None:
                continue
            scoped = Filters(months=HISTORY_MONTHS, provider=provider)
            data = RuleInput(
                costs=await self._analytics.service_costs(workspace_id, scoped),
                usage=await self._analytics.usage_changes(
                    workspace_id, scoped, overview.currency, previous_month(month), month
                ),
                month=month,
                currency=overview.currency,
                min_monthly_cost=self._min_monthly_cost,
                steady_ratio=self._steady_ratio,
                docs_url=docs_url,
            )
            found += find_recommendations(profile, data)
        return found
