"""Every total below was worked out by hand from the files in tests/fixtures/billing/."""

import csv
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.readers import find_reader
from costpilot.modules.billing.domain.readers.azure_cost_details import AzureCostDetailsReader
from costpilot.modules.billing.domain.readers.digitalocean_invoice import (
    DigitalOceanInvoiceReader,
)
from costpilot.modules.billing.domain.readers.focus import FocusReader
from costpilot.modules.billing.domain.readers.gcp_billing_export import GcpBillingExportReader
from costpilot.modules.billing.domain.readers.oci_cost_report import OciCostReportReader
from costpilot.modules.billing.domain.records import ChargeCategory

FIXTURES = Path(__file__).parents[1] / "fixtures" / "billing"


def read(name):
    with (FIXTURES / name).open(encoding="utf-8", newline="") as file:
        table = list(csv.reader(file))
    reader = find_reader(table[0])
    return reader, list(reader.read(table[0], table[1:]))


def total(records, category=None):
    return sum(
        (r.billed_cost for r in records if category is None or r.charge_category is category),
        Decimal(0),
    )


@pytest.mark.parametrize(
    ("name", "reader_type"),
    [
        ("azure-ea.csv", AzureCostDetailsReader),
        ("azure-payg.csv", AzureCostDetailsReader),
        ("gcp-standard.csv", GcpBillingExportReader),
        ("oci-cost.csv", OciCostReportReader),
        ("digitalocean-invoice.csv", DigitalOceanInvoiceReader),
        ("focus-azure.csv", FocusReader),
        ("focus-gcp.csv", FocusReader),
        ("focus-oci.csv", FocusReader),
    ],
)
def test_each_file_goes_to_the_right_reader(name, reader_type):
    reader, _ = read(name)

    assert isinstance(reader, reader_type)


def test_azure_ea_total_and_details():
    _, records = read("azure-ea.csv")

    assert total(records) == Decimal("324.3000000001")
    assert total(records, ChargeCategory.PURCHASE) == Decimal("300.00")
    assert total(records, ChargeCategory.ADJUSTMENT) == Decimal("-2.50")
    first = records[0]
    assert first.provider_name == "azure"
    assert first.billing_currency == "EUR"
    assert first.service_category == "Compute"
    assert first.charge_period_start == datetime(2026, 10, 1, tzinfo=UTC)
    assert first.charge_period_end == datetime(2026, 10, 2, tzinfo=UTC)
    assert first.region_id == "westeurope"
    assert first.sku_id == "Dv5 Series: D2 v5"
    assert first.list_cost == Decimal("15.00")
    assert first.tags == {"env": "prod"}


def test_azure_reads_month_day_year_dates_correctly():
    _, records = read("azure-ea.csv")

    assert records[3].charge_period_start == datetime(2026, 10, 15, tzinfo=UTC)


def test_azure_pay_as_you_go_columns():
    _, records = read("azure-payg.csv")

    assert records[0].billed_cost == Decimal("4.00")
    assert records[0].billing_currency == "USD"
    assert records[0].region_id == "eastus"
    assert records[0].resource_id.endswith("disk-1")


def test_gcp_total_keeps_credits_as_their_own_records():
    _, records = read("gcp-standard.csv")

    assert total(records) == Decimal("19.35")
    assert total(records, ChargeCategory.CREDIT) == Decimal("-5.00")
    assert total(records, ChargeCategory.TAX) == Decimal("1.10")
    assert records[0].region_id == "us-central1"
    assert records[0].sub_account_id == "proj-a"
    assert records[0].charge_period_start == datetime(2026, 10, 1, tzinfo=UTC)


def test_oci_total_and_corrections():
    _, records = read("oci-cost.csv")

    assert total(records) == Decimal("1.315")
    assert records[2].charge_category is ChargeCategory.ADJUSTMENT
    assert records[0].service_category == "Compute"
    assert records[1].service_category == "Storage"
    assert records[0].tags == {"Oracle-Tags.CreatedBy": "ann"}


def test_digitalocean_total_with_dollar_signs_credits_and_tax():
    _, records = read("digitalocean-invoice.csv")

    assert total(records) == Decimal("977.27")
    assert records[0].billed_cost == Decimal("1024.00")
    assert total(records, ChargeCategory.CREDIT) == Decimal("-50.00")
    assert total(records, ChargeCategory.TAX) == Decimal("0.16")


def test_digitalocean_descriptions_are_kept_away_from_the_usage_type():
    """Descriptions can hold IP addresses and names, and the usage type can reach the AI."""
    _, records = read("digitalocean-invoice.csv")

    assert "203.0.113.7" not in records[1].sku_id
    assert records[1].resource_id.endswith("203.0.113.7")
    assert records[0].sku_id == "web-group"


@pytest.mark.parametrize(
    ("name", "provider", "billed", "effective"),
    [
        ("focus-azure.csv", "azure", "10.00", "8.00"),
        ("focus-gcp.csv", "gcp", "6.00", "6.00"),
        ("focus-oci.csv", "oci", "2.00", "2.00"),
    ],
)
def test_focus_files_from_three_clouds(name, provider, billed, effective):
    _, records = read(name)

    assert {record.provider_name for record in records} == {provider}
    assert total(records) == Decimal(billed)
    assert sum(r.effective_cost for r in records) == Decimal(effective)


@pytest.mark.parametrize(
    ("header", "row", "message"),
    [
        (
            "Date,MeterCategory,CostInBillingCurrency,BillingCurrency,ChargeType",
            "10/01/2026,Storage,1.00,USD,Mystery",
            "charge type",
        ),
        ("Date,MeterCategory,CostInBillingCurrency", "10/01/2026,Storage,1.00", "no currency"),
        (
            "Date,MeterCategory,CostInBillingCurrency,BillingCurrency",
            "2026/31/10,Storage,1.00,USD",
            "date",
        ),
        (
            "service.description,usage_start_time,cost,currency,cost_type",
            "Compute Engine,2026-10-01 00:00:00 UTC,1.00,USD,mystery",
            "cost type",
        ),
    ],
)
def test_bad_rows_are_refused_with_a_reason(header, row, message):
    columns = header.split(",")
    with pytest.raises(BillRejectedError, match=message):
        list(find_reader(columns).read(columns, [row.split(",")]))
