"""Testes do contrato Pydantic `AnalysisResult` (ADR 0001, spec seção 10)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    Coeficiente,
    FaltaDeAjuste,
    MetadadosExecucao,
)


def _coeficiente() -> Coeficiente:
    return Coeficiente(
        termo="Intercepto",
        estimativa=50.0,
        erro_padrao=1.0,
        valor_t=50.0,
        valor_p=0.0001,
        significativo=True,
    )


def _resultado() -> AnalysisResult:
    return AnalysisResult(
        tipo_planejamento="composto_central",
        fatores=["temperatura"],
        respostas=["rendimento"],
        ajustes=[
            AjusteResposta(
                resposta="rendimento",
                coeficientes=[_coeficiente()],
                anova=[],
                r2=0.95,
                r2_ajustado=0.93,
                falta_de_ajuste=FaltaDeAjuste(aplicavel=False),
                n_observacoes=8,
                graus_liberdade_residuo=4,
                termos_incluidos=["Intercepto"],
            )
        ],
        metadados=MetadadosExecucao(versao_ensaia="0.1.0"),
    )


def test_contrato_e_imutavel() -> None:
    """A fronteira é congelada: a camada de LLM não pode alterar um número."""
    coef = _coeficiente()
    with pytest.raises(ValidationError):
        coef.estimativa = 999.0  # type: ignore[misc]


def test_rejeita_tipo_de_planejamento_invalido() -> None:
    with pytest.raises(ValidationError):
        AnalysisResult(
            tipo_planejamento="planejamento_que_nao_existe",  # type: ignore[arg-type]
            fatores=[],
            respostas=[],
            ajustes=[],
            metadados=MetadadosExecucao(versao_ensaia="0.1.0"),
        )


def test_rejeita_coeficiente_nao_numerico() -> None:
    with pytest.raises(ValidationError):
        Coeficiente(
            termo="x1",
            estimativa="não é número",  # type: ignore[arg-type]
            erro_padrao=1.0,
            valor_t=1.0,
            valor_p=0.5,
            significativo=False,
        )


def test_round_trip_por_json_preserva_tudo() -> None:
    original = _resultado()
    recarregado = AnalysisResult.model_validate_json(original.to_json())
    assert recarregado == original


def test_ajuste_recupera_por_nome_e_falha_claro() -> None:
    resultado = _resultado()
    assert resultado.ajuste("rendimento").r2 == 0.95
    with pytest.raises(KeyError, match="não está neste resultado"):
        resultado.ajuste("inexistente")
