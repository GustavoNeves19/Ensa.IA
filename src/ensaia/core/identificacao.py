"""Codificação dos fatores e identificação do planejamento a partir dos dados.

Spec §8.4 (codificação) e RF-05/RF-06 (identificação). É o que a interface usa
quando o usuário só entrega a planilha: ninguém precisa dizer onde fica o −1, o
+1 ou que tipo de planejamento foi feito.

**Por que isto importa para a validação.** Num composto central (DCC/DCCR) os
níveis ±1 são os do fatorial — o 2º e o 4º níveis em ordem —, e os extremos são
os pontos axiais em ±α. Tomar o mínimo e o máximo dos dados como ±1 encolhe a
escala por um fator α: a ANOVA e as previsões não mudam, mas todos os
coeficientes ficam numa escala diferente da publicada, e a comparação com o
artigo (métrica (a)) deixa de fazer sentido.

**Como o planejamento é reconhecido.** Pela geometria dos pontos na escala
codificada, não pela contagem de níveis (Box-Behnken e um fatorial 3^k, por
exemplo, têm os mesmos 3 níveis):

    vértice  todas as coordenadas em ±1            (fatoriais, parte fatorial do DCC)
    axial    uma coordenada em ±α (α ≥ 1), o resto 0 (estrela do DCC)
    aresta   exatamente duas coordenadas em ±1, o resto 0 (Box-Behnken)
    centro   todas as coordenadas em 0
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from ensaia.core.design import Fator, Planejamento
from ensaia.core.results import TipoPlanejamento

# Tolerância, na escala codificada, para dizer que um valor "é" 0 ou ±1. Os
# níveis ±1 e o centro saem exatos dos próprios dados; a folga cobre só o
# arredondamento com que planilhas reais costumam trazer os níveis.
_TOL = 0.02
# Casas usadas para considerar dois níveis reais iguais (evita que 37.5 e
# 37.500000001 virem níveis distintos por erro de ponto flutuante).
_CASAS_NIVEL = 9


@dataclass(frozen=True)
class FatorInferido:
    """Um fator com a codificação deduzida dos próprios valores.

    `fator.minimo`/`fator.maximo` são os níveis reais que viram −1 e +1.
    `alfa_axial` é a distância codificada dos níveis extremos quando o fator
    tem 5 níveis (composto central); `ja_codificado` indica que a planilha já
    trazia os valores em −1/0/+1 (±α).
    """

    fator: Fator
    niveis: tuple[float, ...]
    alfa_axial: float | None = None
    ja_codificado: bool = False
    aviso: str | None = None


def inferir_fator(
    nome: str, valores: Sequence[float], *, unidade: str = ""
) -> FatorInferido:
    """Deduz os níveis reais que correspondem a −1 e +1 (spec §8.4).

    - 2 ou 3 níveis: ±1 são o mínimo e o máximo.
    - 5 níveis (DCC/DCCR): ±1 são o 2º e o 4º níveis em ordem; os extremos são
      ±α, e α é medido (deve dar ~1,414 para k = 2, 1,682 para k = 3...).
    - Valores já em {−1, 0, +1} (ou com ±α simétrico): a planilha já está
      codificada e a escala fica como está.
    - Outra quantidade de níveis: usa mínimo e máximo e avisa.
    """
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
    """True se os níveis já são −1, 0, +1 (e, com 5 níveis, ±α simétrico)."""
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
    """O planejamento reconhecido, pronto para a análise."""

    planejamento: Planejamento
    fatores: list[FatorInferido]
    n_ensaios: int
    n_pontos_centrais: int
    avisos: list[str] = field(default_factory=list)

    @property
    def tipo(self) -> TipoPlanejamento:
        return self.planejamento.tipo


def identificar_planejamento(
    colunas: Mapping[str, Sequence[float]],
    *,
    unidades: Mapping[str, str] | None = None,
) -> Identificacao:
    """Codifica cada fator e reconhece o tipo de planejamento pela geometria.

    `colunas` mapeia cada fator para seus valores na ordem dos ensaios (as
    colunas da planilha). Devolve o `Planejamento` (com os ±1 certos), o número
    de pontos centrais, o α axial e avisos em português para a interface.
    """
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
    """Ensaios com todas as coordenadas no centro (0) da escala codificada."""
    return int(np.sum(np.all(np.abs(matriz_codificada) < _TOL, axis=1)))


def _classificar(
    matriz: NDArray[np.float64],
) -> tuple[TipoPlanejamento, float | None, int, list[str]]:
    """Tipo, α axial, nº de pontos centrais e avisos a partir da matriz codificada."""
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
    avisos: list[str] = []

    if k == 1:
        unico: TipoPlanejamento = (
            "desconhecido" if outro.any() else "fatorial_completo"
        )
        return unico, None, n_centro, avisos

    if outro.any() or (aresta.any() and vertice.any()):
        if _e_fatorial_3k(matriz, k):
            return "fatorial_3k", None, n_centro, avisos
        avisos.append(
            "A disposição dos ensaios não corresponde a fatorial, composto "
            "central ou Box-Behnken: a análise segue como planejamento genérico."
        )
        return "desconhecido", None, n_centro, avisos

    if vertice.any() and not axial.any() and not aresta.any():
        if len(vertices) == 2**k:
            return "fatorial_completo", None, n_centro, avisos
        if _e_fracionado(vertices, k):
            return "fatorial_fracionado", None, n_centro, avisos
        avisos.append(
            f"Só {len(vertices)} dos {2**k} vértices do fatorial foram ensaiados "
            "e eles não formam uma fração regular: análise como genérico."
        )
        return "desconhecido", None, n_centro, avisos

    if vertice.any() and axial.any() and not aresta.any():
        alfa = float(np.mean(absoluto[axial].max(axis=1)))
        estrelas = {tuple(np.round(linha, 6)) for linha in matriz[axial]}
        if len(estrelas) != 2 * k:
            avisos.append(
                f"O composto central deveria ter {2 * k} pontos axiais distintos; "
                f"foram encontrados {len(estrelas)}."
            )
        rotacional = len(vertices) ** 0.25
        if abs(alfa - 1.0) > _TOL and abs(alfa - rotacional) > 0.02 * rotacional:
            avisos.append(
                f"α axial = {alfa:.3f}: não é o rotacional ({rotacional:.3f}) "
                "nem o de face centrada (1)."
            )
        if len(vertices) < 2**k and not _e_fracionado(vertices, k):
            avisos.append("A parte fatorial do composto central está incompleta.")
        return "composto_central", alfa, n_centro, avisos

    if aresta.any() and not vertice.any() and not axial.any():
        return "box_behnken", None, n_centro, avisos

    if _e_fatorial_3k(matriz, k):
        return "fatorial_3k", None, n_centro, avisos
    avisos.append(
        "Não foi possível reconhecer o tipo de planejamento: a análise segue "
        "como planejamento genérico."
    )
    return "desconhecido", None, n_centro, avisos


def _e_fracionado(vertices: set[tuple[int, ...]], k: int) -> bool:
    """Fração regular 2^(k−p): potência de 2 e colunas balanceadas (soma zero)."""
    m = len(vertices)
    if m < 4 or m >= 2**k or m & (m - 1):
        return False
    pontos = np.array(sorted(vertices))
    return bool(np.all(pontos.sum(axis=0) == 0))


def _e_fatorial_3k(matriz: NDArray[np.float64], k: int) -> bool:
    """Todas as 3^k combinações de {−1, 0, +1} presentes (réplicas permitidas)."""
    arredondada = np.round(matriz).astype(int)
    if not np.allclose(matriz, arredondada, atol=_TOL):
        return False
    if np.abs(arredondada).max() > 1:
        return False
    return bool(len({tuple(linha) for linha in arredondada}) == 3**k)
