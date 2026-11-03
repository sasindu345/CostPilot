"""Reads Google Cloud's standard billing export, saved as a flat CSV from BigQuery.

BigQuery cannot save nested credits to CSV, so `docs/guides/cloud-bills.md` gives a query that
adds them up into a `credits_total` column. Dots and underscores in names are both accepted.
"""

from collections.abc import Iterable, Iterator
from decimal import Decimal

from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.readers.base import (
    cell,
    clean_text,
    column_lookup,
    parse_money,
    parse_optional_number,
    parse_time,
)
from costpilot.modules.billing.domain.readers.service_categories import category
from costpilot.modules.billing.domain.records import ChargeCategory, CostRecord, DetailLevel

PROVIDER = "gcp"
REQUIRED = ("service_description", "usage_start_time", "cost", "currency")
FIRST_RECORD_ROW = 2
CREDIT_SERVICE = "Credits"

COST_TYPES = {
    "regular": ChargeCategory.USAGE,
    "tax": ChargeCategory.TAX,
    "adjustment": ChargeCategory.ADJUSTMENT,
    "rounding_error": ChargeCategory.ADJUSTMENT,
}


def _flat(columns: list[str]) -> list[str]:
    return [column.strip().replace(".", "_") for column in columns]


class GcpBillingExportReader:
    def matches(self, columns: list[str]) -> bool:
        lookup = column_lookup(_flat(columns))
        return all(name in lookup for name in REQUIRED)

    def read(self, columns: list[str], rows: Iterable[list[str]]) -> Iterator[CostRecord]:
        lookup = column_lookup(_flat(columns))
        for number, row in enumerate(rows, start=FIRST_RECORD_ROW):
            if row:
                yield from self._to_records(row, lookup, number)

    def _to_records(
        self, row: list[str], lookup: dict[str, int], number: int
    ) -> Iterator[CostRecord]:
        cost_type = clean_text(cell(row, lookup, "cost_type")).lower() or "regular"
        charge = COST_TYPES.get(cost_type)
        if charge is None:
            raise BillRejectedError(f"Row {number} has a cost type we do not know: {cost_type}.")
        service = clean_text(cell(row, lookup, "service_description"))
        base = {
            "provider_name": PROVIDER,
            "charge_period_start": parse_time(cell(row, lookup, "usage_start_time"), number),
            "charge_period_end": parse_time(
                cell(row, lookup, "usage_end_time", "usage_start_time"), number
            ),
            "billing_currency": clean_text(cell(row, lookup, "currency")).upper(),
            "detail_level": DetailLevel.LINE_ITEM,
            "billing_account_id": clean_text(cell(row, lookup, "billing_account_id")),
            "sub_account_id": clean_text(cell(row, lookup, "project_id")),
            "region_id": clean_text(cell(row, lookup, "location_region", "location_location")),
        }
        cost = parse_money(cell(row, lookup, "cost"), number)
        yield CostRecord(
            **base,
            service_name=service,
            service_category=category(PROVIDER, service),
            charge_category=charge,
            billed_cost=cost,
            effective_cost=cost,
            list_cost=parse_optional_number(cell(row, lookup, "cost_at_list"), number),
            sku_id=clean_text(cell(row, lookup, "sku_description")),
            consumed_quantity=parse_optional_number(cell(row, lookup, "usage_amount"), number),
            consumed_unit=clean_text(cell(row, lookup, "usage_unit")),
        )
        credits = parse_money(cell(row, lookup, "credits_total"), number)
        if credits != Decimal(0):
            yield CostRecord(
                **base,
                service_name=service,
                service_category=category(PROVIDER, service),
                charge_category=ChargeCategory.CREDIT,
                billed_cost=credits,
                effective_cost=credits,
                sku_id=CREDIT_SERVICE,
            )
