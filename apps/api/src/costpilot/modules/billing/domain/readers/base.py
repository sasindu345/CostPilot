"""What every bill reader must do, plus small helpers they share."""

import json
from collections.abc import Iterable, Iterator, Sequence
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


# Clouds write dates in different ways. ISO dates are tried first.
TIME_FORMATS = ("%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S %z")


def parse_time(value: str, row_number: int, extra_formats: Sequence[str] = ()) -> datetime:
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = None
        for time_format in (*TIME_FORMATS, *extra_formats):
            try:
                parsed = datetime.strptime(text, time_format)
                break
            except ValueError:
                continue
    if parsed is None:
        raise BillRejectedError(f"Row {row_number} has a date we cannot read.")
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def parse_json_map(value: str) -> dict[str, str]:
    """Some clouds pack labels into JSON. Bad JSON is ignored, as labels are only extras."""
    text = value.strip()
    if not text:
        return {}
    for candidate in (text, f"{{{text}}}"):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return {str(key): str(item) for key, item in parsed.items()}
    return {}


def column_lookup(columns: list[str]) -> dict[str, int]:
    """Find columns whatever their case, as some clouds change it between account types."""
    return {column.strip().lower(): index for index, column in enumerate(columns)}


def cell(row: list[str], lookup: dict[str, int], *names: str) -> str:
    """The first of these columns that exists, or an empty string."""
    for name in names:
        index = lookup.get(name.lower())
        if index is not None and index < len(row):
            return row[index]
    return ""
