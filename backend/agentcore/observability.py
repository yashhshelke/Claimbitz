"""Observability instrumentation: OpenTelemetry traces, Prometheus metrics, Sentry errors.

Call ``setup_observability(app)`` during FastAPI startup to wire everything in.
All configuration reads from ``AgentCoreSettings`` (env vars):
- OTEL_EXPORTER_OTLP_ENDPOINT — if set, traces are exported via OTLP.
- SENTRY_DSN — if set, Sentry captures unhandled exceptions.
- PROMETHEUS_ENABLED — if true (default), /metrics endpoint is exposed.

Designed to be no-op-safe: if an env var is empty, that subsystem is simply
not activated (no import errors, no crashes).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

from .settings import get_settings

logger = logging.getLogger(__name__)


def setup_observability(app: FastAPI) -> None:
    """Wire observability into the FastAPI app. Call once at startup."""
    settings = get_settings()

    # -- Prometheus metrics --
    if settings.prometheus_enabled:
        try:
            from prometheus_fastapi_instrumentator import Instrumentator

            Instrumentator(
                should_group_status_codes=True,
                should_ignore_untemplated=True,
                excluded_handlers=["/v2/health", "/metrics"],
            ).instrument(app).expose(app, endpoint="/metrics")
            logger.info("Prometheus metrics enabled at /metrics")
        except ImportError:
            logger.warning("prometheus-fastapi-instrumentator not installed, metrics disabled")

    # -- OpenTelemetry tracing --
    if settings.otel_exporter_otlp_endpoint:
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create({"service.name": "claimblitz-api", "service.version": "2.0.0"})
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)

            FastAPIInstrumentor.instrument_app(app)
            logger.info("OpenTelemetry tracing enabled -> %s", settings.otel_exporter_otlp_endpoint)
        except ImportError:
            logger.warning("OpenTelemetry packages not installed, tracing disabled")

    # -- Sentry error tracking --
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.starlette import StarletteIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.environment,
                traces_sample_rate=0.1 if settings.is_production else 1.0,
                integrations=[StarletteIntegration(), FastApiIntegration()],
                send_default_pii=False,  # PII masking: never send patient data to Sentry
            )
            logger.info("Sentry error tracking enabled")
        except ImportError:
            logger.warning("sentry-sdk not installed, error tracking disabled")


__all__ = ["setup_observability"]
