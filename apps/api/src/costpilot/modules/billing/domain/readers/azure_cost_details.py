"""Reads Azure Cost Management cost details exports, for EA, MCA and pay-as-you-go accounts.

Column names differ by account type and in case, so each value has several possible columns.
"""

from collections.abc import Iterable, Iterator
from datetime import timedelta

from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.readers.base import (
    cell,
    clean_text,
    column_lookup,
    parse_json_map,
    parse_money,
    parse_optional_number,
    parse_time,
)
from costpilot.modules.billing.domain.readers.service_categories import category
from costpilot.modules.billing.domain.records import ChargeCategory, CostRecord, DetailLevel

PROVIDER = "azure"
COST_COLUMNS = ("CostInBillingCurrency", "PreTaxCost", "Cost")
DATE_COLUMNS = ("Date", "UsageDateTime")
CURRENCY_COLUMNS = ("BillingCurrency", "BillingCurrencyCode", "Currency")
# Azure writes dates as month, day, year.
DATE_FORMATS = ("%m/%d/%Y", "%m/%d/%Y %H:%M:%S")
FIRST_RECORD_ROW = 2
ONE_DAY = timedelta(days=1)

CHARGE_CATEGORIES = {
    "usage": ChargeCategory.USAGE,
    "unusedreservation": ChargeCategory.USAGE,
    "unusedsavingsplan": ChargeCategory.USAGE,
    "purchase": ChargeCategory.PURCHASE,
    "refund": ChargeCategory.ADJUSTMENT,
    "roundingadjustment": ChargeCategory.ADJUSTMENT,
    "tax": ChargeCategory.TAX,
}


class AzureCostDetailsReader:
    def matches(self, columns: list[str]) -> bool:
        lookup = column_lookup(columns)
        return (
            "metercategory" in lookup
            and any(name.lower() in lookup for name in COST_COLUMNS)
            and any(name.lower() in lookup for name in DATE_COLUMNS)
        )

    def read(self, columns: list[str], rows: Iterable[list[str]]) -> Iterator[CostRecord]:
        lookup = column_lookup(columns)
        for number, row in enumerate(rows, start=FIRST_RECORD_ROW):
            if row:
                yield self._to_record(row, lookup, number)

    def _to_record(self, row: list[str], lookup: dict[str, int], number: int) -> CostRecord:
        charge_type = clean_text(cell(row, lookup, "ChargeType")) or "Usage"
        charge = CHARGE_CATEGORIES.get(charge_type.lower())
        if charge is None:
            raise BillRejectedError(
                f"Row {number} has a charge type we do not know: {charge_type}."
            )
        currency = clean_text(cell(row, lookup, *CURRENCY_COLUMNS)).upper()
        if not currency:
            raise BillRejectedError(f"Row {number} has no currency.")
        start = parse_time(cell(row, lookup, *DATE_COLUMNS), number, DATE_FORMATS)
        service = clean_text(cell(row, lookup, "MeterCategory", "ConsumedService")) or charge_type
        subcategory = clean_text(cell(row, lookup, "MeterSubCategory"))
        meter = clean_text(cell(row, lookup, "MeterName"))
        cost = parse_money(cell(row, lookup, *COST_COLUMNS), number)
        return CostRecord(
            provider_name=PROVIDER,
            charge_period_start=start,
            charge_period_end=start + ONE_DAY,
            service_name=service,
            service_category=category(PROVIDER, service),
            charge_category=charge,
            billed_cost=cost,
            # An actual cost export has no spread of prepaid discounts, so both costs match.
            effective_cost=cost,
            billing_currency=currency,
            detail_level=DetailLevel.LINE_ITEM,
            billing_account_id=clean_text(cell(row, lookup, "BillingAccountId")),
            sub_account_id=clean_text(cell(row, lookup, "SubscriptionId")),
            list_cost=parse_optional_number(cell(row, lookup, "paygCostInBillingCurrency"), number),
            region_id=clean_text(cell(row, lookup, "ResourceLocation", "Location", "MeterRegion")),
            resource_id=clean_text(cell(row, lookup, "ResourceId", "InstanceId")),
            sku_id=": ".join(part for part in (subcategory, meter) if part),
            consumed_quantity=parse_optional_number(
                cell(row, lookup, "Quantity", "UsageQuantity"), number
            ),
            consumed_unit=clean_text(cell(row, lookup, "UnitOfMeasure")),
            tags=parse_json_map(cell(row, lookup, "Tags")),
        )
