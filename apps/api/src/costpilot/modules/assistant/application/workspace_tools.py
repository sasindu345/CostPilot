"""The only tools the agents can use.

The workspace is fixed when this object is built from the login session. No method accepts a
workspace, so nothing the AI says can point a tool at another user's data.
"""

from uuid import UUID

from costpilot.modules.analytics.contracts import (
    AnalyticsReader,
    Filters,
    Overview,
    previous_month,
)
from costpilot.modules.assistant.domain.facts import FactList
from costpilot.modules.assistant.domain.models import DocumentPassage, Evidence, Route
from costpilot.modules.knowledge.contracts import KnowledgeSearch
from costpilot.modules.recommendations.contracts import RecommendationReader

HISTORY_MONTHS = 6
DEFAULT_PROVIDER = "aws"
NO_BILLS = "No bills have been uploaded yet, so there are no figures to use."
SUMMARY_ONLY = (
    "Only monthly totals per service are available, so the cause of a change "
    "cannot be traced to a specific resource or usage type."
)
PARTIAL_MONTH = "The latest month is not finished."
DOCUMENTS_DOWN = "Cloud documentation search is unavailable, so no documents could be checked."
NO_DOCUMENTS = "No matching cloud documentation was found."


class WorkspaceTools:
    def __init__(
        self,
        workspace_id: UUID,
        analytics: AnalyticsReader,
        knowledge: KnowledgeSearch,
        recommendations: RecommendationReader,
    ) -> None:
        self._workspace_id = workspace_id
        self._analytics = analytics
        self._knowledge = knowledge
        self._recommendations = recommendations

    async def _overview(self) -> Overview | None:
        return await self._analytics.overview(self._workspace_id, Filters(months=HISTORY_MONTHS))

    async def cost_evidence(self) -> Evidence:
        facts = FactList()
        limitations = await self._add_costs(facts)
        return Evidence((Route.COST,), facts.facts, limitations=limitations)

    async def anomaly_evidence(self) -> Evidence:
        facts = FactList()
        overview = await self._overview()
        if overview is None:
            return Evidence((Route.ANOMALY,), limitations=[NO_BILLS])
        limitations = [PARTIAL_MONTH] if overview.latest_is_partial else []
        filters = Filters(months=HISTORY_MONTHS)
        latest = overview.latest_month
        first = previous_month(latest)
        facts.add_latest(overview)
        unusual = await self._analytics.unusual_costs(self._workspace_id, filters)
        facts.add_unusual(unusual, overview.currency)
        rows = await self._analytics.compare(self._workspace_id, filters, first, latest)
        facts.add_comparison(rows, first, latest, overview.currency)
        if await self.has_line_detail():
            changes = await self._analytics.usage_changes(
                self._workspace_id, filters, overview.currency, first, latest
            )
            facts.add_usage_changes(changes, first, latest, overview.currency)
        else:
            limitations.append(SUMMARY_ONLY)
        return Evidence(
            (Route.ANOMALY,), facts.facts, limitations=limitations, findings=facts.findings
        )

    async def search_documents(
        self, question: str, provider: str | None
    ) -> tuple[list[DocumentPassage], list[str]]:
        """Runs once per question, and the specialists share the result."""
        overview = await self._overview()
        default = overview.providers[0] if overview and overview.providers else DEFAULT_PROVIDER
        result = await self._knowledge.search(question, provider or default)
        if not result.is_available:
            return [], [DOCUMENTS_DOWN]
        if not result.passages:
            return [], [NO_DOCUMENTS]
        passages = [DocumentPassage(p.title, p.url, p.text) for p in result.passages]
        return passages, []

    async def optimization_evidence(
        self, passages: list[DocumentPassage], search_limits: list[str]
    ) -> Evidence:
        facts = FactList()
        overview = await self._overview()
        if overview is None:
            return Evidence((Route.OPTIMIZATION,), passages=passages, limitations=[NO_BILLS])
        facts.add_latest(overview)
        found = await self._recommendations.for_workspace(self._workspace_id)
        rule_passages = facts.add_recommendations(found)
        limitations = [*search_limits, *([PARTIAL_MONTH] if overview.latest_is_partial else [])]
        return Evidence(
            (Route.OPTIMIZATION,),
            facts.facts,
            [*passages, *rule_passages],
            limitations,
            facts.findings,
        )

    def knowledge_evidence(
        self, passages: list[DocumentPassage], search_limits: list[str]
    ) -> Evidence:
        return Evidence((Route.KNOWLEDGE,), passages=passages, limitations=search_limits)

    async def has_line_detail(self) -> bool:
        return await self._analytics.has_line_items(self._workspace_id)

    async def _add_costs(self, facts: FactList) -> list[str]:
        overview = await self._overview()
        if overview is None:
            return [NO_BILLS]
        facts.add_overview(overview, HISTORY_MONTHS)
        return [PARTIAL_MONTH] if overview.latest_is_partial else []
