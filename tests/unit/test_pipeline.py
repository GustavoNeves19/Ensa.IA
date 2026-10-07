"""Testes do pipeline de análise do núcleo (core/pipeline)."""

from __future__ import annotations

import pytest

from ensaia.core.design import Fator, Planejamento, termos_do_modelo
from ensaia.core.pipeline import analisar
from ensaia.core.table import Table


def _planejamento() -> Planejamento:
    return Planejamento(
        tipo="fatorial_completo",
        fatores=[Fator("x1", -1.0, 1.0), Fator("x2", -1.0, 1.0)],
    )


def _tabela_linear() -> Table:
    # Fatorial 2^2 replicado (8 ensaios) com resposta exata y = 5 + 2x1 - x2 + 0,5 x1x2.
    x1 = [-1, 1, -1, 1, -1, 1, -1, 1]
    x2 = [-1, -1, 1, 1, -1, -1, 1, 1]
    y = [5 + 2 * a - b + 0.5 * a * b for a, b in zip(x1, x2, strict=True)]
    return Table.de_colunas({"x1": x1, "x2": x2, "y": y})


def test_analisar_monta_resultado_coerente() -> None:
    termos = termos_do_modelo(["x1", "x2"], incluir_quadraticos=False, grau_interacao=2)
    resultado = analisar(
        _tabela_linear(), _planejamento(), termos, ["y"], versao_ensaia="test"
    )
    assert resultado.fatores == ["x1", "x2"]
    assert resultado.respostas == ["y"]
    assert len(resultado.ajustes) == 1
    ajuste = resultado.ajustes[0]
    assert len(ajuste.coeficientes) == len(termos)
    # Modelo exato: o ajuste tem que recuperar R² = 1.
    assert ajuste.r2 == pytest.approx(1.0, abs=1e-9)
    assert resultado.ponto_otimo is None


def test_analisar_coluna_ausente_falha_claro() -> None:
    plan = Planejamento(
        tipo="fatorial_completo",
        fatores=[Fator("x1", -1.0, 1.0), Fator("nao_existe", -1.0, 1.0)],
    )
    termos = termos_do_modelo(["x1", "nao_existe"], incluir_quadraticos=False)
    with pytest.raises(ValueError, match="ausentes"):
        analisar(_tabela_linear(), plan, termos, ["y"], versao_ensaia="test")


def test_analisar_resposta_com_valor_ausente_falha() -> None:
    tabela = Table.de_colunas(
        {"x1": [-1, 1, -1, 1], "x2": [-1, -1, 1, 1], "y": ["", "2", "3", "4"]}
    )
    termos = termos_do_modelo(["x1", "x2"], incluir_quadraticos=False, grau_interacao=1)
    with pytest.raises(ValueError, match=r"ausentes|numéricos"):
        analisar(tabela, _planejamento(), termos, ["y"], versao_ensaia="test")
