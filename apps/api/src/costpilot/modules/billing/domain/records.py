"""The common bill format. Field names follow the FOCUS specification."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class DetailLevel(StrEnum):
    """How much a file can tell us. A higher value wins when two files cover the same month."""

    SERVICE_MONTH = "service_month"
    LINE_ITEM = "line_item"


class ChargeCategory(StrEnum):
    USAGE = "Usage"
    PURCHASE = "Purchase"
    TAX = "Tax"
    CREDIT = "Credit"
    ADJUSTMENT = "Adjustment"


@dataclass(frozen=True)
class CostRecord:
    provider_name: str
    charge_period_start: datetime
    charge_period_end: datetime
    service_name: str
    service_category: str
    charge_category: ChargeCategory
    billed_cost: Decimal
    effective_cost: Decimal
    billing_currency: str
    detail_level: DetailLevel
    billing_account_id: str = ""
    sub_account_id: str = ""
    list_cost: Decimal | None = None
    region_id: str = ""
    resource_id: str = ""
    sku_id: str = ""
    consumed_quantity: Decimal | None = None
    consumed_unit: str = ""
    tags: dict[str, str] = field(default_factory=dict)
