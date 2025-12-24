"""Minimal FastAPI demo server with tracing instrumentation"""

from fastapi import FastAPI

from aagent.tracing import init_tracing, instrument_fastapi_app

app = FastAPI()

# Initialize tracing (console exporter by default)
init_tracing(
    service_name="ai-agent-architect-demo",
    otlp_endpoint=None,
    enable_console_exporter=True,
)
instrument_fastapi_app(app)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/generate")
def generate_demo(feature: str = "orders"):
    # Example span is automatically created by instrumentation
    return {
        "feature": feature,
        "message": "This is a demo response. Replace with real generation logic.",
    }
