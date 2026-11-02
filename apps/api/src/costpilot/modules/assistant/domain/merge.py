"""Joins what parallel specialists found into one set of evidence, by plain code."""

from collections.abc import Iterable

from costpilot.modules.assistant.domain.facts import FactList
from costpilot.modules.assistant.domain.models import Evidence, Finding


def merge_evidence(results: Iterable[Evidence]) -> Evidence:
    """Keep each fact once, and give the facts new ids, so two specialists never share an id."""
    items = list(results)
    facts = FactList()
    new_ids: dict[tuple[str, str], str] = {}
    findings: list[Finding] = []
    for item in items:
        renamed: dict[str, str] = {}
        for fact in item.facts:
            key = (fact.label, fact.value)
            if key not in new_ids:
                new_ids[key] = facts.add(fact.label, fact.value)
            renamed[fact.id] = new_ids[key]
        for finding in item.findings:
            ids = tuple(renamed.get(fact_id, fact_id) for fact_id in finding.fact_ids)
            findings.append(Finding(finding.claim, ids, finding.document_urls))
    return Evidence(
        routes=tuple(route for item in items for route in item.routes),
        facts=facts.facts,
        passages=list({p.url + p.text: p for item in items for p in item.passages}.values()),
        limitations=list(dict.fromkeys(text for item in items for text in item.limitations)),
        findings=list(dict.fromkeys(findings)),
    )
