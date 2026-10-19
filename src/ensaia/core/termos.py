"""Quais termos entram no modelo: tipo, exclusões, confundimento e redução.

Spec §4 (opções avançadas) e §9 (regras gerais):

- **Tipo de modelo:** linear, com interações de 2ª ordem ou quadrático. Por
  padrão, quadrático quando todos os fatores têm 3 ou mais níveis (há como
  estimar curvatura) e com interações nos planejamentos de 2 níveis.
- **Graus de liberdade:** se o modelo pedido não deixa sobra para o resíduo, ele
  é rebaixado (quadrático → interações → linear), com aviso.
- **Confundimento:** numa fração 2^(k−p), interações aparecem confundidas entre
  si (a coluna de x1·x2 é igual à de x3·x4). Os termos redundantes saem do
  modelo com aviso, em vez de travar a análise com matriz singular.
- **Exclusão manual:** o usuário pode tirar termos para reproduzir o modelo de
  um artigo. Tirar o termo linear de um fator que segue numa interação ou num
  quadrático viola a hierarquia: avisa, não bloqueia (spec §9).
- **Redução backward:** "remover termos não significativos e reajustar", um de
  cada vez (o de maior p), respeitando a hierarquia.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
from numpy.typing import NDArray

from ensaia.core.blocos import Blocos, com_blocos, e_coluna_de_bloco
from ensaia.core.design import INTERCEPTO, Planejamento, interpretar_termo
from ensaia.core.model import RESIDUO, ajustar_ols, matriz_modelo, termos_redundantes
from ensaia.core.results import TipoModelo
from ensaia.core.table import Table

_REBAIXAR: dict[TipoModelo, TipoModelo | None] = {
    "quadratico": "interacoes",
    "interacoes": "linear",
    "linear": None,
}
NOME_MODELO: dict[TipoModelo, str] = {
    "linear": "linear",
    "interacoes": "com interações",
    "quadratico": "quadrático",
}


@dataclass(frozen=True)
class SelecaoTermos:
    """Os termos escolhidos, o tipo efetivo e o que foi preciso avisar."""

    termos: list[str]
    tipo_modelo: TipoModelo
    avisos: list[str] = field(default_factory=list)


def termos_do_tipo(
    niveis_por_fator: dict[str, int], tipo: TipoModelo
) -> list[str]:
    """Termos canônicos de um tipo de modelo, na ordem estável do núcleo.

    Quadráticos só para fatores com 3 ou mais níveis: com 2 níveis, x² é uma
    coluna de 1 (igual ao intercepto) e não há curvatura a estimar.
    """
    nomes = list(niveis_por_fator)
    termos = [INTERCEPTO, *nomes]
    if tipo == "quadratico":
        termos += [f"{n}^2" for n in nomes if niveis_por_fator[n] >= 3]
    if tipo in ("interacoes", "quadratico"):
        termos += [":".join(par) for par in combinations(nomes, 2)]
    return termos


def tipo_padrao(
    niveis_por_fator: dict[str, int], tipo_planejamento: str | None = None
) -> TipoModelo:
    """Quadrático se todos os fatores têm ≥ 3 níveis; senão, com interações.

    Fatorial de 2 níveis com pontos centrais é exceção: os fatores têm 3 níveis
    (−1, 0, +1), mas todas as colunas x² são iguais (1 nos vértices, 0 no
    centro), então não dá para estimar a curvatura de cada fator. O modelo
    certo ali é o com interações, e a curvatura é avaliada pelo teste próprio
    (spec §9, B5).
    """
    if tipo_planejamento in ("fatorial_completo", "fatorial_fracionado"):
        return "interacoes"
    if niveis_por_fator and all(n >= 3 for n in niveis_por_fator.values()):
        return "quadratico"
    return "interacoes"


def escolher_termos(
    tabela: Table,
    planejamento: Planejamento,
    *,
    tipo_modelo: TipoModelo | None = None,
    excluidos: Sequence[str] = (),
    blocos: Blocos | None = None,
) -> SelecaoTermos:
    """Termos do modelo para os dados, com rebaixamento e limpeza de confundidos.

    Com `blocos`, as colunas de bloco entram na conta: um termo que é
    combinação dos blocos (confundido com eles, como a interação tripla de um
    fatorial 2³ dividido em blocos de 4) sai do modelo com aviso, e os graus de
    liberdade gastos com os blocos contam na hora de ver se o modelo cabe.
    """
    n_colunas_bloco = blocos.n_blocos - 1 if blocos is not None else 0
    niveis = {
        f.nome: len(np.unique(np.round(tabela.coluna(f.nome), 9)))
        for f in planejamento.fatores
    }
    pedido = tipo_modelo or tipo_padrao(niveis, planejamento.tipo)
    avisos: list[str] = []
    if pedido == "quadratico" and not any(n >= 3 for n in niveis.values()):
        avisos.append(
            "Todos os fatores têm só 2 níveis: não há curvatura a estimar, então o "
            "modelo quadrático vira modelo com interações."
        )
        pedido = "interacoes"

    excluir = {t for t in excluidos if t != INTERCEPTO}
    tipo: TipoModelo | None = pedido
    while tipo is not None:
        candidatos = termos_do_tipo(niveis, tipo)
        desconhecidos = sorted(excluir - set(candidatos))
        termos = [t for t in candidatos if t not in excluir]
        confundidos = [
            t
            for t in termos_redundantes(
                com_blocos(
                    matriz_modelo(tabela, planejamento, termos, codificar=True),
                    blocos,
                )
            )
            if not e_coluna_de_bloco(t)
        ]
        if confundidos:
            termos = [t for t in termos if t not in confundidos]
        # Sobra ao menos 1 gl para o resíduo, contando as colunas de bloco.
        if len(termos) + n_colunas_bloco < len(tabela):
            if confundidos:
                com_o_que = (
                    "com outros termos ou com os blocos"
                    if blocos
                    else "com outros (combinação dos anteriores)"
                )
                avisos.append(
                    f"Termos confundidos {com_o_que} ficaram fora do modelo: "
                    f"{', '.join(confundidos)}."
                )
            if desconhecidos and tipo == pedido:
                avisos.append(
                    "Termos pedidos para exclusão que não existem neste modelo: "
                    f"{', '.join(desconhecidos)}."
                )
            avisos.extend(_avisos_hierarquia(termos))
            return SelecaoTermos(termos, tipo, avisos)
        menor = _REBAIXAR[tipo]
        if menor is not None:
            avisos.append(
                f"{len(tabela)} ensaios não bastam para o modelo "
                f"{NOME_MODELO[tipo]} ({len(termos)} termos); usando o modelo "
                f"{NOME_MODELO[menor]}."
            )
        tipo = menor

    raise ValueError(
        f"{len(tabela)} ensaios não bastam nem para o modelo linear com "
        f"{len(planejamento.fatores)} fatores: sobra nenhum grau de liberdade "
        "para o resíduo. Use menos fatores ou mais ensaios."
    )


def _avisos_hierarquia(termos: list[str]) -> list[str]:
    """Fatores usados em termos de ordem superior sem o próprio termo linear."""
    lineares = set(termos)
    orfaos = sorted(
        {
            nome
            for t in termos
            if t != INTERCEPTO and _ordem_superior(t)
            for nome, _ in interpretar_termo(t)
            if nome not in lineares
        }
    )
    if not orfaos:
        return []
    return [
        "Modelo não hierárquico: "
        f"{', '.join(orfaos)} aparece(m) em interação ou termo quadrático sem o "
        "termo linear. Os coeficientes passam a depender da codificação e a "
        "ANOVA Tipo II fica indisponível."
    ]


def _ordem_superior(termo: str) -> bool:
    partes = interpretar_termo(termo)
    return len(partes) > 1 or (len(partes) == 1 and partes[0][1] > 1)


def reduzir_backward(
    tabela: Table,
    planejamento: Planejamento,
    termos: list[str],
    y: NDArray[np.float64],
    *,
    alfa: float,
    qm_erro: float | None = None,
    gl_erro: int | None = None,
    blocos: Blocos | None = None,
) -> tuple[list[str], list[str]]:
    """Elimina, um a um, o termo não significativo de maior p, e reajusta.

    Respeita a hierarquia: o termo linear de um fator que ainda está numa
    interação ou num quadrático não sai. Os blocos, se houver, ficam sempre no
    modelo (nunca são candidatos a sair). O teste usa o mesmo termo de erro da
    análise (`qm_erro`/`gl_erro` do erro puro, se for o caso); o erro puro não
    muda entre os modelos, porque só depende das réplicas.

    Devolve (mantidos, descartados), na ordem original.
    """
    atuais = list(termos)
    descartados: list[str] = []
    while True:
        ajuste = ajustar_ols(
            com_blocos(matriz_modelo(tabela, planejamento, atuais), blocos),
            y,
            fixos=blocos.nomes_colunas if blocos is not None else (),
        )
        try:
            pvalores = {
                linha.fonte: linha.valor_p
                for linha in ajuste.tabela_tipo2(qm_erro, gl_erro)
                if linha.fonte != RESIDUO and linha.valor_p is not None
            }
        except ValueError:  # modelo não hierárquico: usa o p do coeficiente
            _, _, pvalores_coef = ajuste.estatisticas_t(qm_erro, gl_erro)
            pvalores = {
                t: p
                for t, p in pvalores_coef.items()
                if t != INTERCEPTO and not e_coluna_de_bloco(t)
            }

        protegidos = {
            nome
            for t in atuais
            if t != INTERCEPTO and _ordem_superior(t)
            for nome, _ in interpretar_termo(t)
        }
        removiveis = {
            t: p for t, p in pvalores.items() if t not in protegidos and p >= alfa
        }
        if not removiveis:
            break
        pior = max(removiveis, key=lambda t: removiveis[t])
        atuais.remove(pior)
        descartados.append(pior)

    ordem = {t: i for i, t in enumerate(termos)}
    return atuais, sorted(descartados, key=lambda t: ordem[t])
