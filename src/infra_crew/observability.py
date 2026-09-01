"""Everything the crew does is a trace in two places: the estate collector and Langfuse.

The crew will not run unless both exporters are configured (estate.load refuses first). Coverage
is proved by querying Langfuse for the run's trace, never by scanning files — see tools/langfuse.py
and the acceptance command in docs/ACCEPTANCE.md.
"""

from __future__ import annotations

import base64

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from infra_crew.estate import Estate

SERVICE_NAME = "infra-crew"


def install(estate: Estate, run_id: str) -> TracerProvider:
    """One provider, two exporters: the collector (LAW 50) and Langfuse's OTLP door."""
    provider = TracerProvider(
        resource=Resource.create({"service.name": SERVICE_NAME, "infra_crew.run_id": run_id})
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{estate.otel_endpoint.rstrip('/')}/v1/traces"))
    )
    auth = base64.b64encode(f"{estate.langfuse_public_key}:{estate.langfuse_secret_key}".encode()).decode()
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"{estate.langfuse_base_url.rstrip('/')}/api/public/otel/v1/traces",
                headers={"Authorization": f"Basic {auth}"},
            )
        )
    )
    trace.set_tracer_provider(provider)
    # crewAI spans (agents, tasks, tool calls, model calls) ride the same provider.
    from openinference.instrumentation.crewai import CrewAIInstrumentor

    CrewAIInstrumentor().instrument(tracer_provider=provider)
    return provider
