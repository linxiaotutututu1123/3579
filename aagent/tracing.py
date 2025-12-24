"""Tracing helpers using OpenTelemetry"""

from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def init_tracing(
    service_name: str = "ai-agent-architect",
    otlp_endpoint: Optional[str] = None,
    enable_console_exporter: bool = True,
):
    """Initialize OpenTelemetry tracing.

    - otlp_endpoint: if provided, configure OTLP exporter to this endpoint.
    - console exporter is enabled by default for local debugging/demos.
    """
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    # OTLP exporter (if endpoint provided) — otherwise we'll just use console
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if enable_console_exporter:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    trace.set_tracer_provider(provider)

    # Auto-instrument common libraries
    RequestsInstrumentor().instrument()


def instrument_fastapi_app(app):
    """Instrument a FastAPI app instance."""
    FastAPIInstrumentor.instrument_app(app)
