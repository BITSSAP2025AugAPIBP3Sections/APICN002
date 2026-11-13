import os

from opentelemetry import trace

TRACER_NAME = "apicn002.rag"


def setup(project: str = "apicn002-rag") -> None:
    """Register the OTEL tracer provider to export spans to Phoenix.

    Set PHOENIX_COLLECTOR_ENDPOINT to override the default localhost URL.
    If arize-phoenix-otel is not installed, tracing becomes a no-op.
    """
    try:
        from phoenix.otel import register
        register(
            project_name=project,
            endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"),
        )
    except ImportError:
        pass
