"""One reader per bill format. Order matters: the first reader that matches wins."""

from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.readers.aws_cost_explorer import AwsCostExplorerReader
from costpilot.modules.billing.domain.readers.aws_cur import AwsCurReader
from costpilot.modules.billing.domain.readers.azure_cost_details import AzureCostDetailsReader
from costpilot.modules.billing.domain.readers.base import BillReader
from costpilot.modules.billing.domain.readers.digitalocean_invoice import (
    DigitalOceanInvoiceReader,
)
from costpilot.modules.billing.domain.readers.focus import FocusReader
from costpilot.modules.billing.domain.readers.gcp_billing_export import GcpBillingExportReader
from costpilot.modules.billing.domain.readers.oci_cost_report import OciCostReportReader

# FOCUS comes first, as other clouds' FOCUS files may share some column names with their own.
READERS: tuple[BillReader, ...] = (
    FocusReader(),
    AwsCurReader(),
    AzureCostDetailsReader(),
    GcpBillingExportReader(),
    OciCostReportReader(),
    DigitalOceanInvoiceReader(),
    AwsCostExplorerReader(),
)


def find_reader(columns: list[str]) -> BillReader:
    for reader in READERS:
        if reader.matches(columns):
            return reader
    raise BillRejectedError(
        "We do not recognise this file. Please upload a FOCUS file, or a cost export from AWS, "
        "Azure, Google Cloud, Oracle Cloud or DigitalOcean."
    )
