from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from costpilot.modules.analytics.application.analytics_service import AnalyticsService
from costpilot.modules.analytics.domain.models import CostType, Filters
from costpilot.modules.identity.contracts import SignedInUser

router = APIRouter(prefix="/analytics", tags=["analytics"])

MIN_MONTHS = 1
MAX_MONTHS = 36
DEFAULT_MONTHS = 6


def get_analytics(request: Request) -> AnalyticsService:
    return request.app.state.analytics


Analytics = Annotated[AnalyticsService, Depends(get_analytics)]


def get_filters(
    months: Annotated[int, Query(ge=MIN_MONTHS, le=MAX_MONTHS)] = DEFAULT_MONTHS,
    cost_type: CostType = CostType.BILLED,
    currency: str | None = None,
    provider: str | None = None,
) -> Filters:
    return Filters(months=months, cost_type=cost_type, currency=currency, provider=provider)


SelectedFilters = Annotated[Filters, Depends(get_filters)]


class MonthCostResponse(BaseModel):
    month: date
    cost: Decimal | None


class ServiceCostResponse(BaseModel):
    name: str
    cost: Decimal
    share_percent: Decimal


class ChangeResponse(BaseModel):
    percent: Decimal | None
    compared_days: int | None
    previous_cost: Decimal | None


class OverviewResponse(BaseModel):
    currency: str
    currencies: list[str]
    providers: list[str]
    total: Decimal
    latest_month: date
    latest_cost: Decimal
    latest_is_partial: bool
    days_covered: int | None
    previous_cost: Decimal | None
    change: ChangeResponse
    trend: list[MonthCostResponse]
    top_services: list[ServiceCostResponse]


class ServiceComparisonResponse(BaseModel):
    service: str
    first_cost: Decimal
    second_cost: Decimal
    difference: Decimal
    percent: Decimal | None


class UnusualCostResponse(BaseModel):
    service: str
    month: date
    cost: Decimal
    usual_cost: Decimal
    increase: Decimal
    percent: Decimal | None


@router.get("/overview")
async def overview(
    user: SignedInUser, analytics: Analytics, filters: SelectedFilters
) -> OverviewResponse | None:
    result = await analytics.overview(user.workspace_id, filters)
    if result is None:
        return None
    return OverviewResponse.model_validate(result, from_attributes=True)


@router.get("/compare")
async def compare(
    first: date, second: date, user: SignedInUser, analytics: Analytics, filters: SelectedFilters
) -> list[ServiceComparisonResponse]:
    rows = await analytics.compare(user.workspace_id, filters, first, second)
    return [ServiceComparisonResponse.model_validate(row, from_attributes=True) for row in rows]


@router.get("/unusual")
async def unusual(
    user: SignedInUser, analytics: Analytics, filters: SelectedFilters
) -> list[UnusualCostResponse]:
    rows = await analytics.unusual_costs(user.workspace_id, filters)
    return [UnusualCostResponse.model_validate(row, from_attributes=True) for row in rows]
