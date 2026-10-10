"""Superfície de resposta: avaliar o modelo ajustado numa grade de dois fatores.

Spec §9, grupo E: superfície 3D (E1) e curvas de contorno (E2). Os dois gráficos
mostram a MESMA coisa — a resposta prevista pelo modelo quando dois fatores
variam e os demais ficam parados num valor escolhido (por padrão, o centro).

A conta é só substituir valores na equação do modelo: para cada ponto da grade,
ŷ = Σ coeficiente × (produto dos fatores codificados de cada termo). Ela mora no
núcleo, e não na tela, pela regra de sempre: a interface desenha, não calcula.
A grade padrão é 25 × 25 (spec §7.3) — suficiente para o olho e barata para o
servidor de 512 MB.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from ensaia.core.design import INTERCEPTO, Fator, interpretar_termo
from ensaia.core.results import AjusteResposta, PontoEstacionario

PONTOS_PADRAO = 25


@dataclass(frozen=True)
class GradeSuperficie:
    """Resposta prevista numa grade regular de dois fatores (unidades reais).

    `z[i][j]` é a previsão em `x = valores_x[j]` e `y = valores_y[i]` — linha
    por valor de y, coluna por valor de x, como uma tabela lida de cima para
    baixo. `fixos` guarda, em unidades reais, onde os outros fatores ficaram.
    """

    resposta: str
    eixo_x: str
    eixo_y: str
    valores_x: list[float]
    valores_y: list[float]
    z: list[list[float]]
    fixos: dict[str, float]

    @property
    def z_minimo(self) -> float:
        return min(min(linha) for linha in self.z)

    @property
    def z_maximo(self) -> float:
        return max(max(linha) for linha in self.z)


def prever(
    ajuste: AjusteResposta, codificados: dict[str, NDArray[np.float64]]
) -> NDArray[np.float64]:
    """Resposta prevista pelo modelo em pontos dados na escala codificada.

    `codificados` mapeia cada fator para um array (todos do mesmo formato). Os
    termos são lidos por `interpretar_termo`, a mesma regra usada para montar a
    matriz do modelo — assim a previsão e o ajuste nunca discordam sobre o que
    "x1:x2" ou "x1^2" significam.
    """
    if not codificados:
        raise ValueError("Informe ao menos um fator para prever.")
    formato = next(iter(codificados.values())).shape
    total = np.zeros(formato, dtype=float)
    for coef in ajuste.coeficientes:
        parcela = np.full(formato, coef.estimativa, dtype=float)
        for nome, potencia in interpretar_termo(coef.termo):
            if nome not in codificados:
                raise ValueError(
                    f"O termo {coef.termo!r} usa o fator {nome!r}, que não foi "
                    f"informado. Fatores informados: {sorted(codificados)}."
                )
            parcela = parcela * codificados[nome] ** potencia
        total = total + parcela
    return total


def ponto_estacionario(
    ajuste: AjusteResposta,
    fatores: Sequence[Fator],
    *,
    limite_codificado: float = 1.0,
) -> PontoEstacionario | None:
    """Ponto estacionário e análise canônica do modelo quadrático (spec §9, E3).

    Escrevendo o modelo como ŷ = b₀ + xᵀb + xᵀBx (B com os quadráticos na
    diagonal e metade de cada interação fora dela), o gradiente zera em
    x_s = −½·B⁻¹·b, onde ŷ_s = b₀ + ½·x_sᵀb. Os autovalores de B classificam
    o ponto. Só faz sentido com o termo quadrático de todos os fatores; sem ele
    (ou com B singular) devolve None.

    `limite_codificado` é a borda da região experimental na escala codificada
    (1 no fatorial e no Box-Behnken; α no composto central).
    """
    nomes = [f.nome for f in fatores]
    k = len(nomes)
    estimativa = {c.termo: c.estimativa for c in ajuste.coeficientes}
    if k == 0 or any(f"{n}^2" not in estimativa for n in nomes):
        return None

    b = np.array([estimativa.get(n, 0.0) for n in nomes])
    matriz_b = np.zeros((k, k))
    for i, ni in enumerate(nomes):
        matriz_b[i, i] = estimativa[f"{ni}^2"]
        for j in range(i + 1, k):
            interacao = estimativa.get(
                f"{ni}:{nomes[j]}", estimativa.get(f"{nomes[j]}:{ni}", 0.0)
            )
            meio = interacao / 2.0
            matriz_b[i, j] = matriz_b[j, i] = meio
    if abs(np.linalg.det(matriz_b)) < 1e-12:
        return None

    x_s = -0.5 * np.linalg.solve(matriz_b, b)
    autovalores = np.linalg.eigvalsh(matriz_b)
    if np.all(autovalores < 0):
        natureza: Literal["maximo", "minimo", "sela"] = "maximo"
    elif np.all(autovalores > 0):
        natureza = "minimo"
    else:
        natureza = "sela"
    y_s = float(estimativa.get(INTERCEPTO, 0.0) + 0.5 * x_s @ b)
    return PontoEstacionario(
        codificado={n: float(v) for n, v in zip(nomes, x_s, strict=True)},
        real={
            f.nome: float(f.decodificar(v))
            for f, v in zip(fatores, x_s, strict=True)
        },
        natureza=natureza,
        autovalores=[float(v) for v in autovalores],
        resposta_prevista=y_s,
        dentro_da_regiao=bool(np.all(np.abs(x_s) <= limite_codificado + 1e-9)),
    )


def grade_superficie(
    ajuste: AjusteResposta,
    fatores: Sequence[Fator],
    eixo_x: str,
    eixo_y: str,
    *,
    fixos: dict[str, float] | None = None,
    pontos: int = PONTOS_PADRAO,
    limites_codificados: tuple[float, float] = (-1.0, 1.0),
) -> GradeSuperficie:
    """Avalia o modelo numa grade `pontos × pontos` dos fatores `eixo_x` e `eixo_y`.

    A grade cobre `limites_codificados` na escala codificada (padrão [−1, +1],
    a região do experimento) e é devolvida em unidades reais, que é o que o
    usuário entende. Os demais fatores ficam em `fixos` (unidades reais) ou, se
    omitidos, no centro da faixa.
    """
    por_nome = {f.nome: f for f in fatores}
    for nome in (eixo_x, eixo_y):
        if nome not in por_nome:
            raise ValueError(
                f"Fator {nome!r} não existe. Disponíveis: {sorted(por_nome)}."
            )
    if eixo_x == eixo_y:
        raise ValueError("Escolha dois fatores diferentes para os eixos.")
    if pontos < 2:
        raise ValueError("A grade precisa de ao menos 2 pontos por eixo.")

    fixos = dict(fixos or {})
    desconhecidos = sorted(set(fixos) - set(por_nome))
    if desconhecidos:
        raise ValueError(f"Fatores fixos desconhecidos: {desconhecidos}.")

    baixo, alto = limites_codificados
    eixo = np.linspace(baixo, alto, pontos)
    cx, cy = np.meshgrid(eixo, eixo)  # cx[i, j] = eixo[j]; cy[i, j] = eixo[i]

    codificados: dict[str, NDArray[np.float64]] = {eixo_x: cx, eixo_y: cy}
    fixos_reais: dict[str, float] = {}
    for fator in fatores:
        if fator.nome in (eixo_x, eixo_y):
            continue
        real = fixos.get(fator.nome, fator.centro)
        fixos_reais[fator.nome] = float(real)
        codificados[fator.nome] = np.full(cx.shape, fator.codificar(real))

    z = prever(ajuste, codificados)
    fx, fy = por_nome[eixo_x], por_nome[eixo_y]
    return GradeSuperficie(
        resposta=ajuste.resposta,
        eixo_x=eixo_x,
        eixo_y=eixo_y,
        valores_x=[float(fx.decodificar(v)) for v in eixo],
        valores_y=[float(fy.decodificar(v)) for v in eixo],
        z=[[float(v) for v in linha] for linha in z],
        fixos=fixos_reais,
    )
