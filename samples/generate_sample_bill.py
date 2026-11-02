"""Create a made-up AWS Cost Explorer bill for testing. It contains no real data.

The October figures match the design image in docs/design/.
"""

import csv
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "output" / "aws-cost-explorer-sample.csv"

SERVICES = ("EC2-Instances", "RDS", "S3", "Other")
MONTHS = {
    "2026-05-01": ("60.10", "38.20", "9.30", "24.00"),
    "2026-06-01": ("88.40", "48.00", "12.60", "31.00"),
    "2026-07-01": ("104.75", "55.25", "14.00", "41.00"),
    "2026-08-01": ("96.20", "54.30", "13.50", "36.00"),
    "2026-09-01": ("138.40", "72.00", "18.00", "42.00"),
    "2026-10-01": ("120.00", "65.00", "18.60", "45.00"),
}


def main() -> None:
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Service", *(f"{name}($)" for name in SERVICES)])
        for month, costs in MONTHS.items():
            writer.writerow([month, *costs])
    print(f"Created {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
