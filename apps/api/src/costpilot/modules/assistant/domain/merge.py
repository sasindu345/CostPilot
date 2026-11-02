"""Joins what parallel specialists found into one set of evidence, by plain code."""

from collections.abc import Iterable

from costpilot.modules.assistant.domain.facts import FactList
from costpilot.modules.assistant.domain.models import Evidence


def merge_evidence(results: Iterable[Evidence]) -> Evidence:
    """Keep each fact once, and give the facts new ids, so two specialists never share an id."""
    items = list(results)
    facts = FactList()
    seen: set[tuple[str, str]] = set()
    for item in items:
        for fact in item.facts:
            if (fact.label, fact.value) not in seen:
                seen.add((fact.label, fact.value))
                facts.add(fact.label, fact.value)
    return Evidence(
        routes=tuple(route for item in items for route in item.routes),
        facts=facts.facts,
        passages=list({p.url + p.text: p for item in items for p in item.passages}.values()),
        limitations=list(dict.fromkeys(text for item in items for text in item.limitations)),
    )
