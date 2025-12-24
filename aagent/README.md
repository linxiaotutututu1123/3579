AI Agent Architect - minimal demo

Tracing & Demo

- Install deps: `pip install -r requirements.txt`
- Run demo server: `python -m aagent.cli serve`
- Visit `http://127.0.0.1:8000/generate?feature=orders` and check console — ConsoleSpanExporter will print spans.

To export to OTLP collector, set OTLP endpoint in `init_tracing(otlp_endpoint="http://collector:4317")` or via environment variable in future extensions.
