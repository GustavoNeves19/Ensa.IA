"""Análises de fatoriais de 2 níveis: efeitos, Lenth, curvatura e médias.
Fora do escopo DCCR (ADR 0013/0015): fica no código, sem uso na tela nem no PDF.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from ensaia.core.design import INTERCEPTO, Planejamento, interpretar_termo
from ensaia.core.results import (
    AjusteResposta,
    AnaliseLenth,
    Efeito,
    EfeitosFatorial,
    MediasInteracao,
    MediasNivel,
    TesteCurvatura,
)
from ensaia.core.table import Table

FATORIAIS = ("fatorial_completo", "fatorial_fracionado")
_TOL = 0.02


def analisar_fatorial(
    ajuste: AjusteResposta,
    dados: Table,
    planejamento: Planejamento,
    *,
    alfa: float,
    qm_erro_puro: float | None,
    gl_erro_puro: int,
    com_replicas: bool | None = None,
) -> EfeitosFatorial | None:
    """Análises do grupo B para uma resposta; None se não for fatorial."""
    if com_replicas is None:
        com_replicas = gl_erro_puro > 0
    if planejamento.tipo not in FATORIAIS:
        return None

    efeitos = [
        Efeito(
            termo=c.termo,
            efeito=2.0 * c.estimativa,
            erro_padrao=2.0 * c.erro_padrao,
            valor_t=c.valor_t,
            valor_p=c.valor_p,
            significativo=c.significativo,
        )
        for c in ajuste.coeficientes
        if c.termo != INTERCEPTO and _sem_quadratico(c.termo)
    ]
    # Lenth só sem réplicas; com erro puro vale o teste t.
    lenth = analise_lenth([e.efeito for e in efeitos]) if not com_replicas else None
    if lenth is not None:
        efeitos = [
            e.model_copy(update={"ativo_lenth": abs(e.efeito) > lenth.me})
            for e in efeitos
        ]

    codificada = _matriz_codificada(dados, planejamento)
    y = np.asarray(dados.coluna(ajuste.resposta), dtype=float)
    vertices = np.all(np.abs(np.abs(codificada) - 1.0) < _TOL, axis=1)
    return EfeitosFatorial(
        efeitos=efeitos,
        lenth=lenth,
        curvatura=teste_curvatura(
            codificada,
            y,
            alfa=alfa,
            qm_erro_puro=qm_erro_puro,
            gl_erro_puro=gl_erro_puro,
        ),
        medias_principais=[
            _medias_nivel(f.nome, dados.coluna(f.nome)[vertices], y[vertices])
            for f in planejamento.fatores
        ],
        medias_interacoes=[
            interacao
            for a, b in combinations(planejamento.fatores, 2)
            if (
                interacao := _medias_interacao(
                    a.nome,
                    b.nome,
                    dados.coluna(a.nome)[vertices],
                    dados.coluna(b.nome)[vertices],
                    y[vertices],
                )
            )
            is not None
        ],
    )


def analise_lenth(efeitos: list[float]) -> AnaliseLenth | None:
    """Pseudo erro-padrão de Lenth e as margens ME e SME."""
    absolutos = np.abs(np.asarray(efeitos, dtype=float))
    m = absolutos.size
    if m < 3:
        return None
    s0 = 1.5 * float(np.median(absolutos))
    pequenos = absolutos[absolutos < 2.5 * s0]
    if s0 == 0.0 or pequenos.size == 0:
        return None
    pse = 1.5 * float(np.median(pequenos))
    gl = m / 3.0
    gama = (1.0 + 0.95 ** (1.0 / m)) / 2.0
    return AnaliseLenth(
        pse=pse,
        me=float(stats.t.ppf(0.975, gl)) * pse,
        sme=float(stats.t.ppf(gama, gl)) * pse,
        graus_liberdade=gl,
    )


def teste_curvatura(
    codificada: NDArray[np.float64],
    y: NDArray[np.float64],
    *,
    alfa: float,
    qm_erro_puro: float | None,
    gl_erro_puro: int,
) -> TesteCurvatura:
    """Compara a média do centro com a dos vértices (curvatura)."""
    centro = np.all(np.abs(codificada) < _TOL, axis=1)
    vertices = np.all(np.abs(np.abs(codificada) - 1.0) < _TOL, axis=1)
    n_c, n_f = int(centro.sum()), int(vertices.sum())
    if n_c < 2:
        return TesteCurvatura(
            aplicavel=False,
            motivo_inaplicavel="o teste exige ao menos 2 ensaios no ponto central",
        )
    media_f, media_c = float(y[vertices].mean()), float(y[centro].mean())
    sq = n_f * n_c * (media_f - media_c) ** 2 / (n_f + n_c)
    if qm_erro_puro is None or qm_erro_puro <= 0.0 or gl_erro_puro <= 0:
        return TesteCurvatura(
            aplicavel=False,
            media_fatorial=media_f,
            media_central=media_c,
            soma_quadrados=sq,
            motivo_inaplicavel="os pontos centrais não variam (erro puro nulo)",
        )
    f = sq / qm_erro_puro
    p = float(stats.f.sf(f, 1, gl_erro_puro))
    return TesteCurvatura(
        aplicavel=True,
        media_fatorial=media_f,
        media_central=media_c,
        soma_quadrados=sq,
        valor_f=f,
        valor_p=p,
        significativa=p < alfa,
    )


@dataclass(frozen=True)
class PontosMeioNormal:
    """Pontos do gráfico meio-normal dos efeitos."""

    termos: list[str]
    absolutos: list[float]
    quantis: list[float]


def pontos_meio_normal(efeitos: list[Efeito]) -> PontosMeioNormal:
    """Calcula os quantis meio-normais dos |efeitos| ordenados."""
    ordenados = sorted(efeitos, key=lambda e: abs(e.efeito))
    m = len(ordenados)
    posicoes = 0.5 + 0.5 * (np.arange(1, m + 1) - 0.5) / m
    return PontosMeioNormal(
        termos=[e.termo for e in ordenados],
        absolutos=[abs(e.efeito) for e in ordenados],
        quantis=[float(v) for v in stats.norm.ppf(posicoes)],
    )


def _sem_quadratico(termo: str) -> bool:
    """Diz se um termo não tem potência acima de 1."""
    return all(potencia == 1 for _, potencia in interpretar_termo(termo))


def _matriz_codificada(dados: Table, planejamento: Planejamento) -> NDArray[np.float64]:
    """Matriz dos fatores na escala codificada."""
    return np.column_stack(
        [
            [f.codificar(float(v)) for v in dados.coluna(f.nome)]
            for f in planejamento.fatores
        ]
    )


def _medias_nivel(
    fator: str, valores: NDArray[np.float64], y: NDArray[np.float64]
) -> MediasNivel:
    """Média da resposta em cada nível de um fator."""
    niveis = sorted({float(v) for v in valores})
    return MediasNivel(
        fator=fator,
        niveis=niveis,
        medias=[float(y[valores == nivel].mean()) for nivel in niveis],
    )


def _medias_interacao(
    fator_a: str,
    fator_b: str,
    valores_a: NDArray[np.float64],
    valores_b: NDArray[np.float64],
    y: NDArray[np.float64],
) -> MediasInteracao | None:
    """Médias por combinação de dois fatores; None se faltar alguma."""
    niveis_a = sorted({float(v) for v in valores_a})
    niveis_b = sorted({float(v) for v in valores_b})
    medias: list[list[float]] = []
    for nb in niveis_b:
        linha: list[float] = []
        for na in niveis_a:
            mascara = (valores_a == na) & (valores_b == nb)
            if not np.any(mascara):
                return None
            linha.append(float(y[mascara].mean()))
        medias.append(linha)
    return MediasInteracao(
        fator_a=fator_a,
        fator_b=fator_b,
        niveis_a=niveis_a,
        niveis_b=niveis_b,
        medias=medias,
    )
