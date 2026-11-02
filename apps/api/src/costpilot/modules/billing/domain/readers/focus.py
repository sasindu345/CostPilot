"""Reads FOCUS exports. The same reader works for every cloud that publishes this format."""

import json
from collections.abc import Iterable, Iterator

from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.readers.base import (
    clean_text,
    parse_money,
    parse_optional_number,
    parse_time,
)
from costpilot.modules.billing.domain.records import ChargeCategory, CostRecord, DetailLevel

REQUIRED_COLUMNS = {
    "BilledCost",
    "EffectiveCost",
    "ChargePeriodStart",
    "ChargePeriodEnd",
    "ChargeCategory",
    "ServiceName",
    "BillingCurrency",
}
PROVIDER_COLUMNS = ("ServiceProviderName", "ProviderName", "InvoiceIssuerName")
PROVIDER_NAMES = {
    "aws": "aws",
    "amazon web services": "aws",
    "microsoft": "azure",
    "azure": "azure",
    "microsoft azure": "azure",
    "google cloud": "gcp",
    "google": "gcp",
    "gcp": "gcp",
    "oracle": "oci",
    "oracle cloud infrastructure": "oci",
    "oci": "oci",
}
CHARGE_CATEGORIES = {category.value.lower(): category for category in ChargeCategory}
FIRST_RECORD_ROW = 2


class FocusReader:
    def matches(self, columns: list[str]) -> bool:
        return {column.strip() for column in columns} >= REQUIRED_COLUMNS

    def read(self, columns: list[str], rows: Iterable[list[str]]) -> Iterator[CostRecord]:
        names = [column.strip() for column in columns]
        for number, values in enumerate(rows, start=FIRST_RECORD_ROW):
            if values:
                yield self._to_record(dict(zip(names, values, strict=False)), number)

    def _to_record(self, row: dict[str, str], number: int) -> CostRecord:
        category = CHARGE_CATEGORIES.get(row["ChargeCategory"].strip().lower())
        if category is None:
            raise BillRejectedError(f"Row {number} has a charge type we do not know.")
        return CostRecord(
            provider_name=self._provider(row),
            charge_period_start=parse_time(row["ChargePeriodStart"], number),
            charge_period_end=parse_time(row["ChargePeriodEnd"], number),
            service_name=clean_text(row["ServiceName"]) or category.value,
            service_category=clean_text(row.get("ServiceCategory", "")) or "Other",
            charge_category=category,
            billed_cost=parse_money(row["BilledCost"], number),
            effective_cost=parse_money(row["EffectiveCost"], number),
            billing_currency=clean_text(row["BillingCurrency"]).upper(),
            detail_level=DetailLevel.LINE_ITEM,
            billing_account_id=clean_text(row.get("BillingAccountId", "")),
            sub_account_id=clean_text(row.get("SubAccountId", "")),
            list_cost=parse_optional_number(row.get("ListCost", ""), number),
            region_id=clean_text(row.get("RegionId", "")),
            resource_id=clean_text(row.get("ResourceId", "")),
            sku_id=clean_text(row.get("SkuId", "")),
            consumed_quantity=parse_optional_number(row.get("ConsumedQuantity", ""), number),
            consumed_unit=clean_text(row.get("ConsumedUnit", "")),
            tags=self._tags(row.get("Tags", "")),
        )

    def _provider(self, row: dict[str, str]) -> str:
        for column in PROVIDER_COLUMNS:
            name = row.get(column, "").strip().lower()
            if name:
                return PROVIDER_NAMES.get(name, clean_text(name))
        return "unknown"

    def _tags(self, value: str) -> dict[str, str]:
        if not value.strip():
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return (
            {str(key): str(item) for key, item in parsed.items()}
            if isinstance(parsed, dict)
            else {}
        )
