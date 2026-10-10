"""Fluxo compartilhado da tela e do MCP: papéis sugeridos e CSV normalizado."""

from __future__ import annotations

import pytest

from ensaia.core.fluxo import analisar_tabela, sugerir_mapeamento
from ensaia.core.table import Table
from ensaia.io.escrita import tabela_para_csv
from ensaia.io.readers import ler_dados_de_bytes


def _tabela() -> Table:
    return Table.de_colunas(
        {
            "Ensaio": [3, 1, 2, 4],
            "lote": ["A", "B", "=SOMA(1)", "-x"],
            "temp": [40, 60, 40, 60],
            "ph": [5.0, 5.0, 7.5, 7.5],
            "rend": [61.2, 70.4, 64.9, 79.3],
        }
    )


def test_sugere_ordem_texto_fatores_e_ultima_numerica_como_resposta() -> None:
    assert sugerir_mapeamento(_tabela()) == {
        "Ensaio": "ordem",
        "lote": "ignorar",
        "temp": "fator",
        "ph": "fator",
        "rend": "resposta",
    }


def test_coluna_de_ordem_no_fim_nao_rouba_o_papel_de_resposta() -> None:
    tabela = Table.de_colunas(
        {"temp": [40, 60, 40, 60], "rend": [1.0, 2.0, 3.0, 4.5], "n": [1, 2, 3, 4]}
    )
    papeis = sugerir_mapeamento(tabela)
    assert papeis["n"] == "ordem" and papeis["rend"] == "resposta"


def test_csv_normalizado_volta_igual_e_neutraliza_formulas_em_texto() -> None:
    tabela = _tabela()
    csv = tabela_para_csv(tabela)
    assert "'=SOMA(1)" in csv and "'-x" in csv
    relida = ler_dados_de_bytes(csv.encode("utf-8"), "dados.csv")
    assert relida.colunas == tabela.colunas
    assert list(relida.coluna("ph")) == list(tabela.coluna("ph"))


def test_analise_sem_fator_ou_resposta_explica_o_que_falta() -> None:
    with pytest.raises(ValueError, match="fator"):
        analisar_tabela(_tabela(), [], ["rend"], versao_ensaia="t")
    with pytest.raises(ValueError, match="resposta"):
        analisar_tabela(_tabela(), ["temp"], [], versao_ensaia="t")
