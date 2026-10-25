"""Fim a fim do núcleo: dados + planejamento + termos → AnalysisResult.
Fonte única da conta para a tela, a validação e o MCP.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from ensaia.core.anova import anova_regressao, erro_puro, teste_falta_ajuste
from ensaia.core.blocos import Blocos, com_blocos, ler_blocos
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
    ordem_execucao: Sequence[int] | None = None,
    analises: Sequence[str] | None = None,
    alvos: Mapping[str, float] | None = None,
    coluna_bloco: str | None = None,
) -> AnalysisResult:
    """Ajusta o modelo a cada resposta e devolve o resultado congelado."""
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

    if coluna_bloco is not None and coluna_bloco in exigidas:
        raise ValueError(
            f"A coluna {coluna_bloco!r} não pode ser bloco e fator/resposta ao "
            "mesmo tempo."
        )
    blocos = ler_blocos(tabela, coluna_bloco) if coluna_bloco else None
    fixos = blocos.nomes_colunas if blocos is not None else []
    rotulos = list(blocos.rotulos) if blocos is not None else None

    ajustes: list[AjusteResposta] = []
    avisos: list[str] = list(avisos_planejamento)
    limite = limite_da_regiao(planejamento)
    if coluna_ordem:
        ordem = [float(v) for v in tabela.coluna(coluna_ordem)]
    elif ordem_execucao is not None:
        ordem = [float(v) for v in ordem_execucao]
    else:
        ordem = None
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
            tabela, resposta, fatores, termo_erro, avisos, rotulos
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
                blocos=blocos,
            )
        matriz = com_blocos(
            matriz_modelo(tabela, planejamento, termos_resposta, codificar=True),
            blocos,
        )
        ajuste = ajustar_ols(matriz, y, fixos=fixos)
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
                blocos=blocos,
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
        planejamento=info_planejamento(
            tabela, planejamento, avisos_planejamento, blocos
        ),
        descritiva=estatistica_descritiva(tabela, [str(r) for r in respostas]),
    )


def limite_da_regiao(planejamento: Planejamento) -> float:
    """Borda da região estudada na escala codificada (±α no DCCR)."""
    if planejamento.tipo == "composto_central" and planejamento.alfa_axial:
        return max(1.0, float(planejamento.alfa_axial))
    return 1.0


def _termo_de_erro(
    tabela: Table,
    resposta: str,
    fatores: list[str],
    pedido: TermoErro,
    avisos: list[str],
    blocos: Sequence[str] | None = None,
) -> tuple[float | None, int | None, TermoErro]:
    """Quadrado médio e g.l. do erro usado nos testes."""
    if pedido == "residuo":
        return None, None, "residuo"
    sq, gl = erro_puro(tabela, resposta, fatores, blocos)
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
    tabela: Table,
    planejamento: Planejamento,
    avisos: Sequence[str] = (),
    blocos: Blocos | None = None,
) -> InfoPlanejamento:
    """Seção do contrato com a geometria e a codificação dos fatores."""
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
        coluna_bloco=blocos.coluna if blocos is not None else None,
        n_blocos=blocos.n_blocos if blocos is not None else None,
    )


def fatores_do_contrato(info: InfoPlanejamento) -> list[Fator]:
    """Reconstrói os fatores a partir do contrato."""
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
    blocos: Blocos | None = None,
) -> AjusteResposta:
    """Empacota o ajuste de uma resposta no contrato AjusteResposta."""
    fatores = planejamento.nomes_fatores
    rotulos = list(blocos.rotulos) if blocos is not None else None
    falta = teste_falta_ajuste(
        dados, resposta, fatores, ajuste, alfa=alfa, blocos=rotulos
    )
    coeficientes = extrair_coeficientes(
        ajuste, alfa=alfa, qm_erro=qm_erro, gl_erro=gl_erro
    )
    gl_teste = ajuste.gl_residuo if gl_erro is None else gl_erro
    y: NDArray[np.float64] = dados.coluna(resposta)
    r2_maximo = (
        (ajuste.soma_quadrados_total - falta.soma_quadrados_erro_puro)
        / ajuste.soma_quadrados_total
        if falta.aplicavel and falta.soma_quadrados_erro_puro is not None
        else None
    )
    ajuste_resposta = AjusteResposta(
        resposta=resposta,
        coeficientes=coeficientes,
        anova=_linhas_anova(resposta, ajuste, avisos, qm_erro, gl_erro),
        r2=ajuste.r2,
        r2_ajustado=ajuste.r2_ajustado,
        r2_maximo=r2_maximo,
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
        efeitos_bloco=(
            blocos.efeitos(ajuste.coeficientes) if blocos is not None else {}
        ),
    )
    # Peças que leem o próprio AjusteResposta: ponto estacionário e grupo B.
    sq_ep, gl_ep = erro_puro(dados, resposta, fatores, rotulos)
    _, gl_replicas = erro_puro(dados, resposta, fatores)
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
                com_replicas=gl_replicas > 0,
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
    """ANOVA Tipo II em linhas do contrato, ou vazia com aviso."""
    try:
        return ajuste.tabela_tipo2(qm_erro, gl_erro)
    except ValueError as erro:
        avisos.append(f"{resposta}: ANOVA Tipo II indisponível — {erro}")
        return []
