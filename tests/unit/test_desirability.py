"""Testes das funções de desejabilidade de Derringer-Suich (issue #6).

Cobre as funções puras `AlvoResposta`, `desejabilidade_individual` e
`desejabilidade_global`. A busca do ótimo (`otimizar`) tem design próprio e
ainda não é coberta aqui.
"""

from __future__ import annotations

import math

import pytest

from lyra.core.desirability import (
    AlvoResposta,
    desejabilidade_global,
    desejabilidade_individual,
)


def _max(*, s: float = 1.0, peso: float = 1.0) -> AlvoResposta:
    return AlvoResposta(
        resposta="y",
        sentido="maximizar",
        limite_inferior=0.0,
        limite_superior=10.0,
        s=s,
        peso=peso,
    )


# --- maximizar ---------------------------------------------------------------


def test_maximizar_satura_nos_extremos() -> None:
    alvo = _max()
    assert desejabilidade_individual(-1.0, alvo) == 0.0
    assert desejabilidade_individual(0.0, alvo) == 0.0
    assert desejabilidade_individual(10.0, alvo) == 1.0
    assert desejabilidade_individual(99.0, alvo) == 1.0


def test_maximizar_linear_no_meio() -> None:
    alvo = _max()
    assert desejabilidade_individual(5.0, alvo) == pytest.approx(0.5)
    assert desejabilidade_individual(2.5, alvo) == pytest.approx(0.25)


def test_forma_s_muda_a_curvatura() -> None:
    alvo = _max(s=2.0)
    # Em s=2, a meia-faixa vale 0,5^2 = 0,25.
    assert desejabilidade_individual(5.0, alvo) == pytest.approx(0.25)


# --- minimizar ---------------------------------------------------------------


def test_minimizar_e_o_espelho_de_maximizar() -> None:
    alvo = AlvoResposta(
        resposta="impureza",
        sentido="minimizar",
        limite_inferior=0.0,
        limite_superior=10.0,
    )
    assert desejabilidade_individual(-1.0, alvo) == 1.0
    assert desejabilidade_individual(0.0, alvo) == 1.0
    assert desejabilidade_individual(10.0, alvo) == 0.0
    assert desejabilidade_individual(99.0, alvo) == 0.0
    assert desejabilidade_individual(2.5, alvo) == pytest.approx(0.75)


# --- alvo --------------------------------------------------------------------


def test_alvo_sobe_ate_o_pico_e_desce() -> None:
    alvo = AlvoResposta(
        resposta="ph",
        sentido="alvo",
        limite_inferior=4.0,
        limite_superior=10.0,
        alvo=7.0,
    )
    assert desejabilidade_individual(7.0, alvo) == pytest.approx(1.0)
    assert desejabilidade_individual(4.0, alvo) == pytest.approx(0.0)
    assert desejabilidade_individual(10.0, alvo) == pytest.approx(0.0)
    assert desejabilidade_individual(5.5, alvo) == pytest.approx(0.5)  # meio da subida
    assert desejabilidade_individual(8.5, alvo) == pytest.approx(0.5)  # meio da descida
    assert desejabilidade_individual(3.0, alvo) == 0.0
    assert desejabilidade_individual(11.0, alvo) == 0.0


# --- desejabilidade global ---------------------------------------------------


def test_global_e_media_geometrica() -> None:
    d = desejabilidade_global([0.25, 0.64], [1.0, 1.0])
    assert d == pytest.approx(math.sqrt(0.25 * 0.64))


def test_global_respeita_pesos() -> None:
    # Peso maior na segunda resposta puxa D para perto dela.
    d = desejabilidade_global([0.2, 0.8], [1.0, 3.0])
    esperado = math.exp((1 * math.log(0.2) + 3 * math.log(0.8)) / 4)
    assert d == pytest.approx(esperado)


def test_global_veta_quando_qualquer_desejabilidade_zera() -> None:
    assert desejabilidade_global([0.0, 0.9, 0.9], [1.0, 1.0, 1.0]) == 0.0


def test_global_de_tudo_otimo_e_um() -> None:
    assert desejabilidade_global([1.0, 1.0], [1.0, 2.0]) == pytest.approx(1.0)


# --- validações --------------------------------------------------------------


def test_alvo_sem_valor_alvo_falha() -> None:
    with pytest.raises(ValueError, match="valor-alvo"):
        AlvoResposta("y", "alvo", 0.0, 10.0)


def test_alvo_fora_dos_limites_falha() -> None:
    with pytest.raises(ValueError, match="entre os limites"):
        AlvoResposta("y", "alvo", 0.0, 10.0, alvo=10.0)


def test_limites_invertidos_falham() -> None:
    with pytest.raises(ValueError, match="limite_superior"):
        AlvoResposta("y", "maximizar", 10.0, 0.0)


def test_forma_e_peso_nao_positivos_falham() -> None:
    with pytest.raises(ValueError, match="forma 's'"):
        _max(s=0.0)
    with pytest.raises(ValueError, match="peso"):
        _max(peso=0.0)


def test_global_tamanhos_incompativeis_falham() -> None:
    with pytest.raises(ValueError, match="difere do de pesos"):
        desejabilidade_global([0.5, 0.5], [1.0])


def test_global_desejabilidade_fora_de_faixa_falha() -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        desejabilidade_global([1.5], [1.0])
