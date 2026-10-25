"""Métricas de validação do §4.3: coeficientes, significância, R² e ótimo.
Os limiares vêm do pré-projeto e não mudam sem mudar o documento.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ensaia.core.design import INTERCEPTO
from ensaia.core.results import AnalysisResult

# --- Limiares fixados no §4.3 do pré-projeto assinado -----------------------
TOLERANCIA_ERRO_RELATIVO = 5.0  # §4.3(a), em pontos percentuais
ALFA_SIGNIFICANCIA = 0.05  # §4.3(b)
TOLERANCIA_R2 = 0.01  # §4.3(c), em valor absoluto de R²


@dataclass(frozen=True)
class ComparacaoCoeficiente:
    """Comparação de um coeficiente com o valor publicado."""

    termo: str
    valor_ensaia: float
    valor_referencia: float
    erro_relativo_pct: float | None
    dentro_tolerancia: bool
    observacao: str = ""


@dataclass(frozen=True)
class ResultadoErroCoeficientes:
    """Resultado do critério (a): erro relativo dos coeficientes."""

    comparacoes: list[ComparacaoCoeficiente]
    erro_relativo_medio_pct: float | None
    erro_relativo_maximo_pct: float | None
    proporcao_dentro_tolerancia: float
    termos_ausentes_no_ensaia: list[str] = field(default_factory=list)
    termos_extras_no_ensaia: list[str] = field(default_factory=list)


def erro_relativo_coeficientes(
    resultado: AnalysisResult,
    resposta: str,
    coeficientes_referencia: dict[str, float],
    *,
    tolerancia_pct: float = TOLERANCIA_ERRO_RELATIVO,
) -> ResultadoErroCoeficientes:
    """Erro relativo de cada coeficiente contra o publicado."""
    ajuste = resultado.ajuste(resposta)
    estimados = {c.termo: c.estimativa for c in ajuste.coeficientes}

    comuns = sorted(set(estimados) & set(coeficientes_referencia))
    ausentes = sorted(set(coeficientes_referencia) - set(estimados))
    extras = sorted(set(estimados) - set(coeficientes_referencia))

    comparacoes: list[ComparacaoCoeficiente] = []
    erros_validos: list[float] = []

    for termo in comuns:
        obtido = estimados[termo]
        esperado = coeficientes_referencia[termo]

        if esperado == 0.0:
            comparacoes.append(
                ComparacaoCoeficiente(
                    termo=termo,
                    valor_ensaia=obtido,
                    valor_referencia=esperado,
                    erro_relativo_pct=None,
                    dentro_tolerancia=math.isclose(obtido, 0.0, abs_tol=1e-9),
                    observacao=(
                        "Coeficiente de referência é zero; erro relativo é "
                        "indefinido. Comparado por proximidade absoluta de zero."
                    ),
                )
            )
            continue

        erro = abs(obtido - esperado) / abs(esperado) * 100.0
        erros_validos.append(erro)
        comparacoes.append(
            ComparacaoCoeficiente(
                termo=termo,
                valor_ensaia=obtido,
                valor_referencia=esperado,
                erro_relativo_pct=erro,
                dentro_tolerancia=erro <= tolerancia_pct,
            )
        )

    dentro = sum(1 for c in comparacoes if c.dentro_tolerancia)
    proporcao = dentro / len(comparacoes) if comparacoes else 0.0

    return ResultadoErroCoeficientes(
        comparacoes=comparacoes,
        erro_relativo_medio_pct=(
            sum(erros_validos) / len(erros_validos) if erros_validos else None
        ),
        erro_relativo_maximo_pct=max(erros_validos) if erros_validos else None,
        proporcao_dentro_tolerancia=proporcao,
        termos_ausentes_no_ensaia=ausentes,
        termos_extras_no_ensaia=extras,
    )


@dataclass(frozen=True)
class ResultadoConcordanciaSignificancia:
    """Resultado do critério (b): concordância de significância."""

    taxa_concordancia: float
    n_concordantes: int
    n_total: int
    divergencias: list[str]


def concordancia_significancia(
    resultado: AnalysisResult,
    resposta: str,
    significancia_referencia: dict[str, bool],
) -> ResultadoConcordanciaSignificancia:
    """Taxa de termos com a mesma classificação de significância."""
    ajuste = resultado.ajuste(resposta)
    obtido = {
        c.termo: c.significativo for c in ajuste.coeficientes if c.termo != INTERCEPTO
    }
    referencia_sem_intercepto = {
        termo: sig
        for termo, sig in significancia_referencia.items()
        if termo != INTERCEPTO
    }

    termos = sorted(set(obtido) | set(referencia_sem_intercepto))
    concordantes = 0
    divergencias: list[str] = []

    for termo in termos:
        sig_ensaia = obtido.get(termo)
        sig_ref = referencia_sem_intercepto.get(termo)

        if sig_ensaia is None:
            divergencias.append(f"{termo}: ausente no EnsaIA, referência={sig_ref}")
        elif sig_ref is None:
            divergencias.append(f"{termo}: ausente na referência, EnsaIA={sig_ensaia}")
        elif sig_ensaia == sig_ref:
            concordantes += 1
        else:
            divergencias.append(
                f"{termo}: EnsaIA={'sig' if sig_ensaia else 'n.s.'}, "
                f"referência={'sig' if sig_ref else 'n.s.'}"
            )

    total = len(termos)
    return ResultadoConcordanciaSignificancia(
        taxa_concordancia=concordantes / total if total else 0.0,
        n_concordantes=concordantes,
        n_total=total,
        divergencias=divergencias,
    )


@dataclass(frozen=True)
class ResultadoComparacaoR2:
    """Resultado do critério (c): diferença de R²."""

    r2_ensaia: float
    r2_referencia: float | None
    diferenca_r2: float | None
    r2_ajustado_ensaia: float
    r2_ajustado_referencia: float | None
    diferenca_r2_ajustado: float | None
    dentro_tolerancia: bool


def comparacao_r2(
    resultado: AnalysisResult,
    resposta: str,
    r2_referencia: float | None,
    r2_ajustado_referencia: float | None = None,
    *,
    tolerancia: float = TOLERANCIA_R2,
) -> ResultadoComparacaoR2:
    """Diferença de R² e R² ajustado contra o publicado."""
    ajuste = resultado.ajuste(resposta)

    dif_r2 = abs(ajuste.r2 - r2_referencia) if r2_referencia is not None else None
    dif_r2_aj = (
        abs(ajuste.r2_ajustado - r2_ajustado_referencia)
        if r2_ajustado_referencia is not None
        else None
    )

    diferencas = [d for d in (dif_r2, dif_r2_aj) if d is not None]
    dentro = all(d <= tolerancia for d in diferencas) if diferencas else False

    return ResultadoComparacaoR2(
        r2_ensaia=ajuste.r2,
        r2_referencia=r2_referencia,
        diferenca_r2=dif_r2,
        r2_ajustado_ensaia=ajuste.r2_ajustado,
        r2_ajustado_referencia=r2_ajustado_referencia,
        diferenca_r2_ajustado=dif_r2_aj,
        dentro_tolerancia=dentro,
    )


@dataclass(frozen=True)
class DiferencaFator:
    """Diferença de um fator entre os ótimos."""

    fator: str
    valor_ensaia: float
    valor_referencia: float
    diferenca_absoluta: float
    diferenca_pct_faixa: float | None


@dataclass(frozen=True)
class ResultadoCondicaoOtima:
    """Resultado do critério (d): diferença da condição ótima."""

    diferencas: list[DiferencaFator]
    aplicavel: bool
    motivo_inaplicavel: str | None = None


def diferenca_condicao_otima(
    resultado: AnalysisResult,
    condicao_referencia: dict[str, float],
    faixas_experimentais: dict[str, tuple[float, float]] | None = None,
) -> ResultadoCondicaoOtima:
    """Diferença entre o ótimo do EnsaIA e o publicado."""
    if resultado.ponto_otimo is None:
        return ResultadoCondicaoOtima(
            diferencas=[],
            aplicavel=False,
            motivo_inaplicavel=(
                "A análise não produziu ponto ótimo (otimização não executada "
                "ou bloqueada por R² insuficiente)."
            ),
        )

    obtido = resultado.ponto_otimo.coordenadas
    diferencas: list[DiferencaFator] = []

    for fator in sorted(set(obtido) & set(condicao_referencia)):
        val_ensaia = obtido[fator]
        val_ref = condicao_referencia[fator]
        dif_abs = abs(val_ensaia - val_ref)

        dif_pct = None
        if faixas_experimentais and fator in faixas_experimentais:
            minimo, maximo = faixas_experimentais[fator]
            amplitude = maximo - minimo
            if amplitude > 0:
                dif_pct = dif_abs / amplitude * 100.0

        diferencas.append(
            DiferencaFator(
                fator=fator,
                valor_ensaia=val_ensaia,
                valor_referencia=val_ref,
                diferenca_absoluta=dif_abs,
                diferenca_pct_faixa=dif_pct,
            )
        )

    return ResultadoCondicaoOtima(diferencas=diferencas, aplicavel=True)
