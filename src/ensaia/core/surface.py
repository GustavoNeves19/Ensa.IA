"""Superfície de resposta, previsão e ponto estacionário do modelo.
Avalia a equação numa grade de dois fatores para os gráficos E1 e E2.
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
    """Resposta prevista numa grade de dois fatores, em unidades reais."""

    resposta: str
    eixo_x: str
    eixo_y: str
    valores_x: list[float]
    valores_y: list[float]
    z: list[list[float]]
    fixos: dict[str, float]

    @property
    def z_minimo(self) -> float:
        """Menor valor previsto na grade."""
        return min(min(linha) for linha in self.z)

    @property
    def z_maximo(self) -> float:
        """Maior valor previsto na grade."""
        return max(max(linha) for linha in self.z)


def prever(
    ajuste: AjusteResposta, codificados: dict[str, NDArray[np.float64]]
) -> NDArray[np.float64]:
    """Resposta prevista em pontos dados na escala codificada."""
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


def prever_condicao(
    ajustes: Sequence[AjusteResposta],
    fatores: Sequence[Fator],
    valores_reais: dict[str, float],
    *,
    limite_codificado: float = 1.0,
) -> tuple[dict[str, float], bool]:
    """Previsão numa condição real e se ela sai da região estudada."""
    faltam = sorted({f.nome for f in fatores} - set(valores_reais))
    if faltam:
        raise ValueError(f"Informe o valor de: {', '.join(faltam)}.")
    codificados = {
        f.nome: np.array([f.codificar(float(valores_reais[f.nome]))]) for f in fatores
    }
    extrapola = any(
        abs(float(v[0])) > limite_codificado + 1e-9 for v in codificados.values()
    )
    return {a.resposta: float(prever(a, codificados)[0]) for a in ajustes}, extrapola


def ponto_estacionario(
    ajuste: AjusteResposta,
    fatores: Sequence[Fator],
    *,
    limite_codificado: float = 1.0,
) -> PontoEstacionario | None:
    """Ponto estacionário e análise canônica (máximo, mínimo, sela)."""
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
    """Avalia o modelo numa grade de dois fatores."""
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


def ordem_por_forca(ajuste: AjusteResposta, nomes: list[str]) -> list[str]:
    """Fatores do mais ao menos influente, pelo maior |t|."""
    forca = dict.fromkeys(nomes, 0.0)
    for c in ajuste.coeficientes:
        if c.termo == INTERCEPTO:
            continue
        for nome, _ in interpretar_termo(c.termo):
            if nome in forca:
                forca[nome] = max(forca[nome], abs(c.valor_t))
    return sorted(nomes, key=lambda n: forca[n], reverse=True)


def par_inicial(ajuste: AjusteResposta, nomes: list[str]) -> tuple[str, str]:
    """Par de fatores que a superfície mostra primeiro."""
    interacoes = [
        c for c in ajuste.coeficientes
        if len({n for n, _ in interpretar_termo(c.termo)}) == 2
    ]
    if interacoes:
        melhor = max(interacoes, key=lambda c: abs(c.valor_t))
        a, b = list(dict.fromkeys(n for n, _ in interpretar_termo(melhor.termo)))
        return a, b
    ordem = ordem_por_forca(ajuste, nomes)
    return ordem[0], ordem[1]
