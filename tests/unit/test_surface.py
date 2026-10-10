"""Testes da grade de superfície de resposta (core/surface)."""

from __future__ import annotations

import numpy as np
import pytest

from ensaia.core.design import Fator
from ensaia.core.results import AjusteResposta, Coeficiente, FaltaDeAjuste
from ensaia.core.surface import grade_superficie, prever


def _coef(termo: str, valor: float) -> Coeficiente:
    return Coeficiente(
        termo=termo,
        estimativa=valor,
        erro_padrao=0.1,
        valor_t=valor / 0.1,
        valor_p=0.01,
        significativo=True,
    )


def _ajuste() -> AjusteResposta:
    # ŷ = 10 + 2·a − 3·b + 1·c + 0,5·a·b − 4·a²   (escala codificada)
    coefs = [
        _coef("Intercepto", 10.0),
        _coef("a", 2.0),
        _coef("b", -3.0),
        _coef("c", 1.0),
        _coef("a:b", 0.5),
        _coef("a^2", -4.0),
    ]
    return AjusteResposta(
        resposta="y",
        coeficientes=coefs,
        anova=[],
        r2=0.9,
        r2_ajustado=0.8,
        falta_de_ajuste=FaltaDeAjuste(aplicavel=False),
        n_observacoes=15,
        graus_liberdade_residuo=9,
        termos_incluidos=[c.termo for c in coefs],
    )


FATORES = [Fator("a", 20.0, 40.0), Fator("b", 1.0, 3.0), Fator("c", 0.0, 10.0)]


def _modelo(a: float, b: float, c: float) -> float:
    return 10 + 2 * a - 3 * b + 1 * c + 0.5 * a * b - 4 * a**2


def test_prever_bate_com_a_equacao() -> None:
    pontos = {"a": np.array([-1.0, 0.0, 1.0]), "b": np.array([1.0, 0.0, -1.0]),
              "c": np.array([0.0, 0.5, -1.0])}
    z = prever(_ajuste(), pontos)
    esperado = [_modelo(-1, 1, 0), _modelo(0, 0, 0.5), _modelo(1, -1, -1)]
    assert z == pytest.approx(esperado)


def test_prever_sem_um_fator_do_modelo_falha_claro() -> None:
    with pytest.raises(ValueError, match="não foi informado"):
        prever(_ajuste(), {"a": np.zeros(2), "b": np.zeros(2)})


def test_grade_tem_25x25_e_cantos_corretos() -> None:
    g = grade_superficie(_ajuste(), FATORES, "a", "b")
    assert len(g.valores_x) == 25 and len(g.valores_y) == 25
    assert len(g.z) == 25 and all(len(linha) == 25 for linha in g.z)
    # Eixos em unidades reais, cobrindo a faixa do experimento.
    assert (g.valores_x[0], g.valores_x[-1]) == pytest.approx((20.0, 40.0))
    assert (g.valores_y[0], g.valores_y[-1]) == pytest.approx((1.0, 3.0))
    # c fica no centro (5,0 real = 0 codificado) por padrão.
    assert g.fixos == {"c": 5.0}
    # z[i][j] = previsão em x = valores_x[j], y = valores_y[i].
    assert g.z[0][0] == pytest.approx(_modelo(-1, -1, 0))
    assert g.z[0][-1] == pytest.approx(_modelo(1, -1, 0))
    assert g.z[-1][0] == pytest.approx(_modelo(-1, 1, 0))
    assert g.z[12][12] == pytest.approx(_modelo(0, 0, 0))


def test_fator_fixo_em_valor_escolhido() -> None:
    g = grade_superficie(_ajuste(), FATORES, "a", "b", fixos={"c": 10.0})
    assert g.fixos == {"c": 10.0}
    assert g.z[12][12] == pytest.approx(_modelo(0, 0, 1))


def test_eixos_trocados_transpoem_a_grade() -> None:
    g1 = grade_superficie(_ajuste(), FATORES, "a", "b", pontos=5)
    g2 = grade_superficie(_ajuste(), FATORES, "b", "a", pontos=5)
    assert np.array(g1.z) == pytest.approx(np.array(g2.z).T)


def test_limites_e_extremos() -> None:
    g = grade_superficie(_ajuste(), FATORES, "a", "b", pontos=3)
    valores = [v for linha in g.z for v in linha]
    assert g.z_minimo == pytest.approx(min(valores))
    assert g.z_maximo == pytest.approx(max(valores))


@pytest.mark.parametrize(
    ("x", "y", "mensagem"),
    [("a", "a", "diferentes"), ("a", "zz", "não existe")],
)
def test_eixos_invalidos(x: str, y: str, mensagem: str) -> None:
    with pytest.raises(ValueError, match=mensagem):
        grade_superficie(_ajuste(), FATORES, x, y)
