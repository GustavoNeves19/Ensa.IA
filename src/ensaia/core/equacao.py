"""Equação do modelo ajustado, na escala codificada e em unidades reais.
Formatada em pt-BR, com 4 algarismos significativos (C5).
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb, floor, log10

from ensaia.core.design import INTERCEPTO, Fator, interpretar_termo
from ensaia.core.results import Coeficiente, Equacao

_MENOS = "−"  # sinal de menos tipográfico (U+2212)

# Monômio como tupla de potências, na ordem dos fatores: (2, 0, 1) = x1²·x3.
Monomio = tuple[int, ...]


def montar_equacao(
    coeficientes: Sequence[Coeficiente], fatores: Sequence[Fator]
) -> Equacao:
    """Monta a equação codificada, só com significativos e em unidades reais."""
    nomes = [f.nome for f in fatores]
    variaveis = {f"X{i + 1}": nome for i, nome in enumerate(nomes)}
    simbolo = {nome: f"X{i + 1}" for i, nome in enumerate(nomes)}

    codificado: dict[Monomio, float] = {}
    for c in coeficientes:
        codificado[_monomio(c.termo, nomes)] = c.estimativa
    significativos = {
        _monomio(c.termo, nomes): c.estimativa
        for c in coeficientes
        if c.termo == INTERCEPTO or c.significativo
    }

    real = _para_unidades_reais(codificado, fatores)
    escala = max((abs(v) for v in real.values()), default=1.0) or 1.0
    real = {m: v for m, v in real.items() if abs(v) > 1e-12 * escala or not any(m)}

    return Equacao(
        codificada=_texto(codificado, [simbolo[n] for n in nomes]),
        real=_texto(real, nomes),
        significativos=_texto(significativos, [simbolo[n] for n in nomes]),
        variaveis=variaveis,
        coeficientes_reais={_nome_canonico(m, nomes): v for m, v in real.items()},
    )


def _monomio(termo: str, nomes: list[str]) -> Monomio:
    """Vetor de potências de um termo, na ordem dos fatores."""
    potencias = [0] * len(nomes)
    for nome, potencia in interpretar_termo(termo):
        potencias[nomes.index(nome)] += potencia
    return tuple(potencias)


def _para_unidades_reais(
    codificado: dict[Monomio, float], fatores: Sequence[Fator]
) -> dict[Monomio, float]:
    """Reescreve o polinômio codificado em unidades reais."""
    k = len(fatores)
    real: dict[Monomio, float] = {}
    for monomio, beta in codificado.items():
        parcial: dict[Monomio, float] = {(0,) * k: beta}
        for j, potencia in enumerate(monomio):
            if potencia == 0:
                continue
            centro = fatores[j].centro
            passo = fatores[j].amplitude / 2.0
            # ((x − c)/s)^p = Σ_i C(p, i)·x^i·(−c)^(p−i) / s^p
            binomio = {
                i: comb(potencia, i) * (-centro) ** (potencia - i) / passo**potencia
                for i in range(potencia + 1)
            }
            novo: dict[Monomio, float] = {}
            for m, v in parcial.items():
                for i, fator_binomio in binomio.items():
                    chave = tuple(e + (i if idx == j else 0) for idx, e in enumerate(m))
                    novo[chave] = novo.get(chave, 0.0) + v * fator_binomio
            parcial = novo
        for m, v in parcial.items():
            real[m] = real.get(m, 0.0) + v
    return real


def _ordem(monomio: Monomio) -> tuple[int, int, tuple[int, ...]]:
    """Chave de ordenação: constante, lineares, quadráticos, interações."""
    grau = sum(monomio)
    distintos = sum(1 for p in monomio if p)
    return (grau, distintos, tuple(-p for p in monomio))


def _texto(termos: dict[Monomio, float], simbolos: Sequence[str]) -> str:
    """Escreve o polinômio como texto (ŷ = b₀ + ...)."""
    partes: list[str] = []
    for monomio in sorted(termos, key=_ordem):
        valor = termos[monomio]
        nome = _nome_legivel(monomio, simbolos)
        numero = _sig4(abs(valor))
        corpo = f"{numero}·{nome}" if nome else numero
        if not partes:
            partes.append(f"{_MENOS}{corpo}" if valor < 0 else corpo)
        else:
            partes.append(f"{_MENOS if valor < 0 else '+'} {corpo}")
    return "ŷ = " + " ".join(partes) if partes else "ŷ = 0"


def _nome_legivel(monomio: Monomio, simbolos: Sequence[str]) -> str:
    """Nome de um monômio com os símbolos dados (X₁·X₂, X₁²)."""
    sobrescrito = {2: "²", 3: "³"}
    return "·".join(
        simbolos[j] + sobrescrito.get(p, f"^{p}" if p > 1 else "")
        for j, p in enumerate(monomio)
        if p
    )


def _nome_canonico(monomio: Monomio, nomes: Sequence[str]) -> str:
    """Nome canônico de um monômio (x1:x2, x1^2)."""
    if not any(monomio):
        return INTERCEPTO
    return ":".join(
        nomes[j] if p == 1 else f"{nomes[j]}^{p}" for j, p in enumerate(monomio) if p
    )


def _sig4(valor: float) -> str:
    """Número com 4 algarismos significativos e vírgula decimal."""
    if valor == 0:
        return "0"
    casas = max(0, 3 - floor(log10(valor)))
    return f"{valor:.{casas}f}".replace(".", ",")
