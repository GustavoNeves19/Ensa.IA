"""Indicativos iniciais (US-06) e próximos passos (US-17)."""

from __future__ import annotations

from ensaia.core.fluxo import analisar_tabela
from ensaia.core.indicativos import indicativos, proximos_passos
from ensaia.core.results import FaltaDeAjuste
from ensaia.exemplos import carregar_exemplo


def _exemplo(nome: str):
    tabela, _ = carregar_exemplo(nome)
    colunas = list(tabela.colunas)
    return analisar_tabela(
        tabela,
        colunas[:-1],
        [colunas[-1]],
        versao_ensaia="t",
        objetivos={colunas[-1]: "maximizar"},
    ).resultado


def test_modelo_bom_tem_sinais_em_ordem_e_cada_um_ligado_a_uma_analise() -> None:
    resultado = _exemplo("metronidazol")
    itens = {i.chave: i for i in indicativos(resultado.ajustes[0], 0.05)}
    esperados = {"r2", "regressao", "falta_ajuste", "normalidade", "influentes"}
    assert esperados <= set(itens)
    assert itens["regressao"].situacao == "ok"
    assert itens["falta_ajuste"].valor == "p = 0,1547"
    assert itens["r2"].situacao == "info"
    assert {i.analise for i in itens.values()} <= {"C2", "C3", "C4", "D2", "D4"}


def test_falta_de_ajuste_significativa_vira_atencao_e_passo_sugerido() -> None:
    resultado = _exemplo("metronidazol")
    ajuste = resultado.ajustes[0].model_copy(
        update={
            "falta_de_ajuste": FaltaDeAjuste(
                aplicavel=True, valor_p=0.01, significativa=True
            )
        }
    )
    sinal = next(i for i in indicativos(ajuste, 0.05) if i.chave == "falta_ajuste")
    assert sinal.situacao == "atencao"
    com_falta = resultado.model_copy(update={"ajustes": [ajuste]})
    assert any("falta de ajuste" in p for p in proximos_passos(com_falta))


def test_otimo_na_borda_e_sela_sugerem_deslocar_a_regiao() -> None:
    passos = proximos_passos(_exemplo("levofloxacino"))
    assert any("ponto de sela" in p for p in passos)
    assert any("borda da região" in p for p in passos)
    assert passos[-1].startswith("Faça um ensaio de confirmação")


def test_otimo_no_interior_so_pede_confirmacao() -> None:
    passos = proximos_passos(_exemplo("metronidazol"))
    assert len(passos) == 1 and "ensaio de confirmação" in passos[0]
