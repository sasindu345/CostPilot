"""Totals here are worked out by hand, so they prove the readers are right."""

import csv
import io
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.readers import find_reader
from costpilot.modules.billing.domain.readers.aws_cost_explorer import AwsCostExplorerReader
from costpilot.modules.billing.domain.readers.aws_cur import AwsCurReader, normalise_column
from costpilot.modules.billing.domain.readers.focus import FocusReader
from costpilot.modules.billing.domain.records import ChargeCategory, DetailLevel


def read(text: str):
    table = list(csv.reader(io.StringIO(text)))
    columns, rows = table[0], table[1:]
    return list(find_reader(columns).read(columns, rows))


def total_billed(records):
    return sum((record.billed_cost for record in records), Decimal(0))


def total_effective(records):
    return sum((record.effective_cost for record in records), Decimal(0))


COST_EXPLORER = """Service,EC2-Instances($),RDS($),S3($),Total costs($)
Service total,258.40,137.00,36.60,432.00
2026-09-01,138.40,72.00,18.00,228.40
2026-10-01,120.00,65.00,18.60,203.60
"""


def test_cost_explorer_gives_exact_totals_and_ignores_summary_lines():
    records = read(COST_EXPLORER)

    assert total_billed(records) == Decimal("432.00")
    assert len(records) == 6


def test_cost_explorer_marks_records_as_summary_detail():
    record = read(COST_EXPLORER)[0]

    assert record.provider_name == "aws"
    assert record.detail_level is DetailLevel.SERVICE_MONTH
    assert record.billing_currency == "USD"
    assert record.service_category == "Compute"
    assert record.charge_period_start == datetime(2026, 9, 1, tzinfo=UTC)
    assert record.charge_period_end == datetime(2026, 10, 1, tzinfo=UTC)


def test_cost_explorer_understands_daily_files():
    records = read("Service,S3($)\n2026-10-01,1.00\n2026-10-02,2.00\n")

    assert records[0].charge_period_end == datetime(2026, 10, 2, tzinfo=UTC)


def test_cost_explorer_handles_december():
    records = read("Service,S3($)\n2026-12-01,1.00\n")

    assert records[0].charge_period_end == datetime(2027, 1, 1, tzinfo=UTC)


NEW_CUR_HEADER = (
    "bill_payer_account_id,line_item_usage_account_id,line_item_line_item_type,"
    "line_item_usage_start_date,line_item_usage_end_date,line_item_product_code,"
    "line_item_usage_type,line_item_resource_id,line_item_usage_amount,"
    "line_item_currency_code,line_item_unblended_cost,pricing_public_on_demand_cost,"
    "pricing_unit,product,resource_tags,savings_plan_savings_plan_effective_cost,"
    "savings_plan_total_commitment_to_date,savings_plan_used_commitment,"
    "reservation_effective_cost,reservation_unused_amortized_upfront_fee_for_billing_period,"
    "reservation_unused_recurring_fee"
)
TIMES = "2026-10-01T00:00:00Z,2026-10-02T00:00:00Z"


def cur_row(line_type, cost, *, product="AmazonEC2", extras=",,,,,,"):
    return (
        f"111,222,{line_type},{TIMES},{product},BoxUsage:t3.micro,i-1,24,USD,{cost},12.00,Hrs,"
        f'"{{""region"":""us-east-1""}}","{{""team"":""web""}}"{extras}'
    )


def cur_bill(*rows):
    return "\n".join((NEW_CUR_HEADER, *rows)) + "\n"


def test_new_cur_reads_every_detail():
    record = read(cur_bill(cur_row("Usage", "10.50")))[0]

    assert record.billed_cost == Decimal("10.50")
    assert record.effective_cost == Decimal("10.50")
    assert record.list_cost == Decimal("12.00")
    assert record.billing_account_id == "111"
    assert record.sub_account_id == "222"
    assert record.region_id == "us-east-1"
    assert record.resource_id == "i-1"
    assert record.sku_id == "BoxUsage:t3.micro"
    assert record.consumed_quantity == Decimal(24)
    assert record.consumed_unit == "Hrs"
    assert record.tags == {"team": "web"}
    assert record.detail_level is DetailLevel.LINE_ITEM


def test_old_cur_columns_give_the_same_result():
    text = (
        "bill/PayerAccountId,lineItem/UsageAccountId,lineItem/LineItemType,"
        "lineItem/UsageStartDate,lineItem/UsageEndDate,lineItem/ProductCode,"
        "lineItem/UsageType,lineItem/ResourceId,lineItem/UsageAmount,"
        "lineItem/CurrencyCode,lineItem/UnblendedCost,pricing/publicOnDemandCost,"
        "pricing/unit,product/region,resourceTags/user:team\n"
        f"111,222,Usage,{TIMES},AmazonEC2,BoxUsage:t3.micro,i-1,24,USD,10.50,12.00,Hrs,"
        "us-east-1,web\n"
    )

    old = read(text)[0]
    new = read(cur_bill(cur_row("Usage", "10.50")))[0]

    assert old == new


