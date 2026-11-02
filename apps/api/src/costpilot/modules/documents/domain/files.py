"""Rules for uploaded files. Every file is untrusted until these checks pass."""

import csv
import gzip
import io
import unicodedata
import zlib
from pathlib import Path, PurePosixPath

from costpilot.modules.documents.domain.errors import InvalidBillFileError, UnsupportedFileError

ALLOWED_SUFFIXES = (".csv", ".csv.gz")
GZIP_MAGIC = b"\x1f\x8b"
MAX_NAME_LENGTH = 200
FORMULA_STARTS = "=+-@"
MIN_COLUMNS = 2
READ_CHUNK_BYTES = 1024 * 1024
NULL_CHARACTER = "\x00"


def safe_file_name(raw_name: str) -> str:
    """Return a name that is safe to show. It is only a label, never a storage path."""
    base = PurePosixPath(raw_name.replace("\\", "/")).name
    visible = "".join(c for c in base if unicodedata.category(c)[0] != "C").strip()
    name = visible.lstrip(FORMULA_STARTS)
    if not name.lower().endswith(ALLOWED_SUFFIXES):
        raise UnsupportedFileError
    return name[-MAX_NAME_LENGTH:]


def check_file_matches_name(file_name: str, first_bytes: bytes) -> None:
    is_gzip_name = file_name.lower().endswith(".gz")
    if is_gzip_name != first_bytes.startswith(GZIP_MAGIC):
        raise UnsupportedFileError


class _SizeLimitedStream(io.RawIOBase):
    """Stops reading once too much has come out, which defeats compressed bombs."""

    def __init__(self, stream: io.BufferedIOBase, max_bytes: int) -> None:
        self._stream = stream
        self._remaining = max_bytes

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: bytearray) -> int:
        data = self._stream.read(min(len(buffer), READ_CHUNK_BYTES))
        self._remaining -= len(data)
        if self._remaining < 0:
            raise InvalidBillFileError("This file is too large once unpacked.")
        buffer[: len(data)] = data
        return len(data)


def _open_binary(path: Path) -> io.BufferedIOBase:
    with path.open("rb") as file:
        is_gzip = file.read(len(GZIP_MAGIC)) == GZIP_MAGIC
    return gzip.open(path, "rb") if is_gzip else path.open("rb")


def count_bill_rows(path: Path, max_unpacked_bytes: int) -> int:
    """Check the file is a readable table and return its number of data rows."""
    try:
        with _open_binary(path) as binary:
            limited = io.BufferedReader(_SizeLimitedStream(binary, max_unpacked_bytes))
            text = io.TextIOWrapper(limited, encoding="utf-8-sig", newline="")
            rows = csv.reader(text)
            header = next(rows, None)
            if header is None or len(header) < MIN_COLUMNS:
                raise InvalidBillFileError("This file has no column headings.")
            row_count = 0
            for row in rows:
                if any(NULL_CHARACTER in cell for cell in row):
                    raise InvalidBillFileError("This file is not a readable CSV table.")
                row_count += 1 if row else 0
    except (csv.Error, UnicodeDecodeError) as error:
        raise InvalidBillFileError("This file is not a readable CSV table.") from error
    except (EOFError, gzip.BadGzipFile, zlib.error) as error:
        raise InvalidBillFileError("This compressed file is damaged.") from error
    if row_count == 0:
        raise InvalidBillFileError("This file has no data rows.")
    return row_count
