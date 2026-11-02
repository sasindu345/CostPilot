import gzip

import pytest

from costpilot.modules.documents.domain.errors import InvalidBillFileError, UnsupportedFileError
from costpilot.modules.documents.domain.files import (
    check_file_matches_name,
    count_bill_rows,
    safe_file_name,
)

LIMIT = 10_000


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("bill.csv", "bill.csv"),
        ("BILL.CSV.GZ", "BILL.CSV.GZ"),
        ("../../etc/bill.csv", "bill.csv"),
        ("C:\\Users\\me\\bill.csv", "bill.csv"),
        ("=cmd|calc.csv", "cmd|calc.csv"),
        ("bi\x00ll\r\n.csv", "bill.csv"),
    ],
)
def test_safe_file_name(raw, expected):
    assert safe_file_name(raw) == expected


@pytest.mark.parametrize("raw", ["bill.pdf", "bill.exe", "", "csv", "bill.csv.exe"])
def test_other_file_types_are_rejected(raw):
    with pytest.raises(UnsupportedFileError):
        safe_file_name(raw)


def test_a_long_name_keeps_its_ending():
    assert safe_file_name("a" * 500 + ".csv").endswith(".csv")
    assert len(safe_file_name("a" * 500 + ".csv")) == 200


def test_gzip_name_must_hold_gzip_content():
    with pytest.raises(UnsupportedFileError):
        check_file_matches_name("bill.csv.gz", b"Service,Cost")


def test_csv_name_must_not_hold_gzip_content():
    with pytest.raises(UnsupportedFileError):
        check_file_matches_name("bill.csv", gzip.compress(b"a,b"))


def write(tmp_path, content: bytes):
    path = tmp_path / "bill"
    path.write_bytes(content)
    return path


def test_counts_rows_in_a_csv(tmp_path):
    path = write(tmp_path, b"Service,Cost\nEC2,1.00\nS3,2.00\n")

    assert count_bill_rows(path, LIMIT) == 2


def test_counts_rows_in_a_compressed_csv(tmp_path):
    path = write(tmp_path, gzip.compress(b"Service,Cost\nEC2,1.00\n"))

    assert count_bill_rows(path, LIMIT) == 1


def test_reads_a_file_that_starts_with_a_byte_order_mark(tmp_path):
    path = write(tmp_path, "Service,Cost\nEC2,1.00\n".encode("utf-8-sig"))

    assert count_bill_rows(path, LIMIT) == 1


@pytest.mark.parametrize(
    "content",
    [b"", b"just one column\n", b"Service,Cost\n", b"\xff\xfe\x00\x01,\x00", b"a,b\n1,\x00\n"],
)
def test_unreadable_tables_are_rejected(tmp_path, content):
    with pytest.raises(InvalidBillFileError):
        count_bill_rows(write(tmp_path, content), LIMIT)


def test_damaged_compressed_file_is_rejected(tmp_path):
    damaged = gzip.compress(b"Service,Cost\n" + b"EC2,1.00\n" * 1000)[:30]

    with pytest.raises(InvalidBillFileError):
        count_bill_rows(write(tmp_path, damaged), LIMIT)


def test_compressed_bomb_is_stopped(tmp_path):
    bomb = gzip.compress(b"a,b\n" + b"1,2\n" * 5_000_000)

    assert len(bomb) < 100_000
    with pytest.raises(InvalidBillFileError, match="too large"):
        count_bill_rows(write(tmp_path, bomb), LIMIT)
