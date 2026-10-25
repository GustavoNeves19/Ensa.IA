"""Otimização: melhor condição de uma resposta ou de várias (desejabilidade).
Função de Derringer-Suich para maximizar, minimizar ou atingir um alvo.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ensaia.core.design import Fator
from ensaia.core.results import AjusteResposta, PontoOtimo, Sentido
from ensaia.core.surface import prever

# Abaixo deste R², o modelo não serve para otimizar (vira aviso).
R2_MINIMO_PARA_OTIMIZAR = 0.50


@dataclass(frozen=True)
class AlvoResposta:
    """Meta de uma resposta: sentido, limites, alvo, forma e peso."""

    resposta: str
    sentido: Sentido
    limite_inferior: float
    limite_superior: float
    alvo: float | None = None
    peso: float = 1.0
    s: float = 1.0

    def __post_init__(self) -> None:
        """Valida limites, alvo, forma e peso da meta."""
        if self.limite_superior <= self.limite_inferior:
            raise ValueError(
                f"Resposta {self.resposta!r}: limite_superior deve ser maior "
                f"que limite_inferior."
            )
        if self.s <= 0:
            raise ValueError(
                f"Resposta {self.resposta!r}: a forma 's' deve ser positiva "
                f"(recebido {self.s})."
            )
        if self.peso <= 0:
            raise ValueError(
                f"Resposta {self.resposta!r}: o peso deve ser positivo "
                f"(recebido {self.peso})."
            )
        if self.sentido == "alvo":
            if self.alvo is None:
                raise ValueError(
                    f"Resposta {self.resposta!r} tem sentido 'alvo' mas nenhum "
                    f"valor-alvo foi informado."
                )
            if not self.limite_inferior < self.alvo < self.limite_superior:
                raise ValueError(
                    f"Resposta {self.resposta!r}: o alvo {self.alvo} precisa ficar "
                    f"estritamente entre os limites "
                    f"({self.limite_inferior}, {self.limite_superior})."
                )


def desejabilidade_individual(valor: float, alvo: AlvoResposta) -> float:
    """Desejabilidade d (0 a 1) de um valor previsto para uma meta."""
    inf = alvo.limite_inferior
    sup = alvo.limite_superior
    s = alvo.s

    if alvo.sentido == "maximizar":
        if valor <= inf:
            return 0.0
        if valor >= sup:
            return 1.0
        return float(((valor - inf) / (sup - inf)) ** s)

    if alvo.sentido == "minimizar":
        if valor <= inf:
            return 1.0
        if valor >= sup:
            return 0.0
        return float(((sup - valor) / (sup - inf)) ** s)

    # sentido == "alvo"; __post_init__ garante inf < alvo.alvo < sup.
    pico = alvo.alvo
    assert pico is not None  # garantido por AlvoResposta.__post_init__
    if valor < inf or valor > sup:
        return 0.0
    if valor <= pico:
        return float(((valor - inf) / (pico - inf)) ** s)
    return float(((sup - valor) / (sup - pico)) ** s)


def desejabilidade_global(individuais: list[float], pesos: list[float]) -> float:
    """Desejabilidade global D: média geométrica ponderada dos d."""
    if len(individuais) != len(pesos):
        raise ValueError(
            f"Número de desejabilidades ({len(individuais)}) difere do de pesos "
            f"({len(pesos)})."
        )
    if not individuais:
        raise ValueError("É preciso ao menos uma desejabilidade para compor D.")
    if any(d < 0.0 or d > 1.0 for d in individuais):
        raise ValueError("Cada desejabilidade individual deve estar em [0, 1].")
    if any(p <= 0.0 for p in pesos):
        raise ValueError("Todos os pesos devem ser positivos.")

    if any(d == 0.0 for d in individuais):
        return 0.0

    soma_pesos = sum(pesos)
    log_medio = (
        sum(p * math.log(d) for d, p in zip(individuais, pesos, strict=True))
        / soma_pesos
    )
    return math.exp(log_medio)


def desejabilidade_vetor(
    valores: NDArray[np.float64], alvo: AlvoResposta
) -> NDArray[np.float64]:
    """Desejabilidade individual para muitos pontos de uma vez."""
    y = np.asarray(valores, dtype=float)
    inf, sup, s = alvo.limite_inferior, alvo.limite_superior, alvo.s
    if alvo.sentido == "maximizar":
        return np.clip((y - inf) / (sup - inf), 0.0, 1.0) ** s
    if alvo.sentido == "minimizar":
        return np.clip((sup - y) / (sup - inf), 0.0, 1.0) ** s
    pico = alvo.alvo
    assert pico is not None
    subida = np.clip((y - inf) / (pico - inf), 0.0, 1.0) ** s
    descida = np.clip((sup - y) / (sup - pico), 0.0, 1.0) ** s
    return np.where((y < inf) | (y > sup), 0.0, np.where(y <= pico, subida, descida))


def metas_padrao(
    ajustes: Sequence[AjusteResposta],
    sentidos: Mapping[str, Sentido],
    alvos: Mapping[str, float] | None = None,
) -> list[AlvoResposta]:
    """Metas com os limites no menor e no maior valor observado."""
    alvos = alvos or {}
    metas: list[AlvoResposta] = []
    for ajuste in ajustes:
        sentido = sentidos.get(ajuste.resposta)
        if sentido is None or ajuste.diagnostico is None:
            continue
        observados = ajuste.diagnostico.observados
        baixo, alto = min(observados), max(observados)
        if alto <= baixo:
            continue
        metas.append(
            AlvoResposta(
                resposta=ajuste.resposta,
                sentido=sentido,
                limite_inferior=baixo,
                limite_superior=alto,
                alvo=alvos.get(ajuste.resposta),
            )
        )
    return metas


def otimizar(
    ajustes: Sequence[AjusteResposta],
    fatores: Sequence[Fator],
    metas: Sequence[AlvoResposta],
    *,
    limite_codificado: float = 1.0,
    r2_minimo: float = R2_MINIMO_PARA_OTIMIZAR,
) -> tuple[PontoOtimo | None, list[str]]:
    """Busca a melhor condição dentro da região estudada (E4 e E5)."""
    # Importação tardia: scipy.optimize só carrega quando se pede o ótimo.
    from scipy.optimize import minimize

    avisos: list[str] = []
    por_nome = {a.resposta: a for a in ajustes}
    metas = [m for m in metas if m.resposta in por_nome]
    if not metas:
        return None, avisos
    fracos = [m.resposta for m in metas if por_nome[m.resposta].r2 < r2_minimo]
    if fracos:
        avisos.append(
            "Otimização não feita: o modelo de "
            f"{', '.join(fracos)} tem R² abaixo de {r2_minimo:.2f}".replace(".", ",")
            + " e não descreve os dados bem o bastante para apontar um ótimo."
        )
        return None, avisos

    nomes = [f.nome for f in fatores]
    k = len(nomes)
    direto = len(metas) == 1 and metas[0].sentido != "alvo"

    def respostas(pontos: NDArray[np.float64]) -> dict[str, NDArray[np.float64]]:
        """Respostas previstas pelos modelos nos pontos dados."""
        colunas = {n: pontos[:, j] for j, n in enumerate(nomes)}
        return {m.resposta: prever(por_nome[m.resposta], colunas) for m in metas}

    def custo(pontos: NDArray[np.float64]) -> NDArray[np.float64]:
        """Valor a minimizar na busca: −ŷ, ŷ ou −log D."""
        previstas = respostas(pontos)
        if direto:
            y = previstas[metas[0].resposta]
            return -y if metas[0].sentido == "maximizar" else y
        individuais = np.column_stack(
            [desejabilidade_vetor(previstas[m.resposta], m) for m in metas]
        )
        pesos = np.array([m.peso for m in metas])
        # Média geométrica ponderada; o piso evita log(0).
        log_d = np.log(np.maximum(individuais, 1e-300))
        global_ = np.exp((log_d * pesos).sum(axis=1) / pesos.sum())
        return -np.where(np.any(individuais == 0, axis=1), 0.0, global_)

    malha = _malha(k, limite_codificado)
    valores = custo(malha)
    ordem = np.argsort(valores, kind="stable")[:5]
    limites = [(-limite_codificado, limite_codificado)] * k
    melhor_x, melhor_v = malha[ordem[0]], float(valores[ordem[0]])
    for indice in ordem:
        resultado = minimize(
            lambda x: float(custo(x.reshape(1, -1))[0]),
            malha[indice],
            method="L-BFGS-B" if direto else "Powell",
            bounds=limites,
        )
        x = np.clip(resultado.x, -limite_codificado, limite_codificado)
        v = float(custo(x.reshape(1, -1))[0])
        if v < melhor_v - 1e-12:
            melhor_x, melhor_v = x, v

    previstas = respostas(melhor_x.reshape(1, -1))
    individuais = {
        m.resposta: float(desejabilidade_vetor(previstas[m.resposta], m)[0])
        for m in metas
    }
    global_d = desejabilidade_global(
        list(individuais.values()), [m.peso for m in metas]
    )
    if not direto and global_d == 0.0:
        avisos.append(
            "Nenhuma condição da região atende a todas as metas ao mesmo tempo "
            "(desejabilidade global = 0)."
        )
    ponto = PontoOtimo(
        coordenadas={
            f.nome: float(f.decodificar(v))
            for f, v in zip(fatores, melhor_x, strict=True)
        },
        coordenadas_codificadas={
            n: float(v) for n, v in zip(nomes, melhor_x, strict=True)
        },
        resposta_prevista={r: float(v[0]) for r, v in previstas.items()},
        desejabilidade_global=global_d,
        desejabilidades_individuais=individuais,
        metas={m.resposta: m.sentido for m in metas},
        metodo="resposta_unica" if direto else "desejabilidade",
        limite_codificado=limite_codificado,
    )
    return ponto, avisos


def _malha(k: int, limite: float) -> NDArray[np.float64]:
    """Pontos de partida da busca: malha regular ou amostra fixa."""
    if k <= 4:
        por_fator = {1: 201, 2: 41, 3: 21, 4: 11}[k]
        eixo = np.linspace(-limite, limite, por_fator)
        return np.array(np.meshgrid(*([eixo] * k), indexing="ij")).reshape(k, -1).T
    rng = np.random.default_rng(20261010)  # semente fixa: busca reprodutível
    return rng.uniform(-limite, limite, size=(4000, k))
