"""Tests for tracing initialization"""

from opentelemetry import trace

from aagent import tracing


def test_init_tracing_sets_provider(tmp_path):
    tracing.init_tracing(
        service_name="test-service", otlp_endpoint=None, enable_console_exporter=True
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test-span") as span:
        assert span is not None
    # If no exceptions raised, basic init works
    assert trace.get_tracer_provider() is not None
