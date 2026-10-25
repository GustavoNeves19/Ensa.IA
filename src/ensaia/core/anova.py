"""ANOVA da regressão, erro puro e teste de falta de ajuste do modelo.
Também separa termos por significância (α = 0,05, ADR 0003).
"""

from __future__ import annotations

from collections.abc import Sequence

from scipy import stats

from ensaia.core.design import INTERCEPTO, interpretar_termo
from ensaia.core.model import RESIDUO, AjusteOLS
from ensaia.core.results import AnovaRegressao, FaltaDeAjuste, LinhaAnova
from ensaia.core.table import Table

ALFA_PADRAO = 0.05

# Box e Wetz (1973): regressão útil para prever quando F/Ftab ≥ ~10.
RAZAO_UTIL_PREVISAO = 10.0

# Fontes da ANOVA da regressão (a linha do resíduo usa RESIDUO, de model.py).
REGRESSAO = "Regressão"
BLOCOS = "Blocos"
FALTA_DE_AJUSTE = "Falta de ajuste"
ERRO_PURO = "Erro puro"
TOTAL = "Total"


def anova_regressao(
    ajuste: AjusteOLS, falta: FaltaDeAjuste, *, alfa: float = ALFA_PADRAO
) -> AnovaRegressao:
    """Monta a ANOVA da regressão (blocos, regressão, resíduo, total) e o F/Ftab."""
    fixos = ajuste.termos_fixos
    gl_res = ajuste.gl_residuo
    sq_t = ajuste.soma_quadrados_total
    sq_res = ajuste.soma_quadrados_residual
    qm_res = sq_res / gl_res

    linhas: list[LinhaAnova] = []
    if fixos:
        sq_so_blocos = ajuste.soma_quadrados_residual_de([INTERCEPTO, *fixos])
        sq_b = sq_t - sq_so_blocos
        linhas.append(
            LinhaAnova(
                fonte=BLOCOS,
                soma_quadrados=sq_b,
                graus_liberdade=len(fixos),
                quadrado_medio=sq_b / len(fixos),
            )
        )
        sq_r = sq_so_blocos - sq_res
    else:
        sq_r = sq_t - sq_res
    gl_r = ajuste.n_parametros - 1 - len(fixos)

    f_tab: float | None = None
    razao: float | None = None
    significativa: bool | None = None
    util: bool | None = None
    if gl_r > 0:
        qm_r = sq_r / gl_r
        f = qm_r / qm_res if qm_res > 0 else None
        p = float(stats.f.sf(f, gl_r, gl_res)) if f is not None else 0.0
        f_tab = float(stats.f.ppf(1.0 - alfa, gl_r, gl_res))
        razao = f / f_tab if f is not None else None
        significativa = p < alfa
        util = razao >= RAZAO_UTIL_PREVISAO if razao is not None else None
        linhas.append(
            LinhaAnova(
                fonte=REGRESSAO,
                soma_quadrados=sq_r,
                graus_liberdade=gl_r,
                quadrado_medio=qm_r,
                valor_f=f,
                valor_p=p,
            )
        )
    linhas.append(
        LinhaAnova(
            fonte=RESIDUO,
            soma_quadrados=sq_res,
            graus_liberdade=gl_res,
            quadrado_medio=qm_res,
        )
    )
    if (
        falta.aplicavel
        and falta.soma_quadrados_falta is not None
        and falta.graus_liberdade_falta
        and falta.soma_quadrados_erro_puro is not None
        and falta.graus_liberdade_erro_puro
    ):
        linhas.append(
            LinhaAnova(
                fonte=FALTA_DE_AJUSTE,
                soma_quadrados=falta.soma_quadrados_falta,
                graus_liberdade=falta.graus_liberdade_falta,
                quadrado_medio=falta.soma_quadrados_falta / falta.graus_liberdade_falta,
                valor_f=falta.valor_f,
                valor_p=falta.valor_p,
            )
        )
        linhas.append(
            LinhaAnova(
                fonte=ERRO_PURO,
                soma_quadrados=falta.soma_quadrados_erro_puro,
                graus_liberdade=falta.graus_liberdade_erro_puro,
                quadrado_medio=(
                    falta.soma_quadrados_erro_puro / falta.graus_liberdade_erro_puro
                ),
            )
        )
    linhas.append(
        LinhaAnova(
            fonte=TOTAL,
            soma_quadrados=sq_t,
            graus_liberdade=ajuste.n_observacoes - 1,
            quadrado_medio=sq_t / (ajuste.n_observacoes - 1),
        )
    )
    return AnovaRegressao(
        linhas=linhas,
        f_tabelado=f_tab,
        razao_f=razao,
        regressao_significativa=significativa,
        util_para_previsao=util,
    )


