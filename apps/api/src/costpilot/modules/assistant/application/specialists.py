"""The AI specialists. Each has one job, and sees only the evidence for that job.

If a specialist fails, or the AI call limit is reached, the Python evidence is kept, so an answer
can still be given.
"""

from collections.abc import Collection
from dataclasses import replace

import structlog

from costpilot.modules.assistant.application.ports import ChatModel
from costpilot.modules.assistant.domain.errors import ModelUnavailableError
from costpilot.modules.assistant.domain.metrics import AnswerMeter
from costpilot.modules.assistant.domain.models import Evidence, Finding
from costpilot.modules.assistant.domain.prompts import (
    ANOMALY_INSTRUCTIONS,
    KNOWLEDGE_INSTRUCTIONS,
    OPTIMIZATION_INSTRUCTIONS,
    specialist_prompt,
)

logger = structlog.get_logger()

ANOMALY = "anomaly"
OPTIMIZATION = "optimization"
KNOWLEDGE = "knowledge"
INSTRUCTIONS = {
    ANOMALY: ANOMALY_INSTRUCTIONS,
    OPTIMIZATION: OPTIMIZATION_INSTRUCTIONS,
    KNOWLEDGE: KNOWLEDGE_INSTRUCTIONS,
}
SPECIALIST_DOWN = "A specialist could not finish, so this answer has less detail."


class SpecialistAgents:
    def __init__(self, model: ChatModel, enabled: Collection[str]) -> None:
        self._model = model
        self._enabled = set(enabled)

    async def add_findings(
        self, name: str, question: str, evidence: Evidence, meter: AnswerMeter
    ) -> Evidence:
        if name not in self._enabled or not meter.reserve_specialist():
            return evidence
        prompt = specialist_prompt(question, evidence)
        try:
            with meter.step(f"{name}_agent"):
                drafts = await self._model.find_findings(INSTRUCTIONS[name], prompt, meter)
        except ModelUnavailableError:
            logger.warning("specialist_failed", specialist=name)
            return replace(evidence, limitations=[*evidence.limitations, SPECIALIST_DOWN])
        findings = [
            Finding(draft.claim, tuple(draft.fact_ids), tuple(draft.document_urls))
            for draft in drafts
        ]
        return replace(evidence, findings=[*evidence.findings, *findings])
