"""Testes do contêiner de dados `Table` (sem pandas)."""

from __future__ import annotations

import numpy as np
import pytest

from ensaia.core.table import Table


def test_de_colunas_infere_numerica_e_texto() -> None:
    t = Table.de_colunas({"x": [1, 2, 3], "rotulo": ["a", "b", "c"]})
    assert t.colunas == ("x", "rotulo")
    assert len(t) == 3
    assert t.e_numerica("x")
    assert not t.e_numerica("rotulo")
    assert t.coluna("x").tolist() == [1.0, 2.0, 3.0]


def test_virgula_decimal_e_celula_vazia() -> None:
    t = Table.de_colunas({"y": ["1,5", "", "3.0"]})
    valores = t.coluna("y")
    assert valores[0] == 1.5
    assert np.isnan(valores[1])
    assert valores[2] == 3.0


def test_coluna_de_texto_recusa_acesso_numerico() -> None:
    t = Table.de_colunas({"rotulo": ["a", "b"]})
    with pytest.raises(ValueError, match="texto"):
        t.coluna("rotulo")


def test_coluna_inexistente_lista_as_disponiveis() -> None:
    t = Table.de_colunas({"x": [1.0]})
    with pytest.raises(KeyError, match="não existe"):
        t.coluna("z")


def test_texto_formata_numeros_sem_casas_desnecessarias() -> None:
    t = Table.de_colunas({"x": [1.0, 2.5, 3.0]})
    assert t.texto("x") == ("1", "2.5", "3")


def test_colunas_com_tamanhos_diferentes_falham() -> None:
    with pytest.raises(ValueError, match="linhas diferentes"):
        Table(
            colunas=("a", "b"),
            valores={"a": np.array([1.0]), "b": np.array([1.0, 2.0])},
        )


def test_tem_indica_presenca() -> None:
    t = Table.de_colunas({"x": [1.0]})
    assert t.tem("x")
    assert not t.tem("y")
