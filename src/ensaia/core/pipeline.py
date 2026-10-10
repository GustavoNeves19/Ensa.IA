"""Monta um `AnalysisResult` a partir de dados + delineamento + termos.

É o fim-a-fim determinístico do núcleo (matriz do modelo → OLS → coeficientes,
ANOVA, falta de ajuste, diagnóstico e equação), empacotado no contrato congelado
`AnalysisResult`.

É a fonte única da conta para todas as portas: a interface web (que infere o
delineamento dos próprios dados), a validação (`validation/runner.py`, que lê os
parâmetros de `referencia.yaml`) e o servidor MCP. Todos chamam `analisar`.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from ensaia.core.anova import anova_regressao, erro_puro, teste_falta_ajuste
from ensaia.core.design import Planejamento
from ensaia.core.diagnostico import diagnosticar
from ensaia.core.effects import extrair_coeficientes, t_critico
from ensaia.core.equacao import montar_equacao
from ensaia.core.identificacao import contar_pontos_centrais
from ensaia.core.model import AjusteOLS, ajustar_ols, matriz_modelo
from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    FatorCodificado,
    InfoPlanejamento,
    LinhaAnova,
    MetadadosExecucao,
    TermoErro,
    TipoModelo,
)
from ensaia.core.table import Table
from ensaia.core.termos import reduzir_backward

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
    termo_erro: TermoErro = "residuo",
    reduzir: bool = False,
    tipo_modelo: TipoModelo | None = None,
) -> AnalysisResult:
    """Ajusta o modelo a cada resposta e devolve o resultado congelado.

    `planejamento` traz os fatores e suas faixas (de onde sai a codificação
    [-1, +1]); `termos` é a lista de termos do modelo (ex.: de
    `termos.escolher_termos`); `respostas` são as colunas de resposta.

    - `termo_erro="erro_puro"` usa o erro puro das réplicas nos testes t e F;
      sem réplicas, cai para o resíduo e avisa.
    - `reduzir=True` aplica a eliminação backward por resposta (cada resposta
      pode terminar com termos diferentes).
    - `tipo_modelo` só é registrado nos metadados (os termos já chegam prontos).

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
        qm_erro, gl_erro, usado = _termo_de_erro(
            tabela, resposta, fatores, termo_erro, avisos
        )
        termos_resposta: list[str] = list(termos)
        descartados: list[str] = []
        if reduzir:
            termos_resposta, descartados = reduzir_backward(
                tabela,
                planejamento,
                termos,
                y,
                alfa=alfa,
                qm_erro=qm_erro,
                gl_erro=gl_erro,
            )
        matriz = matriz_modelo(tabela, planejamento, termos_resposta, codificar=True)
        ajuste = ajustar_ols(matriz, y)
        ajustes.append(
            _ajuste_resposta(
                resposta,
                ajuste,
                termos_resposta,
                avisos,
                tabela,
                planejamento,
                alfa=alfa,
                qm_erro=qm_erro,
                gl_erro=gl_erro,
                termo_erro=usado,
                descartados=descartados,
            )
        )

    return AnalysisResult(
        tipo_planejamento=planejamento.tipo,
        fatores=fatores,
        respostas=[str(r) for r in respostas],
        ajustes=ajustes,
        metadados=MetadadosExecucao(
            versao_ensaia=versao_ensaia,
            alfa=alfa,
            executado_em=executado_em,
            tipo_modelo=tipo_modelo,
            termo_erro=termo_erro,
            reducao_backward=reduzir,
        ),
        ponto_otimo=None,
        avisos=avisos,
        planejamento=info_planejamento(tabela, planejamento, avisos_planejamento),
    )


def _termo_de_erro(
    tabela: Table,
    resposta: str,
    fatores: list[str],
    pedido: TermoErro,
    avisos: list[str],
) -> tuple[float | None, int | None, TermoErro]:
    """(QM, gl, termo usado) do erro dos testes; None/None = resíduo."""
    if pedido == "residuo":
        return None, None, "residuo"
    sq, gl = erro_puro(tabela, resposta, fatores)
    if gl <= 0 or sq <= 0.0:
        motivo = (
            "não há réplicas genuínas" if gl <= 0 else "as réplicas são idênticas"
        )
        avisos.append(
            f"{resposta}: o erro puro foi pedido, mas {motivo}; os testes usaram o "
            "resíduo."
        )
        return None, None, "residuo"
    return sq / gl, gl, "erro_puro"


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
    planejamento: Planejamento,
    *,
    alfa: float,
    qm_erro: float | None = None,
    gl_erro: int | None = None,
    termo_erro: TermoErro = "residuo",
    descartados: Sequence[str] = (),
) -> AjusteResposta:
    """Empacota um ajuste OLS no contrato congelado `AjusteResposta`.

    Cada pedaço vem do seu módulo, que é a fonte única daquela conta:
    coeficientes (`effects`), ANOVA e falta de ajuste (`anova`), diagnóstico
    por ensaio (`diagnostico`) e equação (`equacao`).
    """
    fatores = planejamento.nomes_fatores
    falta = teste_falta_ajuste(dados, resposta, fatores, ajuste, alfa=alfa)
    coeficientes = extrair_coeficientes(
        ajuste, alfa=alfa, qm_erro=qm_erro, gl_erro=gl_erro
    )
    gl_teste = ajuste.gl_residuo if gl_erro is None else gl_erro
    y: NDArray[np.float64] = dados.coluna(resposta)
    return AjusteResposta(
        resposta=resposta,
        coeficientes=coeficientes,
        anova=_linhas_anova(resposta, ajuste, avisos, qm_erro, gl_erro),
        r2=ajuste.r2,
        r2_ajustado=ajuste.r2_ajustado,
        falta_de_ajuste=falta,
        n_observacoes=ajuste.n_observacoes,
        graus_liberdade_residuo=ajuste.gl_residuo,
        termos_incluidos=list(termos),
        termos_descartados=list(descartados),
        t_critico=t_critico(alfa, gl_teste),
        diagnostico=diagnosticar(y, ajuste.valores_ajustados, alfa=alfa),
        anova_regressao=anova_regressao(ajuste, falta, alfa=alfa),
        r2_predicao=ajuste.r2_predicao,
        equacao=montar_equacao(coeficientes, planejamento.fatores),
        termo_erro=termo_erro,
    )


def _linhas_anova(
    resposta: str,
    ajuste: AjusteOLS,
    avisos: list[str],
    qm_erro: float | None = None,
    gl_erro: int | None = None,
) -> list[LinhaAnova]:
    """ANOVA Tipo II em `LinhaAnova`, ou vazia se o modelo não é hierárquico.

    O `AjusteOLS` já devolve as linhas prontas; aqui só se traduz a recusa do
    modelo não hierárquico (um `ValueError`) num aviso que sobe ao relatório.
    """
    try:
        return ajuste.tabela_tipo2(qm_erro, gl_erro)
    except ValueError as erro:
        avisos.append(f"{resposta}: ANOVA Tipo II indisponível — {erro}")
        return []
