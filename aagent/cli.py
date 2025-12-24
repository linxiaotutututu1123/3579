"""CLI for AI Agent Architect (minimal)"""
import typer
import uvicorn
from pathlib import Path
from aagent.spec_engine import render_design

app = typer.Typer()


@app.command()
def gen(feature: str, lang: str = "zh", output: str = None):
    """Generate a design.md for a feature."""
    out = Path(output) if output else None
    path = render_design(feature=feature, lang=lang, output=out)
    typer.echo(f"Generated: {path}")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000):
    """Run demo server (instrumented)."""
    uvicorn.run("aagent.server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
