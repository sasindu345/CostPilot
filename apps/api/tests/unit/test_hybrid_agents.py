"""Agents must run only when they add something, and can never weaken the protections."""

from decimal import Decimal

import pytest

from costpilot.modules.assistant.application.specialists import SPECIALIST_DOWN
from costpilot.modules.assistant.domain.findings import FindingDraft
from costpilot.modules.assistant.domain.guardrails import check_answer, misplaced_facts
from costpilot.modules.assistant.domain.metrics import AnswerMeter
from costpilot.modules.assistant.domain.models import Fact, Route
from costpilot.modules.assistant.domain.prompts import (
    ANOMALY_INSTRUCTIONS,
    KNOWLEDGE_INSTRUCTIONS,
    OPTIMIZATION_INSTRUCTIONS,
)
from costpilot.modules.knowledge.contracts import SearchResult
from costpilot.modules.recommendations.contracts import Recommendation
from tests.unit.test_assistant import (
    FakeAnalytics,
    FakeKnowledge,
    FakeModel,
    FakeRecommendations,
    FakeStore,
    answer_text,
    run,
    service,
)

EC2 = Fact("F1", "EC2-Instances cost", "120.00 USD", "EC2-Instances")
RDS = Fact("F2", "RDS cost", "65.00 USD", "RDS")
GP2 = Recommendation(
    "aws-gp2-to-gp3",
    "aws",
    "Move EBS gp2 volumes to gp3",
    "AWS lists gp3 at a 20 percent lower price per GiB than gp2.",
    "USD",
    Decimal("10.00"),
    "EBS General Purpose SSD volumes",
    "https://docs.test/ebs",
)


def instructions_used(model):
    return [item[0] for item in model.specialist_calls]


def test_a_number_about_another_service_is_rejected():
    assert misplaced_facts("RDS cost {{F1}}.", [EC2, RDS]) == ["F1"]


def test_a_number_in_the_right_sentence_passes():
    answer = "Your EC2 cost was {{F1}}.\n* RDS cost {{F2}}."

    assert check_answer(answer, [EC2, RDS]).passed


def test_a_fact_with_no_subject_can_go_anywhere():
    total = Fact("F3", "Total", "10 USD")

    assert misplaced_facts("Your total was {{F3}}.", [total]) == []


async def test_a_misplaced_number_never_reaches_the_user():
    model = FakeModel(chunks=("RDS cost {{F6}}.",), route=Route.ANOMALY)
    store = FakeStore()

    await run(service(model, store=store))

    assert store.last_trace["checks"]["answer_attempts"] >= 1


async def test_a_simple_cost_question_uses_no_specialist_ai():
    model = FakeModel()
    store = FakeStore()

    await run(service(model, store=store))

    assert model.specialist_calls == []


async def test_the_anomaly_agent_runs_when_something_is_unusual_with_line_detail():
    model = FakeModel(route=Route.ANOMALY)

    await run(service(model))

    assert instructions_used(model) == [ANOMALY_INSTRUCTIONS]
    assert "BoxUsage:t3.large" in model.specialist_calls[0][1]


async def test_the_anomaly_agent_gets_a_resource_count_and_no_resource_names():
    model = FakeModel(route=Route.ANOMALY)

    await run(service(model))

    assert "number of resources" in model.specialist_calls[0][1]
    assert "i-" not in model.specialist_calls[0][1]


async def test_the_anomaly_agent_is_skipped_with_summary_only_data():
    model = FakeModel(route=Route.ANOMALY)

    await run(service(model, analytics=FakeAnalytics(has_detail=False)))

    assert model.specialist_calls == []


async def test_specialists_see_facts_without_their_values():
    model = FakeModel(route=Route.ANOMALY)

    await run(service(model))

    assert "248.60" not in model.specialist_calls[0][1]


async def test_the_knowledge_agent_uses_documents_only():
    model = FakeModel(route=Route.KNOWLEDGE, chunks=("Savings Plans lower your cost.",))
    analytics = FakeAnalytics()

    await run(service(model, analytics=analytics))

    assert instructions_used(model) == [KNOWLEDGE_INSTRUCTIONS]
    assert "1,245.60" not in model.prompts[0]


async def test_a_two_part_question_retrieves_documents_only_once():
    model = FakeModel(route=[Route.OPTIMIZATION, Route.KNOWLEDGE])
    knowledge = FakeKnowledge()

    await run(service(model, knowledge=knowledge))

    assert len(knowledge.seen) == 1
    assert set(instructions_used(model)) == {OPTIMIZATION_INSTRUCTIONS, KNOWLEDGE_INSTRUCTIONS}


async def test_no_documents_means_no_document_agents():
    model = FakeModel(route=Route.KNOWLEDGE)
    knowledge = FakeKnowledge(SearchResult([], is_available=False))

    await run(service(model, knowledge=knowledge))

    assert model.specialist_calls == []


