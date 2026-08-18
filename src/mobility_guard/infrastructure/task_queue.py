from __future__ import annotations

import logging

from celery import Celery  # type: ignore[import-untyped]

from mobility_guard.config import Settings, get_settings
from mobility_guard.domain.models import EnrichmentStatus
from mobility_guard.infrastructure.explanation import (
    OpenAIExplanationProvider,
    TemplateExplanationProvider,
)
from mobility_guard.infrastructure.repository_factory import build_repository

logger = logging.getLogger(__name__)

_settings = get_settings()
celery_app = Celery(
    "mobility_guard",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
)


class CeleryExplanationJobPublisher:
    def publish(self, external_id: str) -> None:
        enhance_explanation.delay(external_id)


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    name="mobility_guard.enhance_explanation",
)
def enhance_explanation(task: object, external_id: str) -> None:
    del task
    settings = Settings()
    repository = build_repository(settings)
    item = None
    try:
        item = repository.get_by_external_id(external_id)
        if item is None:
            logger.warning("transaction_not_found external_id=%s", external_id)
            return
        provider = (
            OpenAIExplanationProvider(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
            if settings.openai_api_key
            else TemplateExplanationProvider()
        )
        explanation = provider.explain(item.transaction, item.analysis)
        repository.update_enrichment(
            external_id,
            explanation=explanation,
            status=EnrichmentStatus.COMPLETED,
        )
    except Exception:
        if item is not None:
            repository.update_enrichment(
                external_id,
                explanation=item.analysis.explanation,
                status=EnrichmentStatus.FAILED,
            )
        raise
    finally:
        repository.close()
