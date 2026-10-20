"""Exemplos públicos, planilha-modelo, previsão de uma condição e limites."""

from __future__ import annotations

import pytest

from ensaia.core.identificacao import identificar_planejamento
from ensaia.core.pipeline import MAX_FATORES, MAX_RESPOSTAS, analisar
from ensaia.core.surface import prever_condicao
from ensaia.core.table import Table
from ensaia.exemplos import EXEMPLOS, carregar_exemplo
from ensaia.io.modelo import planilha_modelo_xlsx
from ensaia.io.readers import ler_dados_de_bytes, listar_abas


@pytest.mark.parametrize("id_", sorted(EXEMPLOS))
def test_exemplos_carregam_e_sao_dccr(id_: str) -> None:
    tabela, nome = carregar_exemplo(id_)
    assert nome.endswith(".csv")
    fatores = list(tabela.colunas)[:3]
    ident = identificar_planejamento(
        {f: [float(v) for v in tabela.coluna(f)] for f in fatores}
    )
    assert ident.tipo == "composto_central"
    assert "DOI" in EXEMPLOS[id_].citacao


def test_planilha_modelo_e_lida_pelo_proprio_ensaia() -> None:
    conteudo = planilha_modelo_xlsx()
    assert listar_abas(conteudo, "modelo.xlsx") == ["Dados", "Como preencher"]
    tabela = ler_dados_de_bytes(conteudo, "modelo.xlsx", aba="Dados")
    assert list(tabela.colunas) == [
        "Ensaio", "Temperatura (°C)", "Tempo (min)", "pH", "Rendimento (%)"
    ]
    assert len(tabela) == 20
    fatores = ["Temperatura (°C)", "Tempo (min)", "pH"]
    ident = identificar_planejamento(
        {f: [float(v) for v in tabela.coluna(f)] for f in fatores}
    )
    assert ident.tipo == "composto_central" and ident.n_pontos_centrais == 6


def test_prever_condicao_bate_com_a_equacao_e_avisa_extrapolacao() -> None:
    from tests.unit.test_modelo_opcoes import TERMOS, _dccr

    tabela, plan = _dccr()
    ajuste = analisar(tabela, plan, TERMOS, ["y"], versao_ensaia="t").ajustes[0]
    previstas, extrapola = prever_condicao(
        [ajuste], plan.fatores, {"temp": 60, "ph": 7}
    )
    intercepto = next(
        c.estimativa for c in ajuste.coeficientes if c.termo == "Intercepto"
    )
    assert previstas["y"] == pytest.approx(intercepto)  # centro: só o intercepto
    assert not extrapola
    _, fora = prever_condicao(
        [ajuste], plan.fatores, {"temp": 90, "ph": 7}, limite_codificado=1.414
    )
    assert fora
    with pytest.raises(ValueError, match="Informe"):
        prever_condicao([ajuste], plan.fatores, {"temp": 60})


def test_limites_de_fatores_e_respostas() -> None:
    from ensaia.core.design import Fator, Planejamento

    n = 20
    colunas = {f"x{i}": [float((j + i) % 2) for j in range(n)] for i in range(8)}
    colunas.update({f"y{i}": [float(j) for j in range(n)] for i in range(6)})
    tabela = Table.de_colunas(colunas)
    muitos = Planejamento(
        "desconhecido", [Fator(f"x{i}", 0, 1) for i in range(MAX_FATORES + 1)]
    )
    with pytest.raises(ValueError, match="até 7 fatores"):
        analisar(tabela, muitos, ["Intercepto"], ["y0"], versao_ensaia="t")
    poucos = Planejamento("desconhecido", [Fator("x0", 0, 1)])
    respostas = [f"y{i}" for i in range(MAX_RESPOSTAS + 1)]
    with pytest.raises(ValueError, match="até 5 respostas"):
        analisar(tabela, poucos, ["Intercepto", "x0"], respostas, versao_ensaia="t")


def test_upload_pula_aba_sem_dados_e_avisa_quando_ela_e_escolhida() -> None:
    from pathlib import Path

    from ensaia.ui.upload import _ler

    caminho = Path(__file__).parents[1] / "fixtures" / "planilhas" / "duas_abas.xls"
    conteudo = caminho.read_bytes()
    abas = listar_abas(conteudo, "duas_abas.xls")
    tabela, aba, erro = _ler(conteudo, "duas_abas.xls", abas, None, None)
    assert aba == "Ensaios" and tabela is not None and not erro
    tabela, aba, erro = _ler(conteudo, "duas_abas.xls", abas, "Leia-me", None)
    assert tabela is None and aba == "Leia-me"
    assert erro == "A aba 'Leia-me' não tem dados de ensaios."
