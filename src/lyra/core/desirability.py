"""Otimização multirresposta pela função de desejabilidade de Derringer-Suich.

Quarto item do pipeline prometido no pré-projeto. Diferente do protótipo
inicial, que só maximizava, esta implementação precisa cobrir os três sentidos
(maximizar, minimizar, alvo) — casos de estudo reais de química quase sempre
têm ao menos uma resposta a minimizar, como teor de impureza ou tempo de
processo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from lyra.core.design import Planejamento
from lyra.core.model import AjusteOLS
from lyra.core.results import PontoOtimo, Sentido

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


def otimizar(
    ajustes: dict[str, AjusteOLS],
    planejamento: Planejamento,
    alvos: list[AlvoResposta],
    *,
    pontos_por_fator: int = 15,
    r2_minimo: float = R2_MINIMO_PARA_OTIMIZAR,
) -> tuple[PontoOtimo | None, list[str]]:
    """Busca a condição que maximiza a desejabilidade global.

    Devolve `(ponto_otimo, avisos)`. `ponto_otimo` vem None quando a
    otimização foi bloqueada — R² insuficiente, por exemplo — e o motivo vai
    nos avisos, que sobem para o `AnalysisResult` e de lá para o relatório.

    Busca em malha (`pontos_por_fator` por dimensão) seguida de refinamento
    local. A malha sozinha não basta: com 15 pontos por fator e 3 fatores são
    3.375 avaliações e o ótimo cai na resolução da grade. Mas malha pura é
    determinística e serve de ponto de partida reprodutível para o refinamento
    — e reprodutibilidade aqui vale mais que o último decimal, porque o §4.3(d)
    compara essa coordenada com a publicada.

    Atenção à explosão combinatória: 15^k avaliações cresce rápido. Para k > 4,
    trocar a malha por amostragem por hipercubo latino + refinamento.

    TODO(#6): implementar. Depende de duas decisões ainda em aberto, por tocarem
    o contrato congelado e uma regra de negócio: (1) como registrar método, nº de
    pontos e semente no `AnalysisResult` (reprodutibilidade do §4.3(d)); e (2) o
    critério de custo que separa os cenários econômico/intermediário/alta
    performance, que a issue #6 define como "definido pelo usuário". As funções
    puras `desejabilidade_individual`/`desejabilidade_global` acima já estão
    prontas e são a base desta busca.
    """
    raise NotImplementedError("Ver issue #6 — busca do ótimo (design em aberto).")
