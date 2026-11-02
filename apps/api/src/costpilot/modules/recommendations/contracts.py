"""Public interface of the recommendations module. Other modules may only import from here."""

from typing import Protocol
from uuid import UUID

from costpilot.modules.recommendations.domain.models import Recommendation

__all__ = ["Recommendation", "RecommendationReader"]


class RecommendationReader(Protocol):
    async def for_workspace(self, workspace_id: UUID) -> list[Recommendation]: ...
