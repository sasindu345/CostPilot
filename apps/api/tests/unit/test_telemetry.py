import pytest
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from costpilot.modules.assistant.infrastructure.gemini_chat_model import (
    count_tokens,
    observed_call,
)
from costpilot.modules.assistant.infrastructure.langgraph_workflow import traced
from costpilot.shared.config import Settings
from costpilot.shared.telemetry import configure_telemetry

SPANS = InMemorySpanExporter()
READER = InMemoryMetricReader()


@pytest.fixture(scope="module", autouse=True)
def providers():
    """OpenTelemetry allows one global provider per process, so these are set once."""
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(SPANS))
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(MeterProvider(metric_readers=[READER]))


def metric_points(name):
    data = READER.get_metrics_data()
    for resource in data.resource_metrics:
        for scope in resource.scope_metrics:
            for metric in scope.metrics:
                if metric.name == name:
                    return list(metric.data.data_points)
    return []


def test_telemetry_is_off_without_an_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    assert configure_telemetry(Settings(), "test") is False


async def test_each_agent_step_becomes_a_span():
    async def step(state):
        return {"done": True}

    assert await traced("cost_specialist", step)({}) == {"done": True}
    assert "agent.cost_specialist" in [span.name for span in SPANS.get_finished_spans()]


def test_a_failed_gemini_call_is_counted_and_marked():
    with pytest.raises(RuntimeError), observed_call("route"):
        raise RuntimeError("Gemini is down")

    span = next(s for s in SPANS.get_finished_spans() if s.name == "gemini.route")
    assert span.status.status_code == trace.StatusCode.ERROR
    calls = metric_points("costpilot.ai.calls")
    assert any(p.attributes == {"step": "route", "outcome": "failed"} for p in calls)


def test_tokens_are_counted_by_direction():
    count_tokens(120, 30)

    totals = {p.attributes["direction"]: p.value for p in metric_points("costpilot.ai.tokens")}
    assert totals["input"] >= 120
    assert totals["output"] >= 30
