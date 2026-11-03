"""OpenTelemetry: traces and metrics, sent to any OTLP receiver.

Off unless OTEL_EXPORTER_OTLP_ENDPOINT is set. Locally that is Grafana's all-in-one image
(`make monitoring`). In production it is Grafana Cloud. The exporters read the standard
OTEL_EXPORTER_OTLP_* variables themselves, including the login header.
"""

import os

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy.ext.asyncio import AsyncEngine

from costpilot.shared.config import Settings

# Health checks run every few seconds and would bury the real requests.
UNTRACED_URLS = "api/health"


def configure_telemetry(settings: Settings, service: str) -> bool:
    """Returns True when telemetry is switched on."""
    if not settings.otel_exporter_otlp_endpoint:
        return False
    # The newer HTTP names label requests by route, such as /api/documents/{document_id},
    # rather than by each address, which would make a new series for every document.
    os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http")
    resource = Resource.create(
        {"service.name": service, "deployment.environment.name": settings.app_env}
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(), export_interval_millis=settings.otel_metric_interval_seconds * 1000
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    return True


def instrument_app(app: FastAPI) -> None:
    FastAPIInstrumentor.instrument_app(app, excluded_urls=UNTRACED_URLS)


def instrument_database(engine: AsyncEngine) -> None:
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