async def test_a_question_naming_a_cloud_searches_that_cloud():
    model = FakeModel(route=Route.KNOWLEDGE, providers=["azure"])
    knowledge = FakeKnowledge(SearchResult([]))

    await run(service(model, knowledge=knowledge), "How do Azure reservations work?")

    assert knowledge.seen[0][1] == ["azure"]


async def test_a_question_comparing_clouds_searches_all_of_them_at_once():
    model = FakeModel(route=Route.KNOWLEDGE, providers=["aws", "azure", "gcp"])
    knowledge = FakeKnowledge(SearchResult([]))

    await run(service(model, knowledge=knowledge), "How do Spot VMs differ across clouds?")

    assert knowledge.seen == [("How do Spot VMs differ across clouds?", ["aws", "azure", "gcp"])]


async def test_the_ai_call_limit_is_never_passed():
    model = FakeModel(route=[Route.ANOMALY, Route.OPTIMIZATION, Route.KNOWLEDGE])
    store = FakeStore()

    await run(service(model, store=store, limit=3))

    assert len(model.specialist_calls) == 1


def test_parallel_specialists_cannot_pass_the_limit_together():
    meter = AnswerMeter(ai_call_limit=4)

    assert [meter.reserve_specialist() for _ in range(3)] == [True, True, False]


async def test_a_failed_specialist_does_not_stop_the_answer():
    model = FakeModel(route=Route.OPTIMIZATION, error="specialist")

    events = await run(service(model))

    assert answer_text(events) == "Total: 248.60 USD."
    assert SPECIALIST_DOWN in model.prompts[0]


async def test_a_specialist_can_be_turned_off_in_settings():
    model = FakeModel(route=Route.ANOMALY)

    await run(service(model, agents=()))

    assert model.specialist_calls == []


async def test_an_ai_finding_with_an_invented_figure_is_dropped_before_the_final_answer():
    bad = FindingDraft(claim="You will save $500 a month", fact_ids=["F1"])
    good = FindingDraft(claim="EC2 grew in one region", fact_ids=["F1"])
    model = FakeModel(route=Route.ANOMALY, findings=[bad, good])
    store = FakeStore()

    await run(service(model, store=store))

    assert "$500" not in model.prompts[0]
    assert "EC2 grew in one region" in model.prompts[0]
    assert store.last_trace["checks"]["evidence_dropped"] == 1


async def test_an_ai_finding_citing_an_unknown_document_is_dropped():
    bad = FindingDraft(claim="Use this trick", document_urls=["https://evil.test"])
    model = FakeModel(route=Route.OPTIMIZATION, findings=[bad])

    await run(service(model))

    assert "Use this trick" not in model.prompts[0]


async def test_only_a_rule_can_state_a_saving():
    model = FakeModel(route=Route.OPTIMIZATION)
    rules = FakeRecommendations([GP2])

    await run(service(model, recommendations=rules))

    assert "Provable monthly saving" in model.prompts[0]
    assert "10.00" not in model.prompts[0]


async def test_documents_stay_available_to_the_final_answer():
    rule = Recommendation(
        "x", "aws", "Review S3", "Reason.", "USD", None, "S3", "https://docs.test/x"
    )
    model = FakeModel(route=Route.OPTIMIZATION)

    await run(service(model, recommendations=FakeRecommendations([rule])))

    assert "Use lifecycle." in model.prompts[0]


async def test_a_detailed_finding_can_stand_in_for_its_document_to_save_tokens():
    url = "https://docs.test/s3"
    claim = "Lifecycle rules move rarely read objects to cheaper storage classes over time."
    model = FakeModel(
        route=Route.OPTIMIZATION,
        findings=[FindingDraft(claim=claim, document_urls=[url])],
    )

    await run(service(model))

    assert "Use lifecycle." not in model.prompts[0]
    assert claim in model.prompts[0]


async def test_a_rule_with_no_proof_says_it_needs_usage_data():
    item = Recommendation(
        "x", "aws", "Review S3", "Reason.", "USD", None, "S3", "https://docs.test/x"
    )
    model = FakeModel(route=Route.OPTIMIZATION)

    await run(service(model, recommendations=FakeRecommendations([item])))

    assert "saving needs usage data" in model.prompts[0]


async def test_each_answer_records_its_ai_calls():
    model = FakeModel(route=Route.ANOMALY)
    store = FakeStore()

    await run(service(model, store=store))

    assert store.last_trace["metrics"]["ai_calls"] >= 1


@pytest.mark.parametrize("route", [Route.COST, Route.ANOMALY, Route.OPTIMIZATION, Route.KNOWLEDGE])
async def test_every_route_still_gives_an_answer(route):
    events = await run(service(FakeModel(route=route, chunks=("No figures needed.",))))

    assert answer_text(events)
