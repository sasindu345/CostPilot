"""What every bill reader must do, plus small helpers they share."""

from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.records import CostRecord

FORMULA_STARTS = "=+-@"


class BillReader(Protocol):
    """Adding a new bill format means adding one class like this, and nothing else."""

    def matches(self, columns: list[str]) -> bool:
        """Is this file mine?"""

    def read(self, columns: list[str], rows: Iterable[list[str]]) -> Iterator[CostRecord]:
        """What are its FOCUS records?"""


def clean_text(value: str) -> str:
    """Stop a bill's text from acting as a spreadsheet formula if it is exported later."""
    return value.strip().lstrip(FORMULA_STARTS).strip()


def parse_money(value: str, row_number: int) -> Decimal:
    try:
        amount = Decimal(value.strip() or "0")
    except InvalidOperation as error:
        raise BillRejectedError(f"Row {row_number} has an amount we cannot read.") from error
    if not amount.is_finite():
        raise BillRejectedError(f"Row {row_number} has an amount we cannot read.")
    return amount


def parse_optional_number(value: str, row_number: int) -> Decimal | None:
    return parse_money(value, row_number) if value.strip() else None


def parse_time(value: str, row_number: int) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as error:
        raise BillRejectedError(f"Row {row_number} has a date we cannot read.") from error
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
