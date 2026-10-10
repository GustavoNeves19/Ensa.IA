"""Otimização multirresposta pela função de desejabilidade de Derringer-Suich.

Quarto item do pipeline prometido no pré-projeto. Diferente do protótipo
inicial, que só maximizava, esta implementação precisa cobrir os três sentidos
(maximizar, minimizar, alvo) — casos de estudo reais de química quase sempre
têm ao menos uma resposta a minimizar, como teor de impureza ou tempo de
processo.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from ensaia.core.design import Fator
from ensaia.core.results import AjusteResposta, PontoOtimo, Sentido
from ensaia.core.surface import prever

# Abaixo deste R², o modelo não descreve os dados bem o bastante para que
# otimizar sobre ele signifique alguma coisa. O protótipo usava 0,50; o valor
# fica configurável e o bloqueio é reportado como aviso no AnalysisResult,
# nunca silenciosamente.
R2_MINIMO_PARA_OTIMIZAR = 0.50


@dataclass(frozen=True)
class AlvoResposta:
    """O que se quer de cada resposta na otimização.

    `s` é o parâmetro de forma de Derringer-Suich: controla a curvatura da
    transição entre inaceitável (d=0) e ideal (d=1). Com `s = 1` a subida é
    linear; `s > 1` exige chegar perto do ideal para a desejabilidade crescer
    (mais rigoroso); `0 < s < 1` recompensa já qualquer melhora (mais tolerante).
    O default 1,0 reproduz a forma linear, que é a dos casos de estudo usados na
    validação. Para o sentido 'alvo', a mesma forma `s` vale nos dois lados.

    `peso` pondera esta resposta na média geométrica global (não é a forma `s`):
    uma resposta com peso maior puxa mais a desejabilidade composta.
    """

    resposta: str
    sentido: Sentido
    limite_inferior: float
    limite_superior: float
    alvo: float | None = None
    peso: float = 1.0
    s: float = 1.0

    def __post_init__(self) -> None:
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
    """d_i em [0, 1] para uma resposta, pelas formas de Derringer-Suich (1980).

    As três formas, com L = limite inferior, U = limite superior, T = alvo e
    s = parâmetro de forma:

        maximizar  0 se y <= L;  ((y-L)/(U-L))^s se L < y < U;  1 se y >= U
        minimizar  1 se y <= L;  ((U-y)/(U-L))^s se L < y < U;  0 se y >= U
        alvo       0 fora de [L, U];
                   ((y-L)/(T-L))^s   se L <= y <= T   (sobe até 1 no alvo)
                   ((U-y)/(U-T))^s   se T <  y <= U   (desce depois)

    Fora da faixa o valor é *saturado*, não extrapolado: uma resposta melhor que
    o limite superior num problema de maximizar vale 1, nunca mais que 1. Isso é
    o que torna a desejabilidade comparável entre respostas de escalas diferentes
    — é o ponto da transformação.
    """
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
    """D = média geométrica ponderada das desejabilidades individuais.

        D = (Π d_i^{w_i})^{1 / Σ w_i}

    Média geométrica, não aritmética: se qualquer resposta for inaceitável
    (d_i = 0), D tem que zerar. Com média aritmética, uma resposta péssima seria
    compensada por outras boas, e o otimizador recomendaria uma condição que
    viola um requisito — exatamente o tipo de erro que um usuário sem formação
    em estatística não teria como perceber no relatório. O veto (qualquer d_i = 0
    ⇒ D = 0) é tratado explicitamente, antes de cair no log, porque ln(0) = −∞.
    """
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
    """`desejabilidade_individual` aplicada a muitos pontos de uma vez (numpy).

    Mesmas formas e mesma saturação; existe para a busca do ótimo avaliar a
    malha inteira sem laço em Python.
    """
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
    """Metas com os limites usuais: o menor e o maior valor observado.

    É o padrão de softwares como o Design-Expert: a desejabilidade vai de 0 no
    pior valor observado a 1 no melhor. Respostas fora de `sentidos` ficam de
    fora da otimização.
    """
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
    """Busca a melhor condição dentro da região experimental (spec §9, E4/E5).

    - **Uma resposta a maximizar ou minimizar (E4):** otimiza a própria
      resposta prevista. A desejabilidade satura em 1 e deixaria o ótimo
      indefinido no platô; a resposta não satura.
    - **Várias respostas, ou uma com alvo (E5):** maximiza a desejabilidade
      global de Derringer e Suich.

    A região é a caixa [−limite, +limite] na escala codificada (±1 no fatorial
    e no Box-Behnken, ±α no composto central). Busca determinística: malha
    regular (ou amostra fixa quando há muitos fatores) e refinamento local a
    partir dos 5 melhores pontos dela; o resultado se repete byte a byte, o que
    o §4.3(d) exige para comparar com o artigo.

    Devolve `(ponto, avisos)`. Com R² abaixo de `r2_minimo` numa resposta
    usada, a otimização é recusada e o motivo vai nos avisos.
    """
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
        colunas = {n: pontos[:, j] for j, n in enumerate(nomes)}
        return {m.resposta: prever(por_nome[m.resposta], colunas) for m in metas}

    def custo(pontos: NDArray[np.float64]) -> NDArray[np.float64]:
        previstas = respostas(pontos)
        if direto:
            y = previstas[metas[0].resposta]
            return -y if metas[0].sentido == "maximizar" else y
        individuais = np.column_stack(
            [desejabilidade_vetor(previstas[m.resposta], m) for m in metas]
        )
        pesos = np.array([m.peso for m in metas])
        # Média geométrica ponderada; o piso evita log(0), e o veto (algum
        # d = 0 ⇒ D = 0) é aplicado à parte, como em desejabilidade_global.
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
    """Pontos de partida: malha regular até 4 fatores; amostra fixa acima disso."""
    if k <= 4:
        por_fator = {1: 201, 2: 41, 3: 21, 4: 11}[k]
        eixo = np.linspace(-limite, limite, por_fator)
        return np.array(np.meshgrid(*([eixo] * k), indexing="ij")).reshape(k, -1).T
    rng = np.random.default_rng(20261010)  # semente fixa: busca reprodutível
    return rng.uniform(-limite, limite, size=(4000, k))
