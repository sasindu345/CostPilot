"""Fail if source code contains values that belong in settings. See Rule 2 in AGENTS.md."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WEB_SOURCE = ROOT / "apps/web/src"
API_SOURCE = ROOT / "apps/api/src"
TOKEN_FILE = WEB_SOURCE / "styles/tokens.css"

TAILWIND_COLOURS = (
    "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal"
    "|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose"
)

WEB_RULES = {
    "raw colour": re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|oklch)\("),
    "built-in Tailwind colour": re.compile(rf"\b[a-z-]+-(?:{TAILWIND_COLOURS})-\d{{2,3}}\b"),
}
SHARED_RULES = {
    "hardcoded URL": re.compile(r"https?://(?!www\.w3\.org)"),
    "hardcoded AI model name": re.compile(r"[\"'`]gemini-[\w.-]+[\"'`]"),
}


def scan(folder: Path, suffixes: set[str], rules: dict[str, re.Pattern[str]]) -> list[str]:
    problems = []
    for path in sorted(folder.rglob("*")):
        if path.suffix not in suffixes or path == TOKEN_FILE:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for name, pattern in rules.items():
                if pattern.search(line):
                    relative = path.relative_to(ROOT)
                    problems.append(f"{relative}:{number}: {name}: {line.strip()}")
    return problems


def main() -> int:
    web_suffixes = {".ts", ".tsx", ".css"}
    problems = scan(WEB_SOURCE, web_suffixes, WEB_RULES | SHARED_RULES)
    problems += scan(API_SOURCE, {".py"}, SHARED_RULES)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} hardcoded value(s) found. See Rule 2 in AGENTS.md.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
