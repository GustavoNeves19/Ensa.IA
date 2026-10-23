"""Indicativos iniciais (US-06) e próximos passos (US-17).

As fixtures são montadas à mão (contrato `AjusteResposta`/`AnalysisResult`
direto), não a partir de um exemplo carregado: `indicativos`/`proximos_passos`
só leem o contrato, então testar com valores escolhidos a dedo é mais preciso
e não depende de nenhum dado real ou tipo de planejamento específico.
"""

from __future__ import annotations

from ensaia.core.indicativos import indicativos, proximos_passos
from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    AnovaRegressao,
    Coeficiente,
    Diagnostico,
    FaltaDeAjuste,
    LinhaAnova,
    MetadadosExecucao,
    PontoEstacionario,
    PontoOtimo,
)


def _ajuste(
    *,
    falta: FaltaDeAjuste | None = None,
    natureza: str | None = None,
    dentro_da_regiao: bool = True,
) -> AjusteResposta:
    ponto_estacionario = (
        PontoEstacionario(
            codificado={"x1": 0.2, "x2": 0.1},
            real={"x1": 52.0, "x2": 6.2},
            natureza=natureza,
            autovalores=[1.0, -1.0] if natureza == "sela" else [-1.0, -1.0],
            resposta_prevista=90.0,
            dentro_da_regiao=dentro_da_regiao,
        )
        if natureza is not None
        else None
    )
    return AjusteResposta(
        resposta="rendimento",
        coeficientes=[
            Coeficiente(
                termo="x1", estimativa=1.0, erro_padrao=0.1, valor_t=10.0,
                valor_p=0.001, significativo=True,
            )
        ],
        anova=[],
        anova_regressao=AnovaRegressao(
            linhas=[
                LinhaAnova(
                    fonte="Regressão", soma_quadrados=10.0, graus_liberdade=2,
                    quadrado_medio=5.0, valor_f=20.0, valor_p=0.001,
                )
            ],
            regressao_significativa=True,
        ),
        r2=0.98,
        r2_ajustado=0.96,
        falta_de_ajuste=falta or FaltaDeAjuste(aplicavel=False),
        n_observacoes=20,
        graus_liberdade_residuo=13,
        termos_incluidos=["Intercepto", "x1"],
        diagnostico=Diagnostico(
            observados=[1.0, 2.0, 3.0],
            preditos=[1.1, 1.9, 3.0],
            residuos=[-0.1, 0.1, 0.0],
            shapiro_p=0.5,
            normalidade_rejeitada=False,
            alavancagem=[0.2, 0.3, 0.1],
            ensaios_influentes=[],
            possiveis_outliers=[],
        ),
        ponto_estacionario=ponto_estacionario,
    )


def _resultado(
    ajuste: AjusteResposta, *, ponto_otimo: PontoOtimo | None = None
) -> AnalysisResult:
    return AnalysisResult(
        tipo_planejamento="composto_central",
        fatores=["x1", "x2"],
        respostas=["rendimento"],
        ajustes=[ajuste],
        metadados=MetadadosExecucao(versao_ensaia="t"),
        ponto_otimo=ponto_otimo,
    )


def test_modelo_bom_tem_sinais_em_ordem_e_cada_um_ligado_a_uma_analise() -> None:
    falta = FaltaDeAjuste(aplicavel=True, valor_p=0.1547, significativa=False)
    ajuste = _ajuste(falta=falta)
    itens = {i.chave: i for i in indicativos(ajuste, 0.05)}
    esperados = {"r2", "regressao", "falta_ajuste", "normalidade", "influentes"}
    assert esperados <= set(itens)
    assert itens["regressao"].situacao == "ok"
    assert itens["falta_ajuste"].valor == "p = 0,1547"
    assert itens["r2"].situacao == "info"
    assert {i.analise for i in itens.values()} <= {"C2", "C3", "C4", "D2", "D4"}


def test_falta_de_ajuste_significativa_vira_atencao_e_passo_sugerido() -> None:
    falta = FaltaDeAjuste(aplicavel=True, valor_p=0.01, significativa=True)
    ajuste = _ajuste(falta=falta)
    sinal = next(i for i in indicativos(ajuste, 0.05) if i.chave == "falta_ajuste")
    assert sinal.situacao == "atencao"
    resultado = _resultado(ajuste)
    assert any("falta de ajuste" in p for p in proximos_passos(resultado))


def test_otimo_na_borda_e_sela_sugerem_deslocar_a_regiao() -> None:
    ajuste = _ajuste(natureza="sela", dentro_da_regiao=False)
    otimo = PontoOtimo(
        coordenadas={"x1": 70.0, "x2": 6.0},
        coordenadas_codificadas={"x1": 1.0, "x2": 0.3},
        resposta_prevista={"rendimento": 95.0},
        desejabilidade_global=0.8,
    )
    passos = proximos_passos(_resultado(ajuste, ponto_otimo=otimo))
    assert any("ponto de sela" in p for p in passos)
    assert any("borda da região" in p for p in passos)
    assert passos[-1].startswith("Faça um ensaio de confirmação")


def test_otimo_no_interior_so_pede_confirmacao() -> None:
    ajuste = _ajuste(natureza="maximo", dentro_da_regiao=True)
    otimo = PontoOtimo(
        coordenadas={"x1": 55.0, "x2": 6.5},
        coordenadas_codificadas={"x1": 0.2, "x2": 0.3},
        resposta_prevista={"rendimento": 95.0},
        desejabilidade_global=0.95,
    )
    passos = proximos_passos(_resultado(ajuste, ponto_otimo=otimo))
    assert len(passos) == 1 and "ensaio de confirmação" in passos[0]
