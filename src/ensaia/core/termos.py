"""Escolha dos termos do modelo: tipo, exclusões, confundimento e redução.
Rebaixa o modelo sem g.l., tira termos confundidos e faz a redução backward.
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
    """Termos escolhidos, tipo efetivo e avisos."""

    termos: list[str]
    tipo_modelo: TipoModelo
    avisos: list[str] = field(default_factory=list)


def termos_do_tipo(
    niveis_por_fator: dict[str, int], tipo: TipoModelo
) -> list[str]:
    """Termos de um tipo de modelo (linear, interações, quadrático)."""
    nomes = list(niveis_por_fator)
    termos = [INTERCEPTO, *nomes]
    if tipo == "quadratico":
        termos += [f"{n}^2" for n in nomes if niveis_por_fator[n] >= 3]
    if tipo in ("interacoes", "quadratico"):
        termos += [":".join(par) for par in combinations(nomes, 2)]
    return termos


def tipo_padrao(tipo_planejamento: str | None = None) -> TipoModelo:
    """Tipo de modelo padrão: quadrático no DCCR, senão com interações."""
    if tipo_planejamento == "composto_central":
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
    """Termos do modelo, com rebaixamento e limpeza de confundidos."""
    n_colunas_bloco = blocos.n_blocos - 1 if blocos is not None else 0
    niveis = {
        f.nome: len(np.unique(np.round(tabela.coluna(f.nome), 9)))
        for f in planejamento.fatores
    }
    pedido = tipo_modelo or tipo_padrao(planejamento.tipo)
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
    """Avisa fatores usados em termos superiores sem o termo linear."""
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
    """Diz se o termo é quadrático ou interação."""
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
    """Remove o termo não significativo de maior p e reajusta, em ciclo."""
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
