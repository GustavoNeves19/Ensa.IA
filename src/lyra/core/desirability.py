"""Otimização multirresposta pela função de desejabilidade de Derringer-Suich.

Quarto item do pipeline prometido no pré-projeto. Diferente do protótipo
inicial, que só maximizava, esta implementação precisa cobrir os três sentidos
(maximizar, minimizar, alvo) — casos de estudo reais de química quase sempre
têm ao menos uma resposta a minimizar, como teor de impureza ou tempo de
processo.
"""

from __future__ import annotations

from dataclasses import dataclass

from lyra.core.design import Planejamento
from lyra.core.results import PontoOtimo, Sentido

# Abaixo deste R², o modelo não descreve os dados bem o bastante para que
# otimizar sobre ele signifique alguma coisa. O protótipo usava 0,50; o valor
# fica configurável e o bloqueio é reportado como aviso no AnalysisResult,
# nunca silenciosamente.
R2_MINIMO_PARA_OTIMIZAR = 0.50


@dataclass(frozen=True)
class AlvoResposta:
    """O que se quer de cada resposta na otimização."""

    resposta: str
    sentido: Sentido
    limite_inferior: float
    limite_superior: float
    alvo: float | None = None
    peso: float = 1.0

    def __post_init__(self) -> None:
        if self.sentido == "alvo" and self.alvo is None:
            raise ValueError(
                f"Resposta {self.resposta!r} tem sentido 'alvo' mas nenhum "
                f"valor-alvo foi informado."
            )
        if self.limite_superior <= self.limite_inferior:
            raise ValueError(
                f"Resposta {self.resposta!r}: limite_superior deve ser maior "
                f"que limite_inferior."
            )


def desejabilidade_individual(valor: float, alvo: AlvoResposta) -> float:
    """d_i em [0, 1] para uma resposta.

    TODO(#6): implementar as três formas de Derringer-Suich:
        maximizar  0 abaixo do inferior, sobe até 1 no superior
        minimizar  1 abaixo do inferior, cai até 0 no superior
        alvo       sobe até 1 no alvo e desce depois
    """
    raise NotImplementedError("Ver issue #6 — desejabilidade.")


def desejabilidade_global(individuais: list[float], pesos: list[float]) -> float:
    """D = média geométrica ponderada das desejabilidades individuais.

    Média geométrica, não aritmética: se qualquer resposta for inaceitável
    (d_i = 0), D tem que zerar. Com média aritmética, uma resposta péssima
    seria compensada por outras boas, e o otimizador recomendaria uma condição
    que viola um requisito — exatamente o tipo de erro que um usuário sem
    formação em estatística não teria como perceber no relatório.

    TODO(#6): implementar.
    """
    raise NotImplementedError("Ver issue #6 — desejabilidade.")


def otimizar(
    ajustes,
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

    TODO(#6): implementar.
    """
    raise NotImplementedError("Ver issue #6 — desejabilidade.")
