"""One reader per bill format. Order matters: the first reader that matches wins."""

from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.readers.aws_cost_explorer import AwsCostExplorerReader
from costpilot.modules.billing.domain.readers.aws_cur import AwsCurReader
from costpilot.modules.billing.domain.readers.base import BillReader
from costpilot.modules.billing.domain.readers.focus import FocusReader

READERS: tuple[BillReader, ...] = (FocusReader(), AwsCurReader(), AwsCostExplorerReader())


def find_reader(columns: list[str]) -> BillReader:
    for reader in READERS:
        if reader.matches(columns):
            return reader
    raise BillRejectedError(
        "We do not recognise this file. Please upload an AWS Cost Explorer, "
        "Cost and Usage Report or FOCUS file."
    )
