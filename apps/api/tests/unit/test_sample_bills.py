"""The sample bills must match the figures in the design image."""

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from costpilot.modules.billing.domain.readers import find_reader

SAMPLES = Path(__file__).parents[4] / "samples" / "output"
CUR_FILE = SAMPLES / "aws-cur2-sample-2026-10.csv"


@pytest.mark.skipif(not CUR_FILE.exists(), reason="Run `make sample` first")
def test_october_sample_totals_248_60():
    with CUR_FILE.open(encoding="utf-8", newline="") as file:
        table = list(csv.reader(file))

    records = list(find_reader(table[0]).read(table[0], table[1:]))

    assert sum(record.billed_cost for record in records) == Decimal("248.60")
