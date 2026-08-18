from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from decimal import Decimal
from statistics import median

from mobility_guard.domain.models import (
    AnomalyAnalysis,
    AnomalyKind,
    AnomalyReason,
    StoredTransaction,
    Transaction,
)


class RuleBasedAnomalyDetector:
    """Explainable baseline using robust statistics and deterministic rules."""

    def __init__(self, threshold: float = 0.65) -> None:
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        self._threshold = threshold

    def analyze(
        self, transaction: Transaction, history: list[StoredTransaction]
    ) -> AnomalyAnalysis:
        reasons: list[AnomalyReason] = []

        duplicate = self._find_possible_duplicate(transaction, history)
        if duplicate is not None:
            reasons.append(
                AnomalyReason(
                    kind=AnomalyKind.POSSIBLE_DUPLICATE,
                    weight=0.82,
                    message=(
                        "Existe uma cobrança semelhante no mesmo estabelecimento "
                        f"há menos de 5 minutos ({duplicate.transaction.external_id})."
                    ),
                )
            )

        amount_weight = self._amount_anomaly_weight(transaction.amount, history)
        if amount_weight > 0:
            reasons.append(
                AnomalyReason(
                    kind=AnomalyKind.HIGH_AMOUNT,
                    weight=amount_weight,
                    message=(
                        "O valor está significativamente acima do histórico recente do cliente."
                    ),
                )
            )

        local_hour = transaction.occurred_at.hour
        if 0 <= local_hour < 5:
            reasons.append(
                AnomalyReason(
                    kind=AnomalyKind.UNUSUAL_HOUR,
                    weight=0.25,
                    message="A transação ocorreu em um horário pouco usual, entre 00h e 05h.",
                )
            )

        if len(history) < 3 and not reasons:
            reasons.append(
                AnomalyReason(
                    kind=AnomalyKind.INSUFFICIENT_HISTORY,
                    weight=0.0,
                    message="Ainda não há histórico suficiente para uma comparação robusta.",
                )
            )

        score = self._combine_weights(reason.weight for reason in reasons)
        explanation = self._fallback_explanation(score, reasons)
        return AnomalyAnalysis(
            score=score,
            threshold=self._threshold,
            reasons=tuple(reasons),
            explanation=explanation,
        )

    @staticmethod
    def _find_possible_duplicate(
        transaction: Transaction, history: list[StoredTransaction]
    ) -> StoredTransaction | None:
        for item in reversed(history):
            previous = item.transaction
            elapsed = abs(transaction.occurred_at_utc - previous.occurred_at_utc)
            if (
                previous.merchant.casefold() == transaction.merchant.casefold()
                and previous.amount == transaction.amount
                and elapsed <= timedelta(minutes=5)
            ):
                return item
        return None

    @staticmethod
    def _amount_anomaly_weight(
        amount: Decimal, history: list[StoredTransaction]
    ) -> float:
        if len(history) < 3:
            return 0.0

        amounts = [float(item.transaction.amount) for item in history[-30:]]
        center = median(amounts)
        deviations = [abs(value - center) for value in amounts]
        mad = median(deviations)
        value = float(amount)

        if mad == 0:
            ratio = value / center if center > 0 else 1.0
            if ratio >= 3:
                return 0.72
            if ratio >= 2:
                return 0.55
            return 0.0

        robust_z = 0.6745 * (value - center) / mad
        if robust_z >= 8:
            return 0.78
        if robust_z >= 5:
            return 0.68
        if robust_z >= 3.5:
            return 0.52
        return 0.0

    @staticmethod
    def _combine_weights(weights: Iterable[float]) -> float:
        probability_of_none = 1.0
        for weight in weights:
            probability_of_none *= 1 - weight
        return round(1 - probability_of_none, 4)

    @staticmethod
    def _fallback_explanation(score: float, reasons: list[AnomalyReason]) -> str:
        relevant = [reason.message for reason in reasons if reason.weight > 0]
        if not relevant:
            return "Nenhum sinal relevante de anomalia foi encontrado nesta transação."
        verdict = "A cobrança é suspeita." if score >= 0.65 else "A cobrança merece atenção."
        return verdict + " " + " ".join(relevant)
