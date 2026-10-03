"""Celery worker for distributed claim processing.

In production, claim processing is offloaded from the FastAPI web process
to a pool of Celery workers consuming from a RabbitMQ broker. This gives:
- Horizontal scaling: add more workers to process more claims concurrently.
- Fault isolation: a stuck/crashed LLM call doesn't block the API server.
- Retry/backoff: Celery's built-in retry with exponential backoff.
- Visibility: Celery Flower dashboard for monitoring task status.

Usage:
  celery -A agentcore.worker worker --loglevel=info --pool=solo

The ``--pool=solo`` is important because the Supervisor uses asyncio
internally (asyncio.gather for parallel analysts). Celery's default
prefork pool doesn't support asyncio. For production with higher
concurrency, use ``--pool=gevent`` or run multiple solo workers.

The broker URL defaults to the same RabbitMQ instance declared in
AgentCoreSettings.rabbitmq_url. Redis is used as the result backend
so the API layer can poll task status.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from celery import Celery

from .settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Celery app configuration
celery_app = Celery(
    "claimblitz",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retry policy for broker connection issues
    broker_connection_retry_on_startup=True,
    # Result expiry (24h, matches blackboard TTL)
    result_expires=86400,
    # Task routes: all claim tasks go to the 'claims' queue
    task_routes={
        "agentcore.worker.process_claim_task": {"queue": "claims"},
    },
)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Inside an already-running loop (unlikely in worker, but safe)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@celery_app.task(
    name="agentcore.worker.process_claim_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def process_claim_task(self, *, claim_id: str, raw_text: str, file_meta: dict[str, Any] | None = None):
    """Celery task: run the full Supervisor pipeline for a claim.

    This is the production equivalent of the background task in
    ``agentcore.api.routes._process_claim_background``. The API layer
    dispatches here instead of using FastAPI BackgroundTasks when
    RabbitMQ is available.
    """
    logger.info("Processing claim %s (attempt %d)", claim_id, self.request.retries + 1)

    async def _process():
        from .api.deps import get_blackboard_dep, get_supervisor_dep
        from .protocol import ClaimStage

        supervisor = get_supervisor_dep()
        blackboard = get_blackboard_dep()

        try:
            state = await supervisor.process_claim(
                claim_id=claim_id,
                raw_text=raw_text,
                file_meta=file_meta or {},
            )
            await blackboard.set_many(claim_id, {
                "stage": state.stage.value,
                "findings_count": len(state.findings),
                "decision_steps": len(state.decision_path.steps),
            })
            await blackboard.publish_event(claim_id, {
                "type": "processing_complete",
                "stage": state.stage.value,
            })
            return {
                "claim_id": claim_id,
                "stage": state.stage.value,
                "findings": len(state.findings),
            }
        except Exception as exc:
            await blackboard.set_many(claim_id, {
                "stage": ClaimStage.FAILED.value,
                "error": str(exc),
            })
            await blackboard.publish_event(claim_id, {
                "type": "processing_failed",
                "error": str(exc),
            })
            raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Claim %s failed: %s", claim_id, exc)
        # Celery retry with exponential backoff
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


__all__ = ["celery_app", "process_claim_task"]
