"""Monta um `AnalysisResult` a partir de dados + delineamento + termos.

É o fim-a-fim determinístico do núcleo (matriz do modelo → OLS → coeficientes,
ANOVA, falta de ajuste, diagnóstico e equação), empacotado no contrato congelado
`AnalysisResult`.

É a fonte única da conta para todas as portas: a interface web (que infere o
delineamento dos próprios dados), a validação (`validation/runner.py`, que lê os
parâmetros de `referencia.yaml`) e o servidor MCP. Todos chamam `analisar`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from ensaia.core.anova import anova_regressao, erro_puro, teste_falta_ajuste
from ensaia.core.catalogo import IDS
from ensaia.core.descritiva import estatistica_descritiva
from ensaia.core.design import Fator, Planejamento
from ensaia.core.desirability import metas_padrao, otimizar
from ensaia.core.diagnostico import diagnosticar
from ensaia.core.effects import extrair_coeficientes, t_critico
from ensaia.core.equacao import montar_equacao
from ensaia.core.fatorial import analisar_fatorial
from ensaia.core.identificacao import contar_pontos_centrais
from ensaia.core.model import AjusteOLS, ajustar_ols, matriz_modelo
from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    FatorCodificado,
    InfoPlanejamento,
    LinhaAnova,
    MetadadosExecucao,
    Sentido,
    TermoErro,
    TipoModelo,
)
from ensaia.core.surface import ponto_estacionario
from ensaia.core.table import Table
from ensaia.core.termos import reduzir_backward

ALFA_PADRAO = 0.05
# Spec §15: limites que evitam abuso de memória e modelos sem sentido.
MAX_FATORES = 7
MAX_RESPOSTAS = 5


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
    objetivos: Mapping[str, Sentido] | None = None,
    coluna_ordem: str | None = None,
    analises: Sequence[str] | None = None,
    alvos: Mapping[str, float] | None = None,
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
    - `analises` são os IDs marcados (spec §9; padrão: todos). Só registram a
      escolha: o que é barato é calculado sempre.
    - `coluna_ordem` (opcional) é a ordem de execução dos ensaios, para o
      gráfico de resíduos × ordem (spec §9, D3).
    - `objetivos` (maximizar, minimizar ou alvo por resposta; `alvos` traz o
      valor-alvo) aciona a busca da condição ótima dentro da região
      experimental (spec §9, E4/E5), com limites pelos valores observados.

    Levanta `ValueError` quando falta uma coluna exigida ou uma resposta tem
    valor ausente/não numérico — mensagens em português, prontas para virar aviso
    na interface.
    """
    fatores = planejamento.nomes_fatores
    desconhecidas = sorted(set(analises or ()) - set(IDS))
    if desconhecidas:
        raise ValueError(
            f"Análises desconhecidas: {desconhecidas}. Use os IDs {list(IDS)}."
        )
    if len(fatores) > MAX_FATORES:
        raise ValueError(
            f"O EnsaIA analisa até {MAX_FATORES} fatores por vez; foram "
            f"marcados {len(fatores)}. Deixe só os que você variou de propósito."
        )
    if len(respostas) > MAX_RESPOSTAS:
        raise ValueError(
            f"O EnsaIA analisa até {MAX_RESPOSTAS} respostas por vez; foram "
            f"marcadas {len(respostas)}."
        )
    exigidas = set(fatores) | set(respostas)
    ausentes = sorted(exigidas - set(tabela.colunas))
    if ausentes:
        raise ValueError(
            f"Colunas ausentes na planilha: {ausentes}. "
            f"Disponíveis: {list(tabela.colunas)}."
        )

    ajustes: list[AjusteResposta] = []
    avisos: list[str] = list(avisos_planejamento)
    limite = limite_da_regiao(planejamento)
    ordem = (
        [float(v) for v in tabela.coluna(coluna_ordem)] if coluna_ordem else None
    )
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
                limite_codificado=limite,
                ordem=ordem,
            )
        )

    ponto_otimo = None
    if objetivos:
        metas = metas_padrao(ajustes, objetivos, alvos)
        ponto_otimo, avisos_otimo = otimizar(
            ajustes, planejamento.fatores, metas, limite_codificado=limite
        )
        avisos.extend(avisos_otimo)

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
            analises=list(analises) if analises is not None else list(IDS),
        ),
        ponto_otimo=ponto_otimo,
        avisos=avisos,
        planejamento=info_planejamento(tabela, planejamento, avisos_planejamento),
        descritiva=estatistica_descritiva(tabela, [str(r) for r in respostas]),
    )


def limite_da_regiao(planejamento: Planejamento) -> float:
    """Borda da região experimental na escala codificada.

    ±α no composto central (os pontos axiais fazem parte da região estudada);
    ±1 nos demais planejamentos. É até onde o modelo pode ser usado sem
    extrapolar, e por isso é a caixa da busca do ótimo.
    """
    if planejamento.tipo == "composto_central" and planejamento.alfa_axial:
        return max(1.0, float(planejamento.alfa_axial))
    return 1.0


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


def fatores_do_contrato(info: InfoPlanejamento) -> list[Fator]:
    """Os fatores de volta a partir da seção `planejamento` do contrato.

    É o inverso de `info_planejamento`: quem só tem o `AnalysisResult` (o PDF,
    o servidor MCP) reconstrói a codificação sem reler a planilha.
    """
    return [
        Fator(f.nome, f.centro - f.passo, f.centro + f.passo, f.unidade)
        for f in info.fatores
    ]


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
    limite_codificado: float = 1.0,
    ordem: list[float] | None = None,
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
    ajuste_resposta = AjusteResposta(
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
        diagnostico=diagnosticar(
            y,
            ajuste.valores_ajustados,
            alfa=alfa,
            alavancagem=ajuste.alavancagem,
            n_parametros=ajuste.n_parametros,
            ordem=ordem,
        ),
        anova_regressao=anova_regressao(ajuste, falta, alfa=alfa),
        r2_predicao=ajuste.r2_predicao,
        equacao=montar_equacao(coeficientes, planejamento.fatores),
        termo_erro=termo_erro,
    )
    # Peças que leem o próprio AjusteResposta (coeficientes já com o termo de
    # erro escolhido): ponto estacionário (E3) e efeitos de fatorial (grupo B).
    sq_ep, gl_ep = erro_puro(dados, resposta, fatores)
    return ajuste_resposta.model_copy(
        update={
            "ponto_estacionario": ponto_estacionario(
                ajuste_resposta,
                planejamento.fatores,
                limite_codificado=limite_codificado,
            ),
            "efeitos_fatorial": analisar_fatorial(
                ajuste_resposta,
                dados,
                planejamento,
                alfa=alfa,
                qm_erro_puro=sq_ep / gl_ep if gl_ep > 0 else None,
                gl_erro_puro=gl_ep,
            ),
        }
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
