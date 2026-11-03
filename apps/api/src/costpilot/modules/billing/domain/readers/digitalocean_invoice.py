"""Reads the DigitalOcean invoice CSV. DigitalOcean has no FOCUS export.

The description column can hold IP addresses and server names, so it is stored as the resource,
which never reaches the AI. The product group is used as the usage type instead.
"""

from collections.abc import Iterable, Iterator

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

PROVIDER = "digitalocean"
CURRENCY = "USD"
REQUIRED = ("product", "description", "start", "end", "usd")
TAX_PRODUCT = "taxes"
CREDIT_PRODUCT = "credits"
FIRST_RECORD_ROW = 2
HOURS_UNIT = "Hours"


def _money_text(value: str) -> str:
    """ "$3.11" and "-$5.00" become "3.11" and "-5.00"."""
    return value.strip().replace("$", "").replace(",", "")


class DigitalOceanInvoiceReader:
    def matches(self, columns: list[str]) -> bool:
        lookup = column_lookup(columns)
        return all(name in lookup for name in REQUIRED)

    def read(self, columns: list[str], rows: Iterable[list[str]]) -> Iterator[CostRecord]:
        lookup = column_lookup(columns)
        for number, row in enumerate(rows, start=FIRST_RECORD_ROW):
            if row:
                yield self._to_record(row, lookup, number)

    def _to_record(self, row: list[str], lookup: dict[str, int], number: int) -> CostRecord:
        product = clean_text(cell(row, lookup, "product"))
        cost = parse_money(_money_text(cell(row, lookup, "USD")), number)
        group = clean_text(cell(row, lookup, "group_description"))
        hours = cell(row, lookup, "hours")
        tag = clean_text(cell(row, lookup, "tag_name"))
        return CostRecord(
            provider_name=PROVIDER,
            charge_period_start=parse_time(cell(row, lookup, "start"), number),
            charge_period_end=parse_time(cell(row, lookup, "end"), number),
            service_name=product,
            service_category=category(PROVIDER, product),
            charge_category=self._charge(product, cost),
            billed_cost=cost,
            effective_cost=cost,
            billing_currency=CURRENCY,
            detail_level=DetailLevel.LINE_ITEM,
            sub_account_id=clean_text(cell(row, lookup, "project_name")),
            resource_id=clean_text(cell(row, lookup, "description")),
            sku_id=group or product,
            consumed_quantity=parse_optional_number(hours, number),
            consumed_unit=HOURS_UNIT if hours.strip() else "",
            tags={"tag": tag} if tag else {},
        )

    def _charge(self, product: str, cost) -> ChargeCategory:
        name = product.lower()
        if name == TAX_PRODUCT:
            return ChargeCategory.TAX
        if name == CREDIT_PRODUCT or cost < 0:
            return ChargeCategory.CREDIT
        return ChargeCategory.USAGE
