"""Ponto estacionário (E3), ótimo de uma resposta (E4) e desejabilidade (E5)."""

from __future__ import annotations

import numpy as np
import pytest

from ensaia.core.design import Fator
from ensaia.core.desirability import AlvoResposta, metas_padrao, otimizar
from ensaia.core.results import AjusteResposta, Coeficiente, Diagnostico, FaltaDeAjuste
from ensaia.core.surface import ponto_estacionario

FATORES = [Fator("a", 10.0, 30.0), Fator("b", 1.0, 3.0)]


def _ajuste(
    nome: str,
    coefs: dict[str, float],
    observados: tuple[float, float],
    r2: float = 0.95,
) -> AjusteResposta:
    lista = [
        Coeficiente(
            termo=t, estimativa=v, erro_padrao=0.1, valor_t=v / 0.1, valor_p=0.01,
            significativo=True,
        )
        for t, v in coefs.items()
    ]
    baixo, alto = observados
    return AjusteResposta(
        resposta=nome,
        coeficientes=lista,
        anova=[],
        r2=r2,
        r2_ajustado=r2,
        falta_de_ajuste=FaltaDeAjuste(aplicavel=False),
        n_observacoes=13,
        graus_liberdade_residuo=7,
        termos_incluidos=list(coefs),
        diagnostico=Diagnostico(
            observados=[baixo, alto], preditos=[baixo, alto], residuos=[0.0, 0.0]
        ),
    )


# ŷ = 10 + 2a − 4b − 3a² − 2b² + 1·a·b  (escala codificada): côncava, máximo interno.
CONCAVA = {"Intercepto": 10, "a": 2, "b": -4, "a^2": -3, "b^2": -2, "a:b": 1}


def test_ponto_estacionario_zera_o_gradiente_e_e_maximo() -> None:
    p = ponto_estacionario(_ajuste("y", CONCAVA, (0, 12)), FATORES)
    assert p is not None
    x, z = p.codificado["a"], p.codificado["b"]
    assert 2 - 6 * x + z == pytest.approx(0, abs=1e-9)  # ∂ŷ/∂a
    assert -4 - 4 * z + x == pytest.approx(0, abs=1e-9)  # ∂ŷ/∂b
    assert p.natureza == "maximo" and all(v < 0 for v in p.autovalores)
    assert p.dentro_da_regiao
    assert p.real["a"] == pytest.approx(20 + 10 * x)
    esperado = 10 + 2 * x - 4 * z - 3 * x**2 - 2 * z**2 + x * z
    assert p.resposta_prevista == pytest.approx(esperado)


def test_ponto_de_sela_e_sem_quadratico() -> None:
    sela = {"Intercepto": 0, "a": 1, "b": 1, "a^2": 2, "b^2": -2}
    p = ponto_estacionario(_ajuste("y", sela, (0, 1)), FATORES)
    assert p is not None and p.natureza == "sela"
    sem = {"Intercepto": 0, "a": 1, "b": 1, "a^2": 2}
    assert ponto_estacionario(_ajuste("y", sem, (0, 1)), FATORES) is None


def test_otimo_numerico_coincide_com_o_ponto_estacionario() -> None:
    ajuste = _ajuste("y", CONCAVA, (0, 12))
    estacionario = ponto_estacionario(ajuste, FATORES)
    otimo, avisos = otimizar(
        [ajuste], FATORES, metas_padrao([ajuste], {"y": "maximizar"})
    )
    assert otimo is not None and not avisos
    assert otimo.metodo == "resposta_unica"
    assert estacionario is not None
    for f in ("a", "b"):
        assert otimo.coordenadas_codificadas[f] == pytest.approx(
            estacionario.codificado[f], abs=1e-4
        )
    assert otimo.resposta_prevista["y"] == pytest.approx(
        estacionario.resposta_prevista, abs=1e-6
    )


def test_modelo_linear_tem_otimo_no_canto() -> None:
    ajuste = _ajuste("y", {"Intercepto": 5, "a": 2, "b": -1}, (0, 10))
    otimo, _ = otimizar([ajuste], FATORES, metas_padrao([ajuste], {"y": "maximizar"}))
    assert otimo is not None
    assert otimo.coordenadas_codificadas == pytest.approx({"a": 1.0, "b": -1.0})
    assert otimo.coordenadas == pytest.approx({"a": 30.0, "b": 1.0})
    minimo, _ = otimizar([ajuste], FATORES, metas_padrao([ajuste], {"y": "minimizar"}))
    assert minimo is not None
    assert minimo.coordenadas_codificadas == pytest.approx({"a": -1.0, "b": 1.0})


def test_desejabilidade_equilibra_respostas_em_conflito() -> None:
    sobe = _ajuste("y1", {"Intercepto": 10, "a": 5}, (5, 15))
    desce = _ajuste("y2", {"Intercepto": 10, "a": 5}, (5, 15))
    metas = [
        AlvoResposta("y1", "maximizar", 5, 15),
        AlvoResposta("y2", "minimizar", 5, 15),
    ]
    otimo, _ = otimizar([sobe, desce], FATORES, metas)
    assert otimo is not None and otimo.metodo == "desejabilidade"
    # d1 = (1 + a)/2, d2 = (1 − a)/2 → D = √(d1·d2), máximo 0,5 em a = 0.
    assert otimo.coordenadas_codificadas["a"] == pytest.approx(0.0, abs=1e-3)
    assert otimo.desejabilidade_global == pytest.approx(0.5, abs=1e-4)


def test_meta_de_alvo() -> None:
    ajuste = _ajuste("y", {"Intercepto": 10, "a": 5}, (5, 15))
    metas = [AlvoResposta("y", "alvo", 5, 15, alvo=12.5)]
    otimo, _ = otimizar([ajuste], FATORES, metas)
    assert otimo is not None
    assert otimo.resposta_prevista["y"] == pytest.approx(12.5, abs=1e-3)
    assert otimo.desejabilidade_global == pytest.approx(1.0, abs=1e-3)


def test_r2_baixo_recusa_a_otimizacao() -> None:
    fraco = _ajuste("y", CONCAVA, (0, 12), r2=0.3)
    metas = metas_padrao([fraco], {"y": "maximizar"})
    otimo, avisos = otimizar([fraco], FATORES, metas)
    assert otimo is None
    assert any("R²" in a for a in avisos)


def test_busca_e_reprodutivel_e_respeita_alfa() -> None:
    ajuste = _ajuste("y", {"Intercepto": 5, "a": 2, "b": -1}, (0, 10))
    metas = metas_padrao([ajuste], {"y": "maximizar"})
    a, _ = otimizar([ajuste], FATORES, metas, limite_codificado=1.682)
    b, _ = otimizar([ajuste], FATORES, metas, limite_codificado=1.682)
    assert a == b
    assert a is not None
    assert np.max(np.abs(list(a.coordenadas_codificadas.values()))) == pytest.approx(
        1.682
    )
