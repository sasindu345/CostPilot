"""Evidence grades, given by code. The AI's own confidence is never used."""

from enum import StrEnum

from costpilot.modules.assistant.domain.models import Evidence, Route


class Grade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


def needs_documents(evidence: Evidence) -> bool:
    return Route.OPTIMIZATION in evidence.routes


def grade_answer(
    evidence: Evidence, *, used_template: bool, has_line_detail: bool, used_evidence: bool = True
) -> Grade:
    """A: full evidence. B: a small gap. C: limited evidence. D: not enough to answer."""
    if not used_evidence or (not evidence.facts and not evidence.passages):
        return Grade.D
    needs_detail = Route.ANOMALY in evidence.routes
    if used_template or (needs_detail and not has_line_detail):
        return Grade.C
    if needs_documents(evidence) and not evidence.passages:
        return Grade.C
    return Grade.B if evidence.limitations else Grade.A
