"""Métricas de validação estatística — implementa o §4.3 do pré-projeto.

Cada função aqui corresponde a um item literal da seção "4.3 Validação
Estatística" do pré-projeto assinado. Os limiares NÃO são escolha de
implementação: foram fixados no documento entregue à orientadora, e mudá-los
sem mudar o documento quebra a correspondência entre o que o TCC promete e o
que o código faz.

    (a) Erro relativo percentual dos coeficientes  → tolerância 5%
    (b) Concordância de significância estatística  → alfa 0,05
    (c) Comparação de R² e R² ajustado             → tolerância 0,01
    (d) Diferença nas condições ótimas             → absoluta e % da faixa

O item (e) — fidelidade dos relatórios do LLM — vive em fidelity.py, porque
depende de julgamento humano item a item e não é aritmética.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from lyra.core.design import INTERCEPTO
from lyra.core.results import AnalysisResult

# --- Limiares fixados no §4.3 do pré-projeto assinado -----------------------
TOLERANCIA_ERRO_RELATIVO = 5.0  # §4.3(a), em pontos percentuais
ALFA_SIGNIFICANCIA = 0.05  # §4.3(b)
TOLERANCIA_R2 = 0.01  # §4.3(c), em valor absoluto de R²


@dataclass(frozen=True)
class ComparacaoCoeficiente:
    termo: str
    valor_lyra: float
    valor_referencia: float
    erro_relativo_pct: float | None
    dentro_tolerancia: bool
    observacao: str = ""


@dataclass(frozen=True)
class ResultadoErroCoeficientes:
    """§4.3(a)"""

    comparacoes: list[ComparacaoCoeficiente]
    erro_relativo_medio_pct: float | None
    erro_relativo_maximo_pct: float | None
    proporcao_dentro_tolerancia: float
    termos_ausentes_no_lyra: list[str] = field(default_factory=list)
    termos_extras_no_lyra: list[str] = field(default_factory=list)


def erro_relativo_coeficientes(
    resultado: AnalysisResult,
    resposta: str,
    coeficientes_referencia: dict[str, float],
    *,
    tolerancia_pct: float = TOLERANCIA_ERRO_RELATIVO,
) -> ResultadoErroCoeficientes:
    """§4.3(a) — erro relativo percentual de cada coeficiente estimado.

    O erro relativo é indefinido quando o valor de referência é zero; nesse
    caso `erro_relativo_pct` vem None e a comparação é marcada com uma
    observação, em vez de virar infinito e contaminar a média. Isso acontece
    de verdade: artigos frequentemente reportam coeficientes não significativos
    como 0.

    Coeficientes presentes num lado e ausentes no outro NÃO entram na média —
    seriam uma comparação sem par. Eles são reportados à parte, porque uma
    divergência de *quais* termos entraram no modelo é um achado por si só, e
    normalmente mais interessante que o erro numérico.
    """
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
                    valor_lyra=obtido,
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
                valor_lyra=obtido,
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
        termos_ausentes_no_lyra=ausentes,
        termos_extras_no_lyra=extras,
    )


@dataclass(frozen=True)
class ResultadoConcordanciaSignificancia:
    """§4.3(b)"""

    taxa_concordancia: float
    n_concordantes: int
    n_total: int
    divergencias: list[str]


def concordancia_significancia(
    resultado: AnalysisResult,
    resposta: str,
    significancia_referencia: dict[str, bool],
) -> ResultadoConcordanciaSignificancia:
    """§4.3(b) — taxa de concordância na classificação de significância.

    Taxa = nº de termos com classificação coincidente / nº total de termos
    avaliados, exatamente como definido no documento.

    Um termo presente na referência mas ausente do modelo do LYRA conta como
    divergência (e não é simplesmente ignorado): se o artigo considerou o termo
    e o LYRA nem o incluiu, isso é discordância de fato, e varrer para debaixo
    do tapete inflaria artificialmente a taxa.

    O intercepto fica de fora: a concordância de significância do §4.3(b) é
    sobre *quais efeitos são significativos*, e o intercepto (a média geral) não
    é um efeito de fator. Os artigos de DOE não o classificam, e incluí-lo só
    criaria uma divergência artificial contra uma referência que, corretamente,
    o deixa em branco.
    """
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
        sig_lyra = obtido.get(termo)
        sig_ref = referencia_sem_intercepto.get(termo)

        if sig_lyra is None:
            divergencias.append(f"{termo}: ausente no LYRA, referência={sig_ref}")
        elif sig_ref is None:
            divergencias.append(f"{termo}: ausente na referência, LYRA={sig_lyra}")
        elif sig_lyra == sig_ref:
            concordantes += 1
        else:
            divergencias.append(
                f"{termo}: LYRA={'sig' if sig_lyra else 'n.s.'}, "
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
    """§4.3(c)"""

    r2_lyra: float
    r2_referencia: float | None
    diferenca_r2: float | None
    r2_ajustado_lyra: float
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
    """§4.3(c) — diferença absoluta de R² e R² ajustado.

    Aceita referência ausente porque é comum: muitos artigos reportam R² e
    omitem o ajustado. Nesse caso a diferença correspondente vem None e não
    entra no julgamento de tolerância.
    """
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
        r2_lyra=ajuste.r2,
        r2_referencia=r2_referencia,
        diferenca_r2=dif_r2,
        r2_ajustado_lyra=ajuste.r2_ajustado,
        r2_ajustado_referencia=r2_ajustado_referencia,
        diferenca_r2_ajustado=dif_r2_aj,
        dentro_tolerancia=dentro,
    )


@dataclass(frozen=True)
class DiferencaFator:
    fator: str
    valor_lyra: float
    valor_referencia: float
    diferenca_absoluta: float
    diferenca_pct_faixa: float | None


@dataclass(frozen=True)
class ResultadoCondicaoOtima:
    """§4.3(d)"""

    diferencas: list[DiferencaFator]
    aplicavel: bool
    motivo_inaplicavel: str | None = None


def diferenca_condicao_otima(
    resultado: AnalysisResult,
    condicao_referencia: dict[str, float],
    faixas_experimentais: dict[str, tuple[float, float]] | None = None,
) -> ResultadoCondicaoOtima:
    """§4.3(d) — diferença entre a condição ótima do LYRA e a publicada.

    Expressa em termos absolutos e, quando `faixas_experimentais` é fornecida,
    também como percentual da faixa de cada fator. O percentual é o número que
    de fato importa: 2 unidades de diferença numa faixa de 10 é muito, numa
    faixa de 1000 é ruído — e sem normalizar pela faixa, fatores em escalas
    diferentes não são comparáveis entre si.
    """
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
        val_lyra = obtido[fator]
        val_ref = condicao_referencia[fator]
        dif_abs = abs(val_lyra - val_ref)

        dif_pct = None
        if faixas_experimentais and fator in faixas_experimentais:
            minimo, maximo = faixas_experimentais[fator]
            amplitude = maximo - minimo
            if amplitude > 0:
                dif_pct = dif_abs / amplitude * 100.0

        diferencas.append(
            DiferencaFator(
                fator=fator,
                valor_lyra=val_lyra,
                valor_referencia=val_ref,
                diferenca_absoluta=dif_abs,
                diferenca_pct_faixa=dif_pct,
            )
        )

    return ResultadoCondicaoOtima(diferencas=diferencas, aplicavel=True)
