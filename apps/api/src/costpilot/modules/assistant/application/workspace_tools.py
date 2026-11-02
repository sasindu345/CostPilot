"""The only tools the agents can use.

The workspace is fixed when this object is built from the login session. No method accepts a
workspace, so nothing the AI says can point a tool at another user's data.
"""

from uuid import UUID

from costpilot.modules.analytics.contracts import AnalyticsReader, Filters, previous_month
from costpilot.modules.assistant.domain.facts import FactList
from costpilot.modules.assistant.domain.models import DocumentPassage, Evidence, Route
from costpilot.modules.knowledge.contracts import KnowledgeSearch

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
        self, workspace_id: UUID, analytics: AnalyticsReader, knowledge: KnowledgeSearch
    ) -> None:
        self._workspace_id = workspace_id
        self._analytics = analytics
        self._knowledge = knowledge

    async def cost_evidence(self) -> Evidence:
        facts = FactList()
        limitations = await self._add_costs(facts)
        return Evidence(Route.COST, facts.facts, limitations=limitations)

    async def anomaly_evidence(self) -> Evidence:
        facts = FactList()
        limitations = await self._add_costs(facts)
        filters = Filters(months=HISTORY_MONTHS)
        overview = await self._analytics.overview(self._workspace_id, filters)
        if overview is not None:
            unusual = await self._analytics.unusual_costs(self._workspace_id, filters)
            facts.add_unusual(unusual, overview.currency)
            first = previous_month(overview.latest_month)
            rows = await self._analytics.compare(
                self._workspace_id, filters, first, overview.latest_month
            )
            facts.add_comparison(rows, first, overview.latest_month, overview.currency)
            if not await self._analytics.has_line_items(self._workspace_id):
                limitations.append(SUMMARY_ONLY)
        return Evidence(Route.ANOMALY, facts.facts, limitations=limitations)

    async def optimization_evidence(self, question: str) -> Evidence:
        facts = FactList()
        limitations = await self._add_costs(facts)
        overview = await self._analytics.overview(
            self._workspace_id, Filters(months=HISTORY_MONTHS)
        )
        provider = overview.providers[0] if overview and overview.providers else DEFAULT_PROVIDER
        result = await self._knowledge.search(question, provider)
        if not result.is_available:
            limitations.append(DOCUMENTS_DOWN)
        elif not result.passages:
            limitations.append(NO_DOCUMENTS)
        passages = [
            DocumentPassage(passage.title, passage.url, passage.text) for passage in result.passages
        ]
        return Evidence(Route.OPTIMIZATION, facts.facts, passages, limitations)

    async def _add_costs(self, facts: FactList) -> list[str]:
        overview = await self._analytics.overview(
            self._workspace_id, Filters(months=HISTORY_MONTHS)
        )
        if overview is None:
            return [NO_BILLS]
        facts.add_overview(overview, HISTORY_MONTHS)
        return [PARTIAL_MONTH] if overview.latest_is_partial else []
