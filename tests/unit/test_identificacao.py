"""Testes da codificação de fatores e da identificação do planejamento."""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from ensaia.core.identificacao import identificar_planejamento, inferir_fator
from ensaia.io.readers import ler_dados

CASOS = Path(__file__).resolve().parents[2] / "casos_de_estudo"


def _colunas(pontos: list[tuple[float, ...]], nomes: str = "abcdefg") -> dict:
    k = len(pontos[0])
    return {nomes[j]: [p[j] for p in pontos] for j in range(k)}


def _fatorial(k: int) -> list[tuple[float, ...]]:
    return [tuple(float(v) for v in p) for p in itertools.product([-1, 1], repeat=k)]


def _dcc(k: int, alfa: float, centrais: int) -> list[tuple[float, ...]]:
    estrela = []
    for j in range(k):
        for s in (-alfa, alfa):
            p = [0.0] * k
            p[j] = s
            estrela.append(tuple(p))
    return _fatorial(k) + estrela + [tuple([0.0] * k)] * centrais


# --- codificação de um fator ---------------------------------------------------


def test_dois_niveis_viram_menos_um_e_mais_um() -> None:
    f = inferir_fator("temp", [40, 60, 40, 60])
    assert (f.fator.minimo, f.fator.maximo) == (40, 60)
    assert f.fator.codificar(50) == pytest.approx(0.0)


def test_dccr_usa_o_segundo_e_o_quarto_niveis_como_mais_menos_um() -> None:
    # DCCR k=3: centro 50, passo 10, α = 1,682 → axiais 33,18 e 66,82.
    valores = [40, 60, 40, 60, 40, 60, 40, 60, 33.18, 66.82, 50, 50, 50, 50, 50, 50, 50]
    f = inferir_fator("temp", valores)
    assert (f.fator.minimo, f.fator.maximo) == (40, 60)
    assert f.alfa_axial == pytest.approx(1.682, abs=1e-3)
    assert f.aviso is None
    # Os axiais caem em ±α, não em ±1 (o erro clássico de tomar mín/máx).
    assert f.fator.codificar(66.82) == pytest.approx(1.682, abs=1e-3)


def test_axiais_assimetricos_geram_aviso() -> None:
    f = inferir_fator("t", [30, 40, 50, 60, 75])
    assert f.aviso is not None and "simétricos" in f.aviso


def test_planilha_ja_codificada_fica_como_esta() -> None:
    f = inferir_fator("x1", [-1, 1, -1, 1, 0, 0])
    assert f.ja_codificado
    assert (f.fator.minimo, f.fator.maximo) == (-1, 1)
    f5 = inferir_fator("x1", [-1, 1, -1.414, 1.414, 0])
    assert f5.ja_codificado and f5.alfa_axial == pytest.approx(1.414)


def test_fator_constante_e_recusado() -> None:
    with pytest.raises(ValueError, match="não varia"):
        inferir_fator("x", [5, 5, 5])


# --- identificação do planejamento --------------------------------------------


def test_fatorial_completo_com_pontos_centrais() -> None:
    pontos = _fatorial(3) + [(0.0, 0.0, 0.0)] * 3
    ident = identificar_planejamento(_colunas(pontos))
    assert ident.tipo == "fatorial_completo"
    assert ident.n_pontos_centrais == 3
    assert ident.planejamento.alfa_axial is None


def test_fatorial_fracionado_meia_fracao() -> None:
    # 2^(4-1) com gerador D = ABC.
    pontos = [(a, b, c, a * b * c) for a, b, c in _fatorial(3)]
    ident = identificar_planejamento(_colunas(pontos))
    assert ident.tipo == "fatorial_fracionado"


@pytest.mark.parametrize(("k", "alfa"), [(2, 1.414), (3, 1.682)])
def test_composto_central_rotacional(k: int, alfa: float) -> None:
    ident = identificar_planejamento(_colunas(_dcc(k, alfa, centrais=5)))
    assert ident.tipo == "composto_central"
    assert ident.planejamento.alfa_axial == pytest.approx(alfa, abs=1e-3)
    assert ident.n_pontos_centrais == 5
    assert not ident.avisos


def test_composto_central_de_face_centrada() -> None:
    ident = identificar_planejamento(_colunas(_dcc(3, 1.0, centrais=3)))
    assert ident.tipo == "composto_central"
    assert ident.planejamento.alfa_axial == pytest.approx(1.0)


def test_dcc_em_unidades_reais_recupera_alfa_e_niveis() -> None:
    reais = [
        (50 + 10 * a, 6 + 1.5 * b, 30 + 5 * c) for a, b, c in _dcc(3, 1.682, 6)
    ]
    ident = identificar_planejamento(_colunas(reais))
    assert ident.tipo == "composto_central"
    f = ident.planejamento.fatores
    assert (f[0].minimo, f[0].maximo) == pytest.approx((40, 60))
    assert (f[1].minimo, f[1].maximo) == pytest.approx((4.5, 7.5))
    assert ident.planejamento.alfa_axial == pytest.approx(1.682, abs=1e-3)


def test_alfa_fora_do_rotacional_gera_aviso() -> None:
    ident = identificar_planejamento(_colunas(_dcc(3, 1.3, centrais=2)))
    assert ident.tipo == "composto_central"
    assert any("rotacional" in a for a in ident.avisos)


def test_box_behnken_dos_casos_validados() -> None:
    for caso in ("go-2022-levofloxacino-hidroxiapatita-bbd",
                 "mazloomi-2023-zif67-metronidazol"):
        dados = ler_dados(CASOS / caso / "dados.csv")
        fatores = list(dados.colunas)[:3]
        ident = identificar_planejamento(
            {f: [float(v) for v in dados.coluna(f)] for f in fatores}
        )
        assert ident.tipo == "box_behnken", caso
        assert ident.n_pontos_centrais == 3


def test_box_behnken_nao_e_confundido_com_fatorial_3k() -> None:
    pontos3k = [tuple(float(v) for v in p)
                for p in itertools.product([-1, 0, 1], repeat=3)]
    assert identificar_planejamento(_colunas(pontos3k)).tipo == "fatorial_3k"


def test_disposicao_irregular_vira_generico_com_aviso() -> None:
    pontos = [(0.1, 2.0), (0.5, 3.0), (0.9, 7.0), (0.2, 4.0), (0.7, 5.5)]
    ident = identificar_planejamento(_colunas(pontos))
    assert ident.tipo == "desconhecido"
    assert ident.avisos
