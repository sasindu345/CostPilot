"""Score the whole assistant with real Gemini, and save the result.

Run with `make eval-assistant` or `make eval-agents`. It stops early if Gemini fails, because a
score made during an outage would be misleading.

Usage: eval_assistant.py <questions.yaml> <bill.csv> <output.json>
"""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from uuid import uuid4

import yaml
from sqlalchemy import text

from costpilot.composition import build_assistant_service, build_bill_importer
from costpilot.modules.assistant.application.assistant_service import MODEL_DOWN_ANSWER
from costpilot.modules.documents.domain.files import open_bill_table
from costpilot.modules.documents.domain.models import Document, DocumentStatus
from costpilot.modules.documents.infrastructure.postgres_repository import (
    PostgresDocumentRepository,
)
from costpilot.modules.identity.domain.models import VerifiedIdentity
from costpilot.modules.identity.infrastructure.postgres_repository import (
    PostgresIdentityRepository,
)
from costpilot.shared.config import get_settings
from costpilot.shared.database import Database

PAUSE_SECONDS = 6
MAX_BILL_BYTES = 10_000_000


async def sample_user(database, bill: Path):
    subject = str(uuid4())
    user, _ = await PostgresIdentityRepository(database).save_identity(
        VerifiedIdentity(subject, f"{subject}@example.test", "Eval", "token")
    )
    document_id = uuid4()
    await PostgresDocumentRepository(database).create_with_job(
        Document(
            document_id,
            user.workspace_id,
            user.user_id,
            bill.name,
            "eval",
            1,
            subject,
            DocumentStatus.PROCESSED,
            datetime.now(UTC),
        )
    )
    async with database.transaction() as db:
        await db.execute(text("DELETE FROM jobs WHERE document_id = :id"), {"id": document_id})
    importer = build_bill_importer(get_settings(), database)
    with open_bill_table(bill, MAX_BILL_BYTES) as (columns, rows):
        await importer.import_bill(user.workspace_id, document_id, columns, rows)
    await importer.refresh(user.workspace_id)
    return user


def score(item: dict, answer: str, sources: list[str], trace: dict) -> dict[str, bool]:
    lowered = answer.lower()
    expected = set(item.get("routes", []))
    routes = set(trace.get("routes", []))
    return {
        "route": "routes" not in item or (routes <= expected if expected else not routes),
        "include": all(word.lower() in lowered for word in item.get("include", [])),
        "exclude": not any(word.lower() in lowered for word in item.get("exclude", [])),
        "source": not item.get("sources") or bool(set(item["sources"]) & set(sources)),
    }


async def main() -> int:
    settings = get_settings()
    if not settings.gemini_api_key.get_secret_value():
        print("GEMINI_API_KEY is empty. Add it to .env.")
        return 1
    database = Database(settings.app_database_url)
    questions_path, bill, output = (Path(item) for item in sys.argv[1:4])
    user = await sample_user(database, bill)
    assistant = build_assistant_service(settings, database)
    questions = yaml.safe_load(questions_path.read_text())["questions"]
    results = []
    for number, item in enumerate(questions, start=1):
        chat = await assistant.start_conversation(user)
        await assistant.prepare_question(user, chat.id, item["question"])
        answer = ""
        sources: list[str] = []
        async for event in assistant.answer(user, chat.id, item["question"]):
            if event.type == "text":
                answer += event.text
            if event.type == "done":
                sources = [source.title for source in event.sources]
        if answer == MODEL_DOWN_ANSWER:
            print(f"\nSTOPPED at question {number}: Gemini failed. Check the logs for the reason.")
            await database.close()
            return 2
        messages = await assistant.messages(user, chat.id)
        trace = messages[-1].trace
        checks = score(item, answer, sources, trace)
        metrics = trace.get("metrics", {})
        passed = all(checks.values())
        failed = [name for name, value in checks.items() if not value]
        print(
            f"{'PASS' if passed else 'FAIL ' + ','.join(failed)}  "
            f"grade={messages[-1].grade}  calls={metrics.get('ai_calls')}  "
            f"{metrics.get('total_ms')}ms  {item['question']}\n    {metrics.get('step_ms')}"
        )
        results.append(
            {
                "question": item["question"],
                "answer": answer,
                "passed": passed,
                "failed": failed,
                "grade": messages[-1].grade,
                "routes": trace.get("routes"),
                "used_template": trace.get("checks", {}).get("used_template", False),
                "metrics": metrics,
            }
        )
        await asyncio.sleep(PAUSE_SECONDS)
    await database.close()

    measured = [item["metrics"] for item in results if item["metrics"].get("ai_calls")]
    summary = {
        "measured_on": datetime.now(UTC).date().isoformat(),
        "answer_model": settings.gemini_answer_model,
        "ai_specialists": list(settings.assistant_ai_specialists),
        "questions": len(results),
        "passed": sum(item["passed"] for item in results),
        "used_template": sum(item["used_template"] for item in results),
        "average_ai_calls": round(mean(m["ai_calls"] for m in measured), 2),
        "average_input_tokens": round(mean(m["input_tokens"] for m in measured)),
        "average_output_tokens": round(mean(m["output_tokens"] for m in measured)),
        "average_ms": round(mean(m["total_ms"] for m in measured)),
    }
    output.write_text(json.dumps({"summary": summary, "results": results}, indent=2) + "\n")
    print(f"\n{json.dumps(summary, indent=2)}\nSaved to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
