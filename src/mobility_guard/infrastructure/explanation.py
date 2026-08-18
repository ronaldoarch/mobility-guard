from __future__ import annotations

from openai import OpenAI

from mobility_guard.domain.models import AnomalyAnalysis, Transaction


class OpenAIExplanationProvider:
    """Optional adapter. No customer identifier is sent to the model."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, timeout=8.0, max_retries=1)
        self._model = model

    def explain(self, transaction: Transaction, analysis: AnomalyAnalysis) -> str:
        signals = "\n".join(
            f"- {reason.kind.value}: {reason.message}" for reason in analysis.reasons
        )
        response = self._client.responses.create(
            model=self._model,
            instructions=(
                "Você explica análises antifraude de mobilidade em português do Brasil. "
                "Seja objetivo, não afirme fraude como fato e não invente informações. "
                "Produza no máximo três frases e sugira revisão humana quando o risco for alto."
            ),
            input=(
                f"Categoria: {transaction.category.value}\n"
                f"Valor: R$ {transaction.amount}\n"
                f"Estabelecimento: {transaction.merchant}\n"
                f"Score determinístico: {analysis.score:.2f}\n"
                f"Sinais:\n{signals or '- nenhum'}"
            ),
            store=False,
        )
        return response.output_text.strip() or analysis.explanation


class TemplateExplanationProvider:
    def explain(self, transaction: Transaction, analysis: AnomalyAnalysis) -> str:
        del transaction
        return analysis.explanation

