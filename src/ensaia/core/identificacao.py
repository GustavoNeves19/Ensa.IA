"""Codificação dos fatores e reconhecimento do DCCR a partir dos dados.
Acha os níveis −α, −1, 0, +1, +α e confere a geometria e o α rotacional.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from ensaia.core.design import Fator, Planejamento
from ensaia.core.results import TipoPlanejamento

# Tolerância codificada para dizer que um valor é 0 ou ±1.
_TOL = 0.02
# Tolerância para aceitar o α medido como rotacional (5%).
_TOL_ALFA_ROTACIONAL = 0.05
# Casas para considerar dois níveis reais iguais.
_CASAS_NIVEL = 9


@dataclass(frozen=True)
class FatorInferido:
    """Fator com a codificação deduzida dos próprios valores."""

    fator: Fator
    niveis: tuple[float, ...]
    alfa_axial: float | None = None
    ja_codificado: bool = False
    aviso: str | None = None


def inferir_fator(
    nome: str, valores: Sequence[float], *, unidade: str = ""
) -> FatorInferido:
    """Deduz os níveis reais que viram −1 e +1 e o α axial do fator."""
    niveis = tuple(sorted({round(float(v), _CASAS_NIVEL) for v in valores}))
    if len(niveis) < 2:
        raise ValueError(
            f"O fator {nome!r} não varia (um único nível): não dá para estimar "
            "o efeito dele. Marque a coluna como 'Ignorar'."
        )

    if _parece_codificado(niveis):
        alfa = max(abs(niveis[0]), abs(niveis[-1]))
        return FatorInferido(
            Fator(nome, -1.0, 1.0, unidade),
            niveis,
            alfa_axial=alfa if len(niveis) == 5 else None,
            ja_codificado=True,
        )

    if len(niveis) in (2, 3):
        return FatorInferido(Fator(nome, niveis[0], niveis[-1], unidade), niveis)

    if len(niveis) == 5:
        baixo, alto = niveis[1], niveis[3]
        centro, passo = (baixo + alto) / 2.0, (alto - baixo) / 2.0
        alfa_baixo = (centro - niveis[0]) / passo
        alfa_alto = (niveis[4] - centro) / passo
        aviso = None
        if abs(alfa_baixo - alfa_alto) > _TOL * max(alfa_baixo, alfa_alto):
            aviso = (
                f"{nome}: os níveis axiais não são simétricos em torno do centro "
                f"(α inferior {alfa_baixo:.3f}, α superior {alfa_alto:.3f})."
            )
        elif abs(niveis[2] - centro) > _TOL * passo:
            aviso = (
                f"{nome}: o nível central ({niveis[2]:g}) não fica no meio dos "
                f"níveis ±1 ({baixo:g} e {alto:g})."
            )
        return FatorInferido(
            Fator(nome, baixo, alto, unidade),
            niveis,
            alfa_axial=(alfa_baixo + alfa_alto) / 2.0,
            aviso=aviso,
        )

    return FatorInferido(
        Fator(nome, niveis[0], niveis[-1], unidade),
        niveis,
        aviso=(
            f"{nome}: {len(niveis)} níveis distintos; ±1 foram tomados como o "
            "mínimo e o máximo observados."
        ),
    )


def _parece_codificado(niveis: tuple[float, ...]) -> bool:
    """Diz se os níveis já estão na escala codificada."""
    tem = {round(v, 6) for v in niveis}
    if len(niveis) in (2, 3):
        return {-1.0, 1.0} <= tem and tem <= {-1.0, 0.0, 1.0}
    if len(niveis) == 5:
        return (
            {-1.0, 0.0, 1.0} <= tem
            and abs(niveis[0] + niveis[-1]) < 1e-6
            and niveis[-1] > 1.0
        )
    return False


@dataclass(frozen=True)
class Identificacao:
    """Planejamento reconhecido, pontos centrais e avisos."""

    planejamento: Planejamento
    fatores: list[FatorInferido]
    n_ensaios: int
    n_pontos_centrais: int
    avisos: list[str] = field(default_factory=list)

    @property
    def tipo(self) -> TipoPlanejamento:
        """Tipo do planejamento reconhecido."""
        return self.planejamento.tipo


def identificar_planejamento(
    colunas: Mapping[str, Sequence[float]],
    *,
    unidades: Mapping[str, str] | None = None,
) -> Identificacao:
    """Codifica os fatores e reconhece o tipo de planejamento."""
    if not colunas:
        raise ValueError("Escolha ao menos um fator.")
    unidades = unidades or {}
    inferidos = [
        inferir_fator(nome, valores, unidade=unidades.get(nome, ""))
        for nome, valores in colunas.items()
    ]
    tamanhos = {len(v) for v in colunas.values()}
    if len(tamanhos) != 1:
        raise ValueError("Os fatores têm números diferentes de ensaios.")
    n = tamanhos.pop()

    matriz = np.column_stack(
        [
            [f.fator.codificar(float(v)) for v in colunas[f.fator.nome]]
            for f in inferidos
        ]
    )
    tipo, alfa, n_centro, avisos_geometria = _classificar(matriz)
    alfas_fator = [f.alfa_axial for f in inferidos if f.alfa_axial is not None]
    if alfa is None and alfas_fator:
        alfa = float(np.mean(alfas_fator))

    avisos = [f.aviso for f in inferidos if f.aviso] + avisos_geometria
    planejamento = Planejamento(
        tipo=tipo,
        fatores=[f.fator for f in inferidos],
        n_pontos_centrais=n_centro,
        alfa_axial=alfa,
    )
    return Identificacao(
        planejamento=planejamento,
        fatores=inferidos,
        n_ensaios=n,
        n_pontos_centrais=n_centro,
        avisos=avisos,
    )


def contar_pontos_centrais(matriz_codificada: NDArray[np.float64]) -> int:
    """Conta os ensaios com todos os fatores no centro."""
    return int(np.sum(np.all(np.abs(matriz_codificada) < _TOL, axis=1)))


_FORA_DO_ESCOPO = (
    "Este sistema reconhece apenas o delineamento composto central rotacional "
    "(DCCR)."
)


def _classificar(
    matriz: NDArray[np.float64],
) -> tuple[TipoPlanejamento, float | None, int, list[str]]:
    """Classifica a geometria: DCCR ou desconhecido, com o α e avisos."""
    _, k = matriz.shape
    absoluto = np.abs(matriz)
    zero = absoluto < _TOL
    um = np.abs(absoluto - 1.0) < _TOL
    n_nulos = zero.sum(axis=1)

    centro = np.all(zero, axis=1)
    vertice = np.all(um, axis=1)
    axial = (n_nulos == k - 1) & (absoluto.max(axis=1) >= 1.0 - _TOL) & ~centro
    aresta = (n_nulos == k - 2) & np.all(zero | um, axis=1) & (k >= 3)
    outro = ~(centro | vertice | axial | aresta)

    n_centro = int(centro.sum())
    vertices = {tuple(np.sign(linha).astype(int)) for linha in matriz[vertice]}

    if k < 2:
        return (
            "desconhecido",
            None,
            n_centro,
            [f"{_FORA_DO_ESCOPO} Ele exige ao menos 2 fatores."],
        )

    if outro.any() or (aresta.any() and vertice.any()):
        if _e_fatorial_3k(matriz, k):
            return (
                "desconhecido",
                None,
                n_centro,
                [f"{_FORA_DO_ESCOPO} A disposição corresponde a um fatorial "
                 "completo de 3 níveis (3^k)."],
            )
        return (
            "desconhecido",
            None,
            n_centro,
            [f"{_FORA_DO_ESCOPO} A disposição dos ensaios não corresponde a "
             "nenhum padrão reconhecido."],
        )

    if vertice.any() and not axial.any() and not aresta.any():
        if len(vertices) == 2**k:
            return (
                "desconhecido",
                None,
                n_centro,
                [f"{_FORA_DO_ESCOPO} A disposição corresponde a um fatorial "
                 f"completo 2^{k}, sem os pontos axiais do DCCR."],
            )
        if _e_fracionado(vertices, k):
            return (
                "desconhecido",
                None,
                n_centro,
                [f"{_FORA_DO_ESCOPO} A disposição corresponde a um fatorial "
                 "fracionado, sem os pontos axiais do DCCR."],
            )
        return (
            "desconhecido",
            None,
            n_centro,
            [f"{_FORA_DO_ESCOPO} Só {len(vertices)} dos {2**k} vértices do "
             "fatorial foram ensaiados e eles não formam uma fração regular."],
        )

    if vertice.any() and axial.any() and not aresta.any():
        avisos: list[str] = []
        alfa = float(np.mean(absoluto[axial].max(axis=1)))
        estrelas = {tuple(np.round(linha, 6)) for linha in matriz[axial]}
        if len(estrelas) != 2 * k:
            avisos.append(
                f"O composto central deveria ter {2 * k} pontos axiais distintos; "
                f"foram encontrados {len(estrelas)}."
            )
        if len(vertices) < 2**k and not _e_fracionado(vertices, k):
            avisos.append("A parte fatorial do composto central está incompleta.")

        rotacional = len(vertices) ** 0.25
        if abs(alfa - rotacional) > _TOL_ALFA_ROTACIONAL * rotacional:
            motivo = (
                "de face centrada (α=1)"
                if abs(alfa - 1.0) < _TOL
                else f"α={alfa:.3f}"
            )
            return (
                "desconhecido",
                alfa,
                n_centro,
                [
                    f"{_FORA_DO_ESCOPO} Este composto central é {motivo}, não "
                    f"rotacional (α esperado: {rotacional:.3f} para "
                    f"{len(vertices)} pontos fatoriais).",
                    *avisos,
                ],
            )
        return "composto_central", alfa, n_centro, avisos

    if aresta.any() and not vertice.any() and not axial.any():
        return (
            "desconhecido",
            None,
            n_centro,
            [f"{_FORA_DO_ESCOPO} A disposição corresponde a um delineamento "
             "Box-Behnken."],
        )

    if _e_fatorial_3k(matriz, k):
        return (
            "desconhecido",
            None,
            n_centro,
            [f"{_FORA_DO_ESCOPO} A disposição corresponde a um fatorial "
             "completo de 3 níveis (3^k)."],
        )
    return (
        "desconhecido",
        None,
        n_centro,
        [f"{_FORA_DO_ESCOPO} Não foi possível reconhecer a disposição dos "
         "ensaios."],
    )


def _e_fracionado(vertices: set[tuple[int, ...]], k: int) -> bool:
    """Diz se os vértices formam uma fração regular 2^(k−p)."""
    m = len(vertices)
    if m < 4 or m >= 2**k or m & (m - 1):
        return False
    pontos = np.array(sorted(vertices))
    return bool(np.all(pontos.sum(axis=0) == 0))


def _e_fatorial_3k(matriz: NDArray[np.float64], k: int) -> bool:
    """Diz se todas as combinações de −1, 0, +1 estão presentes."""
    arredondada = np.round(matriz).astype(int)
    if not np.allclose(matriz, arredondada, atol=_TOL):
        return False
    if np.abs(arredondada).max() > 1:
        return False
    return bool(len({tuple(linha) for linha in arredondada}) == 3**k)
