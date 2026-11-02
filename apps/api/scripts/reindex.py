"""Build the documentation search. Run with `make reindex`."""

import asyncio
import sys

from costpilot.composition import build_knowledge_indexer
from costpilot.modules.knowledge.infrastructure.yaml_files import read_sources
from costpilot.shared.config import get_settings


async def main() -> int:
    settings = get_settings()
    if not settings.gemini_api_key.get_secret_value():
        print("GEMINI_API_KEY is empty. Add it to .env. See docs/guides/getting-started.md")
        return 1
    sources = read_sources(settings.knowledge_sources_path)
    report = await build_knowledge_indexer(settings).run(sources)
    print(f"Indexed:   {len(report.indexed)}")
    print(f"Unchanged: {len(report.unchanged)}")
    print(f"Removed:   {len(report.removed)}")
    print(f"Failed:    {len(report.failed)} {report.failed or ''}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
