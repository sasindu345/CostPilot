"""The format every specialist's findings use, and the check they pass before the final answer."""

from dataclasses import replace

from pydantic import BaseModel, Field

from costpilot.modules.assistant.domain.guardrails import looks_like_injection, typed_numbers
from costpilot.modules.assistant.domain.models import Evidence, Finding

MAX_CLAIM_LENGTH = 300


class FindingDraft(BaseModel):
    """What a specialist may say. Phase 8's AI agents must return exactly this."""

    claim: str = Field(min_length=1, max_length=MAX_CLAIM_LENGTH)
    fact_ids: list[str] = Field(default_factory=list)
    document_urls: list[str] = Field(default_factory=list)


def is_supported(finding: Finding, known_facts: set[str], known_urls: set[str]) -> bool:
    has_support = bool(finding.fact_ids or finding.document_urls)
    return (
        has_support
        and set(finding.fact_ids) <= known_facts
        and set(finding.document_urls) <= known_urls
        and not typed_numbers(finding.claim)
        and not looks_like_injection(finding.claim)
    )


def validate_evidence(evidence: Evidence) -> tuple[Evidence, int]:
    """Keep only what can be proven. Return the clean evidence and how many items were dropped."""
    passages = [item for item in evidence.passages if not looks_like_injection(item.text)]
    known_facts = {fact.id for fact in evidence.facts}
    known_urls = {item.url for item in passages}
    findings = [item for item in evidence.findings if is_supported(item, known_facts, known_urls)]
    dropped = len(evidence.passages) - len(passages) + len(evidence.findings) - len(findings)
    return replace(evidence, passages=passages, findings=findings), dropped
