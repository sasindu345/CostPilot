from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from costpilot.modules.identity.contracts import SignedInUser
from costpilot.modules.recommendations.application.recommendation_service import (
    RecommendationService,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recommendations(request: Request) -> RecommendationService:
    return request.app.state.recommendations


Recommendations = Annotated[RecommendationService, Depends(get_recommendations)]


class RecommendationResponse(BaseModel):
    id: str
    provider: str
    title: str
    reason: str
    currency: str
    monthly_saving: Decimal | None
    source_title: str | None
    source_url: str | None


@router.get("")
async def list_recommendations(
    user: SignedInUser, recommendations: Recommendations
) -> list[RecommendationResponse]:
    found = await recommendations.for_workspace(user.workspace_id)
    return [RecommendationResponse.model_validate(item, from_attributes=True) for item in found]