@pytest.mark.parametrize(
    ("column", "expected"),
    [
        ("lineItem/UnblendedCost", "line_item_unblended_cost"),
        ("lineItem/LineItemType", "line_item_line_item_type"),
        ("bill/PayerAccountId", "bill_payer_account_id"),
        ("pricing/publicOnDemandCost", "pricing_public_on_demand_cost"),
        ("line_item_unblended_cost", "line_item_unblended_cost"),
    ],
)
def test_column_names_are_normalised(column, expected):
    assert normalise_column(column) == expected


@pytest.mark.parametrize(
    ("line_type", "category"),
    [
        ("Usage", ChargeCategory.USAGE),
        ("Tax", ChargeCategory.TAX),
        ("Credit", ChargeCategory.CREDIT),
        ("Refund", ChargeCategory.ADJUSTMENT),
        ("Fee", ChargeCategory.PURCHASE),
        ("RIFee", ChargeCategory.PURCHASE),
    ],
)
def test_charge_types_are_kept_apart(line_type, category):
    assert read(cur_bill(cur_row(line_type, "1.00")))[0].charge_category is category


def test_credits_reduce_the_total():
    records = read(cur_bill(cur_row("Usage", "10.00"), cur_row("Credit", "-4.00")))

    assert total_billed(records) == Decimal("6.00")


def test_savings_plan_bill_is_worked_out_by_hand():
    """A $7 plan covers $10 of usage. The invoice is $7, and the true usage cost is also $7."""
    records = read(
        cur_bill(
            cur_row("SavingsPlanCoveredUsage", "10.00", extras=",7.00,,,,,"),
            cur_row("SavingsPlanNegation", "-10.00"),
            cur_row("SavingsPlanRecurringFee", "7.00", extras=",,7.00,7.00,,,"),
        )
    )

    assert total_billed(records) == Decimal("7.00")
    assert total_effective(records) == Decimal("7.00")


def test_unused_savings_plan_commitment_counts_as_a_real_cost():
    records = read(cur_bill(cur_row("SavingsPlanRecurringFee", "7.00", extras=",,7.00,5.00,,,")))

    assert total_effective(records) == Decimal("2.00")


def test_reserved_instance_usage_uses_its_effective_cost():
    records = read(
        cur_bill(
            cur_row("DiscountedUsage", "0.00", extras=",,,,3.50,,"),
            cur_row("RIFee", "30.00", extras=",,,,,1.25,0.75"),
        )
    )

    assert total_billed(records) == Decimal("30.00")
    assert total_effective(records) == Decimal("5.50")


def test_amounts_stay_exact_at_many_decimal_places():
    records = read(
        cur_bill(*[cur_row("Usage", "0.0000000001") for _ in range(3)], cur_row("Usage", "0.1"))
    )

    assert total_billed(records) == Decimal("0.1000000003")


def test_formula_tricks_in_text_are_removed():
    record = read(cur_bill(cur_row("Usage", "1.00", product='=HYPERLINK("x")')))[0]

    assert not record.service_name.startswith("=")


FOCUS_BILL = """BilledCost,EffectiveCost,ListCost,ChargePeriodStart,ChargePeriodEnd,ChargeCategory,ServiceName,ServiceCategory,BillingCurrency,ServiceProviderName,BillingAccountId,SubAccountId,RegionId,ResourceId,SkuId,ConsumedQuantity,ConsumedUnit,Tags
5.00,4.00,6.00,2026-10-01T00:00:00Z,2026-10-02T00:00:00Z,Usage,Virtual Machines,Compute,USD,Microsoft,acct,sub,eastus,vm-1,sku-1,1,Hours,"{""team"":""web""}"
-1.00,-1.00,,2026-10-01T00:00:00Z,2026-10-02T00:00:00Z,Credit,,,USD,Microsoft,acct,sub,,,,,,
"""


def test_focus_file_from_another_cloud():
    records = read(FOCUS_BILL)

    assert records[0].provider_name == "azure"
    assert records[0].service_category == "Compute"
    assert records[0].tags == {"team": "web"}
    assert total_billed(records) == Decimal("4.00")
    assert total_effective(records) == Decimal("3.00")
    assert records[1].charge_category is ChargeCategory.CREDIT


def test_each_format_goes_to_its_own_reader():
    assert isinstance(find_reader(["Service", "S3($)"]), AwsCostExplorerReader)
    assert isinstance(find_reader(NEW_CUR_HEADER.split(",")), AwsCurReader)
    assert isinstance(find_reader(FOCUS_BILL.split("\n")[0].split(",")), FocusReader)


def test_unknown_file_is_refused_with_a_helpful_message():
    with pytest.raises(BillRejectedError, match="do not recognise"):
        find_reader(["name", "age"])


@pytest.mark.parametrize(
    ("bill", "message"),
    [
        (cur_bill(cur_row("Usage", "abc")), "Row 2 has an amount"),
        (cur_bill(cur_row("Usage", "NaN")), "Row 2 has an amount"),
        (cur_bill(cur_row("Usage", "Infinity")), "Row 2 has an amount"),
        (cur_bill(cur_row("Mystery", "1.00")), "Row 2 has a charge type"),
        ("Service,S3($)\nnot-a-date,1.00\n", "Row 2 has a date"),
    ],
)
def test_bad_rows_are_refused_with_the_row_number(bill, message):
    with pytest.raises(BillRejectedError, match=message):
        read(bill)
