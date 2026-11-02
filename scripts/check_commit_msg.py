"""Reject commit messages that credit an AI tool. See Rule 4 in AGENTS.md."""

import re
import sys
from pathlib import Path

BLOCKED_LINES = re.compile(
    r"^\s*(co-authored-by:|.*generated (with|by) .*(claude|copilot|chatgpt|cursor|gemini|\bai\b))",
    re.IGNORECASE | re.MULTILINE,
)


def main() -> int:
    message = Path(sys.argv[1]).read_text(encoding="utf-8")
    without_git_comments = "\n".join(
        line for line in message.splitlines() if not line.startswith("#")
    )
    match = BLOCKED_LINES.search(without_git_comments)
    if match:
        print(f"Commit rejected: AI attribution is not allowed: {match.group(0).strip()}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
