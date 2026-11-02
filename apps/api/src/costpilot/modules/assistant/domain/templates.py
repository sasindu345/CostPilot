"""A plain answer built only by code, for when the AI's answer cannot be trusted or reached."""

from costpilot.modules.assistant.domain.models import Evidence

MAX_FACTS = 6
TEMPLATE_INTRO = "I could not check a written answer, so here are the figures I can confirm:"
NO_FIGURES = "I do not have enough information to answer that."


def template_answer(evidence: Evidence) -> str:
    if not evidence.facts:
        lines = [NO_FIGURES]
    else:
        facts = evidence.facts[:MAX_FACTS]
        lines = [TEMPLATE_INTRO, *(f"- {fact.label}: {fact.value}" for fact in facts)]
    lines += evidence.limitations
    return "\n".join(lines)
