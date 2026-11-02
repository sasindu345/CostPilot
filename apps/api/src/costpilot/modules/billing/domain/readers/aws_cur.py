"""Reads AWS Cost and Usage Reports, in both the old and the new column style."""

import json
import re
from collections.abc import Iterable, Iterator
from decimal import Decimal

from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.readers.aws_services import service_category
from costpilot.modules.billing.domain.readers.base import (
    clean_text,
    parse_money,
    parse_optional_number,
    parse_time,
)
from costpilot.modules.billing.domain.records import ChargeCategory, CostRecord, DetailLevel

PROVIDER = "aws"
REQUIRED_COLUMNS = {
    "line_item_line_item_type",
    "line_item_usage_start_date",
    "line_item_usage_end_date",
    "line_item_product_code",
    "line_item_unblended_cost",
    "line_item_currency_code",
}
LEGACY_TAG_PREFIX = "resource_tags_user:"
FIRST_RECORD_ROW = 2

CHARGE_CATEGORIES = {
    "Usage": ChargeCategory.USAGE,
    "DiscountedUsage": ChargeCategory.USAGE,
    "SavingsPlanCoveredUsage": ChargeCategory.USAGE,
    "SavingsPlanNegation": ChargeCategory.USAGE,
    "Tax": ChargeCategory.TAX,
    "Credit": ChargeCategory.CREDIT,
    "Refund": ChargeCategory.ADJUSTMENT,
    "BundledDiscount": ChargeCategory.ADJUSTMENT,
    "EdpDiscount": ChargeCategory.ADJUSTMENT,
    "Fee": ChargeCategory.PURCHASE,
    "RIFee": ChargeCategory.PURCHASE,
    "SavingsPlanRecurringFee": ChargeCategory.PURCHASE,
    "SavingsPlanUpfrontFee": ChargeCategory.PURCHASE,
}


def normalise_column(name: str) -> str:
    """Turn `lineItem/UnblendedCost` into `line_item_unblended_cost`."""
    category, _, field = name.strip().partition("/")
    if not field:
        return name.strip().lower()
    if ":" in field:
        return f"{_snake(category)}_{field}"
    return f"{_snake(category)}_{_snake(field)}"


def _snake(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value).lower()


class AwsCurReader:
    def matches(self, columns: list[str]) -> bool:
        return {normalise_column(column) for column in columns} >= REQUIRED_COLUMNS

    def read(self, columns: list[str], rows: Iterable[list[str]]) -> Iterator[CostRecord]:
        names = [normalise_column(column) for column in columns]
        for number, values in enumerate(rows, start=FIRST_RECORD_ROW):
            if values:
                yield self._to_record(dict(zip(names, values, strict=False)), number)

    def _to_record(self, row: dict[str, str], number: int) -> CostRecord:
        line_type = row["line_item_line_item_type"].strip()
        category = CHARGE_CATEGORIES.get(line_type)
        if category is None:
            raise BillRejectedError(f"Row {number} has a charge type we do not know: {line_type}.")

        billed_cost = parse_money(row["line_item_unblended_cost"], number)
        service = clean_text(row["line_item_product_code"]) or line_type
        usage_type = clean_text(row.get("line_item_usage_type", ""))
        product = self._json_map(row.get("product", ""))
        return CostRecord(
            provider_name=PROVIDER,
            charge_period_start=parse_time(row["line_item_usage_start_date"], number),
            charge_period_end=parse_time(row["line_item_usage_end_date"], number),
            service_name=service,
            service_category=service_category(service),
            charge_category=category,
            billed_cost=billed_cost,
            effective_cost=self._effective_cost(line_type, billed_cost, row, number),
            billing_currency=clean_text(row["line_item_currency_code"]).upper(),
            detail_level=DetailLevel.LINE_ITEM,
            billing_account_id=clean_text(row.get("bill_payer_account_id", "")),
            sub_account_id=clean_text(row.get("line_item_usage_account_id", "")),
            list_cost=parse_optional_number(row.get("pricing_public_on_demand_cost", ""), number),
            region_id=clean_text(
                row.get("product_region_code")
                or row.get("product_region")
                or product.get("region")
                or ""
            ),
            resource_id=clean_text(row.get("line_item_resource_id", "")),
            sku_id=usage_type,
            consumed_quantity=parse_optional_number(row.get("line_item_usage_amount", ""), number),
            consumed_unit=clean_text(row.get("pricing_unit", "")),
            tags=self._tags(row),
        )

    def _effective_cost(
        self, line_type: str, billed_cost: Decimal, row: dict[str, str], number: int
    ) -> Decimal:
        """Spread prepaid discounts over the usage they paid for, as AWS Cost Explorer does."""

        def amount(column: str) -> Decimal:
            return parse_money(row.get(column, ""), number)

        match line_type:
            case "SavingsPlanCoveredUsage":
                return amount("savings_plan_savings_plan_effective_cost")
            case "DiscountedUsage":
                return amount("reservation_effective_cost")
            case "SavingsPlanNegation" | "SavingsPlanUpfrontFee":
                return Decimal(0)
            case "SavingsPlanRecurringFee":
                return amount("savings_plan_total_commitment_to_date") - amount(
                    "savings_plan_used_commitment"
                )
            case "RIFee":
                return amount("reservation_unused_amortized_upfront_fee_for_billing_period") + (
                    amount("reservation_unused_recurring_fee")
                )
            case _:
                return billed_cost

    def _tags(self, row: dict[str, str]) -> dict[str, str]:
        tags = {
            key.removeprefix(LEGACY_TAG_PREFIX): value
            for key, value in row.items()
            if key.startswith(LEGACY_TAG_PREFIX) and value
        }
        return tags | self._json_map(row.get("resource_tags", ""))

    def _json_map(self, value: str) -> dict[str, str]:
        """CUR 2.0 packs some columns into JSON. Bad JSON is ignored, as these are only extras."""
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
