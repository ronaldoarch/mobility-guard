from dataclasses import dataclass

from mobility_guard.application.ports import (
    ExplanationJobPublisher,
    ExplanationProvider,
    TransactionRepository,
)
from mobility_guard.application.use_cases import GetBillingSummary, RecordTransaction
from mobility_guard.config import Settings
from mobility_guard.domain.anomaly_detector import RuleBasedAnomalyDetector
from mobility_guard.infrastructure.explanation import OpenAIExplanationProvider
from mobility_guard.infrastructure.repository_factory import build_repository
from mobility_guard.infrastructure.task_queue import CeleryExplanationJobPublisher


@dataclass(frozen=True, slots=True)
class Container:
    repository: TransactionRepository
    record_transaction: RecordTransaction
    get_billing_summary: GetBillingSummary


def build_container(settings: Settings) -> Container:
    repository = build_repository(settings)
    explanation_provider: ExplanationProvider | None = None
    job_publisher: ExplanationJobPublisher | None = None
    if settings.async_explanation_enabled:
        job_publisher = CeleryExplanationJobPublisher()
    elif settings.openai_api_key:
        explanation_provider = OpenAIExplanationProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    detector = RuleBasedAnomalyDetector(threshold=settings.anomaly_threshold)
    return Container(
        repository=repository,
        record_transaction=RecordTransaction(
            repository,
            detector,
            explanation_provider,
            job_publisher,
        ),
        get_billing_summary=GetBillingSummary(repository),
    )
