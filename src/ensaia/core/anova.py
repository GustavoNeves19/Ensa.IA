"""Tabela de ANOVA, seleção de termos e teste de falta de ajuste.

Critério de significância: alfa = 0,05, conforme §4.3(b) do pré-projeto
assinado. O protótipo original usava p <= 0,10; a mudança é deliberada e está
registrada em docs/decisoes/0003-criterio-de-significancia.md.
"""

from __future__ import annotations

from scipy import stats

from ensaia.core.model import AjusteOLS
from ensaia.core.results import FaltaDeAjuste, LinhaAnova
from ensaia.core.table import Table

ALFA_PADRAO = 0.05


def tabela_anova(ajuste: AjusteOLS, tipo: int = 2) -> list[LinhaAnova]:
    """Constrói a tabela de ANOVA do modelo ajustado.

    ANOVA tipo II por padrão: com planejamentos desbalanceados (o que acontece
    sempre que há pontos centrais repetidos), a soma de quadrados sequencial
    (tipo I) depende da ordem em que os termos entram no modelo, e resultados
    que mudam conforme a ordem das colunas não são defensáveis numa banca.

    TODO(#4): a Tipo II já é calculada em numpy por `AjusteOLS.tabela_tipo2()`
    (ver model.py e ADR 0007); aqui é só adaptá-la para `list[LinhaAnova]` e
    acrescentar a decomposição falta de ajuste/erro puro. Sem statsmodels.
    """
    raise NotImplementedError("Ver issue #4 — ANOVA e seleção de termos.")


def selecionar_termos(
    anova: list[LinhaAnova],
    *,
    alfa: float = ALFA_PADRAO,
    manter_hierarquia: bool = True,
) -> tuple[list[str], list[str]]:
    """Separa os termos em (mantidos, descartados) por significância.

    `manter_hierarquia=True` preserva o princípio hierárquico: se x1:x2 é
    significativo, x1 e x2 ficam no modelo mesmo que individualmente não
    sejam. Modelo não hierárquico deixa de ser invariante à mudança de escala
    dos fatores — os coeficientes passam a depender de onde você pôs o zero, o
    que é indefensável em quimiometria.

    TODO(#4): implementar.
    """
    raise NotImplementedError("Ver issue #4 — ANOVA e seleção de termos.")


def teste_falta_ajuste(
    dados: Table,
    resposta: str,
    fatores: list[str],
    ajuste: AjusteOLS,
    *,
    alfa: float = ALFA_PADRAO,
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
    y = dados.coluna(resposta)
    colunas = [dados.coluna(f) for f in fatores]
    grupos: dict[tuple[float, ...], list[int]] = {}
    for i in range(len(y)):
        chave = tuple(float(col[i]) for col in colunas)
        grupos.setdefault(chave, []).append(i)

    gl_erro_puro = len(y) - len(grupos)
    if gl_erro_puro <= 0:
        return FaltaDeAjuste(
            aplicavel=False,
            motivo_inaplicavel=(
                "não há réplicas genuínas: cada combinação de níveis aparece "
                "uma única vez"
            ),
        )

    sq_erro_puro = 0.0
    for indices in grupos.values():
        if len(indices) > 1:
            valores = y[indices]
            sq_erro_puro += float(((valores - valores.mean()) ** 2).sum())

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
