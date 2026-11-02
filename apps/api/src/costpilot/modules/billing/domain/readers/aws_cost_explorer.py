"""Reads the CSV you can download from AWS Cost Explorer: one column per service."""

import calendar
import re
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta

from costpilot.modules.billing.domain.errors import BillRejectedError
from costpilot.modules.billing.domain.readers.aws_services import service_category
from costpilot.modules.billing.domain.readers.base import clean_text, parse_money, parse_time
from costpilot.modules.billing.domain.records import ChargeCategory, CostRecord, DetailLevel

PROVIDER = "aws"
DATE_COLUMN = "Service"
SUMMARY_ROW = "Service total"
TOTAL_COLUMN = "Total costs"
COST_COLUMN = re.compile(r"^(?P<service>.+)\((?P<symbol>[^)]+)\)$")
CURRENCY_BY_SYMBOL = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
FIRST_RECORD_ROW = 2


class AwsCostExplorerReader:
    def matches(self, columns: list[str]) -> bool:
        return (
            bool(columns)
            and columns[0].strip() == DATE_COLUMN
            and any(COST_COLUMN.match(column.strip()) for column in columns[1:])
        )

    def read(self, columns: list[str], rows: Iterable[list[str]]) -> Iterator[CostRecord]:
        services = [self._parse_column(column) for column in columns[1:]]
        data = [
            (number, row)
            for number, row in enumerate(rows, start=FIRST_RECORD_ROW)
            if row and row[0].strip() != SUMMARY_ROW
        ]
        is_monthly = all(parse_time(row[0], number).day == 1 for number, row in data)
        for number, row in data:
            start = parse_time(row[0], number)
            end = self._period_end(start, is_monthly)
            for (service, currency), value in zip(services, row[1:], strict=False):
                if service is None:
                    continue
                cost = parse_money(value, number)
                if cost == 0:
                    continue
                yield CostRecord(
                    provider_name=PROVIDER,
                    charge_period_start=start,
                    charge_period_end=end,
                    service_name=service,
                    service_category=service_category(service),
                    charge_category=ChargeCategory.USAGE,
                    billed_cost=cost,
                    effective_cost=cost,
                    billing_currency=currency,
                    detail_level=DetailLevel.SERVICE_MONTH,
                )

    def _parse_column(self, column: str) -> tuple[str | None, str]:
        match = COST_COLUMN.match(column.strip())
        if match is None:
            raise BillRejectedError(f"We do not recognise the column '{clean_text(column)}'.")
        service = clean_text(match["service"])
        currency = CURRENCY_BY_SYMBOL.get(match["symbol"], match["symbol"].strip().upper())
        return (None if service == TOTAL_COLUMN else service), currency

    def _period_end(self, start: datetime, is_monthly: bool) -> datetime:
        if not is_monthly:
            return start + timedelta(days=1)
        days = calendar.monthrange(start.year, start.month)[1]
        return datetime(start.year, start.month, days, tzinfo=UTC) + timedelta(days=1)
