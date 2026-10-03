"""Representação e detecção de planejamentos experimentais.

O pré-projeto assinado compromete o LYRA com três famílias de planejamento
(§4.2, critério 2): fatorial completo 2^k, delineamento composto central e
Box-Behnken. O protótipo atual trabalha com exatamente 3 fatores fixos —
generalizar para k fatores é a refatoração central da fase de implementação.
Ver docs/decisoes/0002-generalizacao-para-k-fatores.md.

Nada aqui depende de qual biblioteca faz a regressão: este módulo só descreve
a geometria do experimento e monta a matriz de termos do modelo.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from lyra.core.results import TipoPlanejamento

INTERCEPTO = "Intercepto"


@dataclass(frozen=True)
class Fator:
    """Um fator independente e sua faixa experimental.

    `minimo`/`maximo` são os níveis reais (unidades do experimento) que
    correspondem a -1 e +1 na escala codificada. Em composto central, são os
    níveis do fatorial, NÃO os pontos axiais: os axiais caem em ±α (ex.: ±1,68)
    e é nessa escala que os artigos publicam os coeficientes. Passar os níveis
    axiais aqui encolhe a escala e distorce todos os coeficientes por um fator
    α, sem nenhum erro aparente.

    A codificação para [-1, +1] é derivada, nunca informada pelo usuário: pedir
    ao usuário que codifique à mão é uma das barreiras que o TCC se propõe a
    remover.
    """

    nome: str
    minimo: float
    maximo: float
    unidade: str = ""

    @property
    def centro(self) -> float:
        return (self.minimo + self.maximo) / 2.0

    @property
    def amplitude(self) -> float:
        return self.maximo - self.minimo

    def codificar(self, valor: float) -> float:
        """Converte nível real para a escala codificada [-1, +1]."""
        if self.amplitude == 0:
            raise ValueError(
                f"Fator {self.nome!r} tem amplitude zero "
                f"(mínimo == máximo == {self.minimo}); não é um fator."
            )
        return (valor - self.centro) / (self.amplitude / 2.0)

    def decodificar(self, codificado: float) -> float:
        """Converte da escala codificada de volta para o nível real."""
        return codificado * (self.amplitude / 2.0) + self.centro


@dataclass(frozen=True)
class Planejamento:
    """Descrição completa do delineamento de um caso de estudo."""

    tipo: TipoPlanejamento
    fatores: list[Fator]
    n_pontos_centrais: int = 0
    alfa_axial: float | None = None  # só para composto central

    @property
    def k(self) -> int:
        return len(self.fatores)

    @property
    def nomes_fatores(self) -> list[str]:
        return [f.nome for f in self.fatores]

    def fator(self, nome: str) -> Fator:
        for f in self.fatores:
            if f.nome == nome:
                return f
        raise KeyError(f"Fator {nome!r} não existe. Disponíveis: {self.nomes_fatores}")


def termos_do_modelo(
    nomes_fatores: list[str],
    *,
    incluir_quadraticos: bool = True,
    grau_interacao: int = 2,
) -> list[str]:
    """Gera os termos do modelo polinomial em notação canônica.

    Para ["temp", "ph"] com quadráticos e interação de 2ª ordem devolve:
        ["Intercepto", "temp", "ph", "temp^2", "ph^2", "temp:ph"]

    A ordem é estável e a notação é a mesma usada em `Coeficiente.termo`, para
    que a comparação com os valores de referência dos casos de estudo seja
    feita por chave e não por posição — comparar por posição é como bugs de
    validação silenciosos nascem.

    `incluir_quadraticos=False` é o caso do fatorial 2^k puro, que não tem
    graus de liberdade para estimar curvatura: sem pontos além dos vértices,
    um termo quadrático é inestimável, e pedi-lo produz matriz singular.
    """
    if grau_interacao < 1:
        raise ValueError("grau_interacao deve ser >= 1")

    termos = [INTERCEPTO]
    termos += list(nomes_fatores)

    if incluir_quadraticos:
        termos += [f"{nome}^2" for nome in nomes_fatores]

    for ordem in range(2, grau_interacao + 1):
        for combo in combinations(nomes_fatores, ordem):
            termos.append(":".join(combo))

    return termos


def interpretar_termo(termo: str) -> list[tuple[str, int]]:
    """Decompõe um termo canônico em pares (fator, potência).

        "Intercepto" -> []
        "x1"         -> [("x1", 1)]
        "x1^2"       -> [("x1", 2)]
        "x1:x2"      -> [("x1", 1), ("x2", 1)]

    É o inverso de `termos_do_modelo`: a notação é definida nos dois lugares
    e só aqui é lida, para que a regra de "quem contém quem" (hierarquia do
    modelo) não dependa de cada módulo reinterpretar a string do seu jeito.
    """
    if termo == INTERCEPTO:
        return []

    partes: list[tuple[str, int]] = []
    for pedaco in termo.split(":"):
        nome, separador, potencia = pedaco.rpartition("^")
        if not separador:
            if not pedaco:
                raise ValueError(f"Termo {termo!r} tem um fator vazio.")
            partes.append((pedaco, 1))
            continue
        if not nome or not potencia.isdigit() or int(potencia) < 2:
            raise ValueError(
                f"Termo {termo!r}: a potência de {pedaco!r} deve ser um inteiro "
                f">= 2 (ex.: 'x1^2')."
            )
        partes.append((nome, int(potencia)))
    return partes


def detectar_tipo(
    niveis_por_fator: dict[str, list[float]],
    n_ensaios: int,
) -> TipoPlanejamento:
    """Infere o tipo de planejamento a partir dos níveis observados.

    Heurística deliberadamente conservadora — devolve "desconhecido" em vez de
    chutar. Um palpite errado aqui escolhe o modelo errado lá na frente e o
    erro só aparece como um R² estranho, difícil de rastrear.

    Regra atual (a refinar quando os casos de estudo reais estiverem
    catalogados — ver docs/decisoes/0002):

        2 níveis por fator                     → fatorial completo (2^k)
        3 níveis por fator                     → Box-Behnken
        5 níveis, simétricos em torno do centro → composto central
        qualquer outra combinação              → desconhecido

    TODO(#2): validar contra os 3-5 casos de estudo selecionados e substituir
    a heurística por verificação da matriz de delineamento, que é o critério
    correto (Box-Behnken e composto central podem coincidir em nº de níveis).
    """
    if not niveis_por_fator:
        return "desconhecido"

    contagens = {len(set(niveis)) for niveis in niveis_por_fator.values()}
    if len(contagens) != 1:
        return "desconhecido"

    n_niveis = contagens.pop()
    if n_niveis == 2:
        return "fatorial_completo"
    if n_niveis == 3:
        return "box_behnken"
    if n_niveis == 5:
        return "composto_central"
    return "desconhecido"
