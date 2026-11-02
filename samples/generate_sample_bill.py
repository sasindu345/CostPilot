"""Create made-up AWS bills for testing. They contain no real data.

The October figures match the design image in docs/design/.
"""

import csv
import gzip
from decimal import Decimal
from pathlib import Path

OUTPUT_FOLDER = Path(__file__).parent / "output"

SERVICES = ("EC2-Instances", "RDS", "S3", "Other")
MONTHS = {
    "2026-05-01": ("60.10", "38.20", "9.30", "24.00"),
    "2026-06-01": ("88.40", "48.00", "12.60", "31.00"),
    "2026-07-01": ("104.75", "55.25", "14.00", "41.00"),
    "2026-08-01": ("96.20", "54.30", "13.50", "36.00"),
    "2026-09-01": ("138.40", "72.00", "18.00", "42.00"),
    "2026-10-01": ("120.00", "65.00", "18.60", "45.00"),
}

CUR_COLUMNS = (
    "bill_payer_account_id",
    "line_item_usage_account_id",
    "line_item_line_item_type",
    "line_item_usage_start_date",
    "line_item_usage_end_date",
    "line_item_product_code",
    "line_item_usage_type",
    "line_item_resource_id",
    "line_item_usage_amount",
    "line_item_currency_code",
    "line_item_unblended_cost",
)
ACCOUNT = "000000000000"
CUR_PRODUCTS = {
    "EC2-Instances": ("AmazonEC2", "BoxUsage:t3.medium", "i-0sample"),
    "RDS": ("AmazonRDS", "InstanceUsage:db.t3.micro", "db-sample"),
    "S3": ("AmazonS3", "TimedStorage-ByteHrs", "sample-bucket"),
    "Other": ("AWSDataTransfer", "DataTransfer-Out-Bytes", ""),
}
DAYS_IN_OCTOBER = 31


def write_cost_explorer() -> Path:
    path = OUTPUT_FOLDER / "aws-cost-explorer-sample.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Service", *(f"{name}($)" for name in SERVICES)])
        for month, costs in MONTHS.items():
            writer.writerow([month, *costs])
    return path


def october_line_items() -> list[list[str]]:
    """One row per service per day. Daily costs add up to the exact monthly total."""
    rows = []
    monthly_costs = MONTHS["2026-10-01"]
    for service, monthly_cost in zip(SERVICES, monthly_costs, strict=True):
        product, usage_type, resource = CUR_PRODUCTS[service]
        total = Decimal(monthly_cost)
        daily = (total / DAYS_IN_OCTOBER).quantize(Decimal("0.0001"))
        for day in range(1, DAYS_IN_OCTOBER + 1):
            cost = daily if day < DAYS_IN_OCTOBER else total - daily * (DAYS_IN_OCTOBER - 1)
            end = f"2026-10-{day + 1:02d}" if day < DAYS_IN_OCTOBER else "2026-11-01"
            rows.append(
                [
                    ACCOUNT,
                    ACCOUNT,
                    "Usage",
                    f"2026-10-{day:02d}T00:00:00Z",
                    f"{end}T00:00:00Z",
                    product,
                    usage_type,
                    resource,
                    "24",
                    "USD",
                    str(cost),
                ]
            )
    return rows


def write_cur() -> list[Path]:
    plain = OUTPUT_FOLDER / "aws-cur2-sample-2026-10.csv"
    with plain.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(CUR_COLUMNS)
        writer.writerows(october_line_items())
    compressed = plain.with_suffix(".csv.gz")
    compressed.write_bytes(gzip.compress(plain.read_bytes(), mtime=0))
    return [plain, compressed]


def main() -> None:
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    for path in (write_cost_explorer(), *write_cur()):
        print(f"Created {path}")


if __name__ == "__main__":
    main()