def erro_puro(
    dados: Table,
    resposta: str,
    fatores: list[str],
    blocos: Sequence[str] | None = None,
) -> tuple[float, int]:
    """Soma de quadrados e g.l. do erro puro: a variação entre réplicas."""
    y = dados.coluna(resposta)
    colunas = [dados.coluna(f) for f in fatores]
    grupos: dict[tuple[object, ...], list[int]] = {}
    for i in range(len(y)):
        chave: tuple[object, ...] = tuple(float(col[i]) for col in colunas)
        if blocos is not None:
            chave = (blocos[i], *chave)
        grupos.setdefault(chave, []).append(i)

    sq = 0.0
    for indices in grupos.values():
        if len(indices) > 1:
            valores = y[indices]
            sq += float(((valores - valores.mean()) ** 2).sum())
    return sq, len(y) - len(grupos)


def selecionar_termos(
    anova: list[LinhaAnova],
    *,
    alfa: float = ALFA_PADRAO,
    manter_hierarquia: bool = True,
) -> tuple[list[str], list[str]]:
    """Separa os termos em mantidos e descartados pelo p, com hierarquia."""
    termos = [linha.fonte for linha in anova if linha.fonte != RESIDUO]
    significativos = {
        linha.fonte
        for linha in anova
        if linha.fonte != RESIDUO
        and linha.valor_p is not None
        and linha.valor_p < alfa
    }

    manter = set(significativos)
    if manter_hierarquia:
        for termo in significativos:
            for fator, _potencia in interpretar_termo(termo):
                # O termo linear de um fator usado num termo superior fica no modelo.
                if fator in termos:
                    manter.add(fator)

    mantidos = [t for t in termos if t in manter]
    descartados = [t for t in termos if t not in manter]
    return mantidos, descartados


def teste_falta_ajuste(
    dados: Table,
    resposta: str,
    fatores: list[str],
    ajuste: AjusteOLS,
    *,
    alfa: float = ALFA_PADRAO,
    blocos: Sequence[str] | None = None,
) -> FaltaDeAjuste:
    """Divide o resíduo em falta de ajuste e erro puro e testa com F."""
    sq_erro_puro, gl_erro_puro = erro_puro(dados, resposta, fatores, blocos)
    if gl_erro_puro <= 0:
        return FaltaDeAjuste(
            aplicavel=False,
            motivo_inaplicavel=(
                "não há réplicas genuínas: cada combinação de níveis aparece "
                "uma única vez"
            ),
        )

    gl_falta = ajuste.gl_residuo - gl_erro_puro
    if gl_falta <= 0:
        return FaltaDeAjuste(
            aplicavel=False,
            motivo_inaplicavel=(
                "o modelo não deixa graus de liberdade para a falta de ajuste "
                "(termos demais para o número de pontos distintos)"
            ),
        )

    sq_falta = ajuste.soma_quadrados_residual - sq_erro_puro
    qm_erro_puro = sq_erro_puro / gl_erro_puro
    qm_falta = sq_falta / gl_falta

    if qm_erro_puro == 0.0:
        # Réplicas idênticas: F infinito; marca significativa sem guardar inf.
        return FaltaDeAjuste(
            aplicavel=True,
            soma_quadrados_falta=sq_falta,
            soma_quadrados_erro_puro=sq_erro_puro,
            graus_liberdade_falta=gl_falta,
            graus_liberdade_erro_puro=gl_erro_puro,
            valor_f=None,
            valor_p=0.0,
            significativa=sq_falta > 0,
        )

    f = qm_falta / qm_erro_puro
    p = float(stats.f.sf(f, gl_falta, gl_erro_puro))
    return FaltaDeAjuste(
        aplicavel=True,
        soma_quadrados_falta=sq_falta,
        soma_quadrados_erro_puro=sq_erro_puro,
        graus_liberdade_falta=gl_falta,
        graus_liberdade_erro_puro=gl_erro_puro,
        valor_f=f,
        valor_p=p,
        significativa=p < alfa,
    )
