"""Tabela de ANOVA, seleção de termos e teste de falta de ajuste.

Critério de significância: alfa = 0,05, conforme §4.3(b) do pré-projeto
assinado. O protótipo original usava p <= 0,10; a mudança é deliberada e está
registrada em docs/decisoes/0003-criterio-de-significancia.md.
"""

from __future__ import annotations

from collections.abc import Sequence

from scipy import stats

from ensaia.core.design import INTERCEPTO, interpretar_termo
from ensaia.core.model import RESIDUO, AjusteOLS
from ensaia.core.results import AnovaRegressao, FaltaDeAjuste, LinhaAnova
from ensaia.core.table import Table

ALFA_PADRAO = 0.05

# Regra prática de Box e Wetz (1973) apud BARROS NETO; SCARMINIO; BRUNS
# (2010, p. 238): uma regressão só é útil para previsão quando F_calc/F_tab é
# de uma ordem de grandeza maior que 1 — "pelo menos cerca de 10 vezes". É um
# critério mais exigente que a significância (razão > 1) e distinto dela.
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
    """ANOVA da regressão no formato da literatura de DOE (spec §9, C2).

        Regressão   gl = p − 1     SQ_R = SQ_T − SQ_res   F = QM_R / QM_res
        Resíduo     gl = n − p     SQ_res
          Falta de ajuste / Erro puro (quando há réplicas genuínas)
        Total       gl = n − 1     SQ_T

    Além do p-valor, devolve o F tabelado F(1 − α; gl_R, gl_res) e a razão
    F calculado / F tabelado (razão maior que 1 é regressão significativa —
    é o mesmo teste F, só reexpresso). Também devolve `util_para_previsao`:
    regra de Box e Wetz (1973) apud Barros Neto, Scarminio e Bruns (2010,
    p. 238), mais exigente que a significância — só com razão ≳10×.

    Com blocos (colunas fixas do ajuste), a variação entre blocos sai numa
    linha própria, antes da regressão, e a regressão mede o que os fatores
    explicam **depois** dos blocos:

        Blocos      gl = b − 1     SQ_B = SQ_T − SQ_res(só blocos)
        Regressão   gl = p − b     SQ_R = SQ_res(só blocos) − SQ_res

    O bloco não recebe teste F: ele é uma restrição de como os ensaios foram
    feitos, não um fator em estudo; a linha mostra quanto da variação ele tirou
    do erro.
    """
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
    """(SQ, gl) do erro puro: a variação entre réplicas da mesma condição.

    Depende só dos dados (não do modelo): agrupa os ensaios com os mesmos níveis
    de todos os fatores e soma a dispersão dentro de cada grupo. gl = n − nº de
    condições distintas; 0 quando nenhuma condição foi repetida.

    Com `blocos` (o rótulo de bloco de cada ensaio), só conta como réplica a
    mesma condição **no mesmo bloco**: duas réplicas em blocos diferentes
    diferem também pelo bloco, e essa diferença não é erro puro.
    """
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
    """Separa os termos em (mantidos, descartados) por significância.

    `manter_hierarquia=True` preserva o princípio hierárquico: se x1:x2 ou x1^2
    é significativo, o termo linear x1 fica no modelo mesmo que individualmente
    não seja. Modelo não hierárquico deixa de ser invariante à mudança de escala
    dos fatores — os coeficientes passam a depender de onde você pôs o zero, o
    que é indefensável em quimiometria.

    Entra a tabela de ANOVA Tipo II (uma `LinhaAnova` por termo, mais a linha de
    resíduo, que é ignorada). O Intercepto não aparece na tabela e é sempre
    mantido pelo chamador — o modelo reduzido é `["Intercepto"] + mantidos`.
    Devolve `(mantidos, descartados)` na ordem original dos termos.
    """
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
                # O termo linear de um fator usado num termo de ordem superior
                # fica no modelo. O nome do termo linear é o próprio nome do fator.
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
    """Decompõe o resíduo em falta de ajuste + erro puro.

    Só é possível com repetições genuínas de uma mesma condição experimental
    (na prática, os pontos centrais). Sem elas, devolve
    `FaltaDeAjuste(aplicavel=False, motivo_inaplicavel=...)` — nunca inventa um
    teste. A camada narrativa depende dessa distinção para não escrever "não
    houve falta de ajuste" quando na verdade o teste não pôde ser feito.

    O erro puro vem da variação da resposta DENTRO de cada combinação de níveis
    repetida; a falta de ajuste é o que sobra do resíduo depois de tirar o erro
    puro. Um F alto (falta de ajuste significativa) diz que o desvio do modelo é
    grande comparado à dispersão entre réplicas — ou seja, o modelo não descreve
    bem os dados, e não é só ruído experimental.

        gl_erro_puro = n − (nº de combinações distintas de níveis)
        SQ_erro_puro = Σ_grupos Σ (y − média do grupo)²
        SQ_falta = SQ_residuo − SQ_erro_puro ;  gl_falta = gl_residuo − gl_erro_puro
        F = (SQ_falta/gl_falta) / (SQ_erro_puro/gl_erro_puro)
    """
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
        # Réplicas idênticas (erro puro nulo): F é infinito; reportar como
        # significativa sem armazenar inf (que não é JSON válido).
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
