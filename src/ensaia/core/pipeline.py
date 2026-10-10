"""Monta um `AnalysisResult` a partir de dados + delineamento + termos.

É o fim-a-fim determinístico do núcleo (matriz do modelo → OLS → coeficientes,
ANOVA e falta de ajuste), empacotado no contrato congelado `AnalysisResult`.

Difere de `validation/runner.py` em quem fornece os parâmetros: o runner os lê
de `referencia.yaml` (e aplica, por cima, as métricas do §4.3 contra os valores
publicados); aqui eles chegam prontos — é o caminho que a interface web usa para
analisar uma planilha enviada pelo usuário, em que o delineamento é inferido dos
próprios dados. Os dois compartilham os mesmos primitivos de cálculo
(`core.model`, `core.effects`, `core.anova`), que são a fonte única da conta.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from ensaia.core.anova import teste_falta_ajuste
from ensaia.core.design import Planejamento
from ensaia.core.diagnostico import diagnosticar
from ensaia.core.effects import extrair_coeficientes, t_critico
from ensaia.core.identificacao import contar_pontos_centrais
from ensaia.core.model import AjusteOLS, ajustar_ols, matriz_modelo
from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    FatorCodificado,
    InfoPlanejamento,
    LinhaAnova,
    MetadadosExecucao,
)
from ensaia.core.table import Table

ALFA_PADRAO = 0.05


def analisar(
    tabela: Table,
    planejamento: Planejamento,
    termos: list[str],
    respostas: Sequence[str],
    *,
    versao_ensaia: str,
    alfa: float = ALFA_PADRAO,
    executado_em: str | None = None,
    avisos_planejamento: Sequence[str] = (),
) -> AnalysisResult:
    """Ajusta o modelo a cada resposta e devolve o resultado congelado.

    `planejamento` traz os fatores e suas faixas (de onde sai a codificação
    [-1, +1]); `termos` é a lista de termos do modelo (ex.: de `termos_do_modelo`);
    `respostas` são as colunas de resposta a ajustar. A otimização por
    desejabilidade (ponto ótimo) ainda não entra aqui — fica `None` até a issue #6.

    Levanta `ValueError` quando falta uma coluna exigida ou uma resposta tem
    valor ausente/não numérico — mensagens em português, prontas para virar aviso
    na interface.
    """
    fatores = planejamento.nomes_fatores
    exigidas = set(fatores) | set(respostas)
    ausentes = sorted(exigidas - set(tabela.colunas))
    if ausentes:
        raise ValueError(
            f"Colunas ausentes na planilha: {ausentes}. "
            f"Disponíveis: {list(tabela.colunas)}."
        )

    matriz = matriz_modelo(tabela, planejamento, termos, codificar=True)
    ajustes: list[AjusteResposta] = []
    avisos: list[str] = list(avisos_planejamento)
    for resposta in respostas:
        resposta = str(resposta)
        y = tabela.coluna(resposta)
        if np.isnan(y).any():
            linhas = [int(i) + 2 for i in np.flatnonzero(np.isnan(y))]
            raise ValueError(
                f"A resposta {resposta!r} tem valores ausentes ou não numéricos "
                f"nas linhas {linhas} da planilha."
            )
        ajuste = ajustar_ols(matriz, y)
        ajustes.append(
            _ajuste_resposta(
                resposta, ajuste, termos, avisos, tabela, fatores, alfa=alfa
            )
        )

    return AnalysisResult(
        tipo_planejamento=planejamento.tipo,
        fatores=fatores,
        respostas=[str(r) for r in respostas],
        ajustes=ajustes,
        metadados=MetadadosExecucao(
            versao_ensaia=versao_ensaia, alfa=alfa, executado_em=executado_em
        ),
        ponto_otimo=None,
        avisos=avisos,
        planejamento=info_planejamento(tabela, planejamento, avisos_planejamento),
    )


def info_planejamento(
    tabela: Table, planejamento: Planejamento, avisos: Sequence[str] = ()
) -> InfoPlanejamento:
    """Seção `design` do contrato: geometria e codificação de cada fator."""
    codificada = np.column_stack(
        [
            [f.codificar(float(v)) for v in tabela.coluna(f.nome)]
            for f in planejamento.fatores
        ]
    )
    return InfoPlanejamento(
        k=planejamento.k,
        n_ensaios=len(tabela),
        n_pontos_centrais=contar_pontos_centrais(codificada),
        alfa_axial=planejamento.alfa_axial,
        fatores=[
            FatorCodificado(
                nome=f.nome, centro=f.centro, passo=f.amplitude / 2.0, unidade=f.unidade
            )
            for f in planejamento.fatores
        ],
        avisos=list(avisos),
    )


def _ajuste_resposta(
    resposta: str,
    ajuste: AjusteOLS,
    termos: list[str],
    avisos: list[str],
    dados: Table,
    fatores: list[str],
    *,
    alfa: float,
) -> AjusteResposta:
    """Empacota um ajuste OLS no contrato congelado `AjusteResposta`.

    A extração de coeficientes é delegada a `effects.extrair_coeficientes` (fonte
    única da tradução termo→coeficiente/significância), a falta de ajuste a
    `anova.teste_falta_ajuste`, que precisa dos dados crus para achar réplicas, e
    os valores por ensaio + normalidade a `diagnostico.diagnosticar`.
    """
    return AjusteResposta(
        resposta=resposta,
        coeficientes=extrair_coeficientes(ajuste, alfa=alfa),
        anova=_linhas_anova(resposta, ajuste, avisos),
        r2=ajuste.r2,
        r2_ajustado=ajuste.r2_ajustado,
        falta_de_ajuste=teste_falta_ajuste(dados, resposta, fatores, ajuste, alfa=alfa),
        n_observacoes=ajuste.n_observacoes,
        graus_liberdade_residuo=ajuste.gl_residuo,
        termos_incluidos=list(termos),
        t_critico=t_critico(alfa, ajuste.gl_residuo),
        diagnostico=diagnosticar(
            dados.coluna(resposta), ajuste.valores_ajustados, alfa=alfa
        ),
    )


def _linhas_anova(
    resposta: str, ajuste: AjusteOLS, avisos: list[str]
) -> list[LinhaAnova]:
    """ANOVA Tipo II em `LinhaAnova`, ou vazia se o modelo não é hierárquico.

    O `AjusteOLS` já devolve as linhas prontas; aqui só se traduz a recusa do
    modelo não hierárquico (um `ValueError`) num aviso que sobe ao relatório.
    """
    try:
        return ajuste.tabela_tipo2()
    except ValueError as erro:
        avisos.append(f"{resposta}: ANOVA Tipo II indisponível — {erro}")
        return []
