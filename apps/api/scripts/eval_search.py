"""Measure search quality: how many test questions find an expected source?"""

import asyncio
import sys

from costpilot.composition import build_knowledge_search
from costpilot.modules.knowledge.infrastructure.yaml_files import read_questions
from costpilot.shared.config import get_settings


async def main() -> int:
    settings = get_settings()
    if not settings.gemini_api_key.get_secret_value():
        print("GEMINI_API_KEY is empty. Add it to .env. See docs/guides/getting-started.md")
        return 1
    search = build_knowledge_search(settings)
    questions = read_questions(settings.knowledge_questions_path)
    hits = 0
    for item in questions:
        result = await search.search(item.question, item.provider)
        found = {passage.source_id for passage in result.passages}
        is_hit = bool(found & set(item.expected))
        hits += is_hit
        print(f"{'PASS' if is_hit else 'MISS'}  {item.question}  ->  {sorted(found)}")
    hit_rate = hits / len(questions)
    print(f"\nHit rate: {hit_rate:.0%}. Target: {settings.search_min_hit_rate:.0%}.")
    return 0 if hit_rate >= settings.search_min_hit_rate else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
