"""Reads Oracle Cloud's own cost report CSV. Oracle's FOCUS reports use FocusReader instead."""

from collections.abc import Iterable, Iterator
from datetime import timedelta

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

PROVIDER = "oci"
REQUIRED = ("lineitem/intervalusagestart", "cost/mycost", "product/service", "cost/currencycode")
TAG_PREFIX = "tags/"
FIRST_RECORD_ROW = 2
ONE_HOUR = timedelta(hours=1)
TRUE = "true"


class OciCostReportReader:
    def matches(self, columns: list[str]) -> bool:
        lookup = column_lookup(columns)
        return all(name in lookup for name in REQUIRED)

    def read(self, columns: list[str], rows: Iterable[list[str]]) -> Iterator[CostRecord]:
        lookup = column_lookup(columns)
        tag_columns = {
            column.strip()[len(TAG_PREFIX) :]: index
            for index, column in enumerate(columns)
            if column.strip().lower().startswith(TAG_PREFIX)
        }
        for number, row in enumerate(rows, start=FIRST_RECORD_ROW):
            if row:
                yield self._to_record(row, lookup, tag_columns, number)

    def _to_record(
        self, row: list[str], lookup: dict[str, int], tags: dict[str, int], number: int
    ) -> CostRecord:
        start = parse_time(cell(row, lookup, "lineItem/intervalUsageStart"), number)
        end_text = cell(row, lookup, "lineItem/intervalUsageEnd")
        service = clean_text(cell(row, lookup, "product/service"))
        is_correction = cell(row, lookup, "lineItem/isCorrection").strip().lower() == TRUE
        cost = parse_money(cell(row, lookup, "cost/myCost"), number)
        description = clean_text(cell(row, lookup, "product/description"))
        sku = clean_text(cell(row, lookup, "cost/productSku"))
        return CostRecord(
            provider_name=PROVIDER,
            charge_period_start=start,
            charge_period_end=parse_time(end_text, number) if end_text else start + ONE_HOUR,
            service_name=service,
            service_category=category(PROVIDER, service),
            charge_category=ChargeCategory.ADJUSTMENT if is_correction else ChargeCategory.USAGE,
            billed_cost=cost,
            effective_cost=cost,
            billing_currency=clean_text(cell(row, lookup, "cost/currencyCode")).upper(),
            detail_level=DetailLevel.LINE_ITEM,
            billing_account_id=clean_text(cell(row, lookup, "lineItem/tenantId")),
            sub_account_id=clean_text(cell(row, lookup, "product/compartmentId")),
            region_id=clean_text(cell(row, lookup, "product/region")),
            resource_id=clean_text(cell(row, lookup, "product/resourceId")),
            sku_id=" ".join(part for part in (sku, description) if part),
            consumed_quantity=parse_optional_number(
                cell(row, lookup, "usage/billedQuantity"), number
            ),
            consumed_unit=clean_text(cell(row, lookup, "cost/skuUnitDescription")),
            tags={
                key: row[index] for key, index in tags.items() if index < len(row) and row[index]
            },
        )
