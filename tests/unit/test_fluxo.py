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


def test_fator_tem_poucos_niveis_e_resposta_varia_por_ensaio() -> None:
    # Fatorial 2³ do Box com a numeração "run_std" e colunas do Minitab.
    tabela = Table.de_colunas(
        {
            "run_std": [1, 2, 3, 4, 5, 6, 7, 8],
            "CenterPt": [1] * 8,
            "Blocks": [1] * 8,
            "T": [-1, 1, -1, 1, -1, 1, -1, 1],
            "C": [-1, -1, 1, 1, -1, -1, 1, 1],
            "K": [-1, -1, -1, -1, 1, 1, 1, 1],
            "y": [60, 72, 54, 68, 52, 83, 45, 80],
            "pureza": [91.2, 93.4, 90.1, 92.8, 89.9, 95.0, 88.7, 94.1],
        }
    )
    assert sugerir_mapeamento(tabela) == {
        "run_std": "ordem",
        "CenterPt": "ignorar",
        "Blocks": "ignorar",
        "T": "fator",
        "C": "fator",
        "K": "fator",
        "y": "resposta",
        "pureza": "resposta",
    }


def test_numeracao_sem_nome_de_ordem_nao_vira_fator() -> None:
    tabela = Table.de_colunas(
        {
            "planejamento": [1, 2, 3, 4, 5, 6],
            "tempo": [30, 30, 60, 60, 45, 45],
            "rend": [61.2, 64.0, 70.4, 72.9, 68.0, 67.5],
        }
    )
    assert sugerir_mapeamento(tabela)["planejamento"] == "ignorar"


def test_respostas_alem_do_limite_comecam_ignoradas() -> None:
    colunas: dict[str, list[object]] = {"tempo": [30, 30, 60, 60, 45, 45, 45]}
    for i in range(7):
        colunas[f"r{i}"] = [float(j * (i + 1)) + 0.5 for j in range(7)]
    papeis = sugerir_mapeamento(Table.de_colunas(colunas))
    assert [c for c, p in papeis.items() if p == "resposta"] == [
        "r0",
        "r1",
        "r2",
        "r3",
        "r4",
    ]
    assert papeis["r5"] == papeis["r6"] == "ignorar"


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
