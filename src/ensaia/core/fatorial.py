"""Análise de fatoriais de 2 níveis: efeitos, Lenth, curvatura e médias (spec §9, B).

Os fatoriais 2^k e 2^(k−p) são o planejamento de triagem: servem para descobrir
quais fatores importam antes de investir num planejamento maior. Por isso a
leitura é por **efeitos** (quanto a resposta muda de −1 a +1), e há ferramentas
próprias para eles:

- **Efeitos** (B1): 2 × coeficiente codificado, com o mesmo t e p.
- **Lenth** (B3): sem réplicas não há erro puro; o método de Lenth (1989)
  estima um pseudo erro-padrão a partir dos próprios efeitos, supondo que a
  maioria é ruído. O gráfico meio-normal mostra os que destoam.
- **Médias por nível** (B4): os gráficos de efeito principal e de interação.
- **Curvatura** (B5): com pontos centrais, compara o centro com os vértices; se
  diferem, a superfície curva e o modelo linear não basta.
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
    """Grupo B da spec para uma resposta; None se o planejamento não é 2^k.

    `com_replicas` diz se alguma condição foi repetida (sem olhar blocos); por
    padrão, se há erro puro. Com blocos os dois diferem: réplicas em blocos
    diferentes não dão erro puro, mas continuam sendo réplicas — e com elas o
    teste t do Pareto, e não o Lenth, é o instrumento certo.
    """
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
    # Lenth só sem réplicas (spec §9, B3): com erro puro, o teste t do Pareto
    # é o instrumento certo, e as duas leituras poderiam se contradizer.
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
    """Pseudo erro-padrão de Lenth (1989) e as margens ME e SME.

        s₀  = 1,5 · mediana(|e|)
        PSE = 1,5 · mediana(|e| : |e| < 2,5·s₀)
        ME  = t(0,975; m/3) · PSE
        SME = t(γ; m/3) · PSE,  γ = (1 + 0,95^(1/m)) / 2

    Precisa de ao menos 3 efeitos; devolve None com menos ou com todos nulos.
    """
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
    """SQ_curv = n_F·n_C·(ȳ_F − ȳ_C)² / (n_F + n_C), testado contra o erro puro."""
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
    """Gráfico meio-normal dos efeitos: |efeito| contra o quantil esperado."""

    termos: list[str]
    absolutos: list[float]
    quantis: list[float]


def pontos_meio_normal(efeitos: list[Efeito]) -> PontosMeioNormal:
    """Quantis meio-normais Φ⁻¹(0,5 + 0,5·(i − 0,5)/m) para os |efeitos| ordenados."""
    ordenados = sorted(efeitos, key=lambda e: abs(e.efeito))
    m = len(ordenados)
    posicoes = 0.5 + 0.5 * (np.arange(1, m + 1) - 0.5) / m
    return PontosMeioNormal(
        termos=[e.termo for e in ordenados],
        absolutos=[abs(e.efeito) for e in ordenados],
        quantis=[float(v) for v in stats.norm.ppf(posicoes)],
    )


def _sem_quadratico(termo: str) -> bool:
    return all(potencia == 1 for _, potencia in interpretar_termo(termo))


def _matriz_codificada(dados: Table, planejamento: Planejamento) -> NDArray[np.float64]:
    return np.column_stack(
        [
            [f.codificar(float(v)) for v in dados.coluna(f.nome)]
            for f in planejamento.fatores
        ]
    )


def _medias_nivel(
    fator: str, valores: NDArray[np.float64], y: NDArray[np.float64]
) -> MediasNivel:
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
    """Médias por combinação; None se alguma combinação não foi ensaiada."""
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
