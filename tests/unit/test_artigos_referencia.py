"""Artigos de referência de DCCR (spec v0.6 §14.3): R1 e R2.

R1 é Bezerra et al. (2022), pão de forma (Statistica, erro puro); R2 é Silva,
Pereira e Almeida (2023), bombeamento de água (Protimiza, resíduo). Os dois
casos estão em `casos_de_estudo/` como rascunho (falta a dupla conferência
humana), por isso a regressão geral os pula; aqui eles rodam direto, porque a
reprodução dos números é teste de software (§14.2), não hipótese do TCC.

Procedência e ressalvas de cada número: o `fonte.md` de cada caso.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ensaia.core.design import Fator, Planejamento, termos_do_modelo
from ensaia.core.identificacao import identificar_planejamento
from ensaia.core.pipeline import analisar
from ensaia.io.readers import ler_dados
from ensaia.validation.runner import validar_caso

CASOS = Path(__file__).parents[2] / "casos_de_estudo"
R1 = CASOS / "bezerra-2022-pao-de-forma"
R2 = CASOS / "silva-2023-bombeamento-agua"


@pytest.mark.parametrize("caso", [R1, R2], ids=lambda c: c.name)
def test_coeficientes_e_significancia_como_no_artigo(caso: Path) -> None:
    """§4.3 (a) e (b): todo coeficiente a menos de 5% e a mesma significância."""
    resultado = validar_caso(caso)
    for resposta, metricas in resultado["metricas"].items():
        erro = metricas["erro_coeficientes"]
        assert erro.proporcao_dentro_tolerancia == 1.0, (
            f"{resposta}: máx {erro.erro_relativo_maximo_pct}%"
        )
        assert metricas["concordancia_significancia"].taxa_concordancia == 1.0


@pytest.mark.parametrize("caso", [R1, R2], ids=lambda c: c.name)
def test_matriz_do_artigo_e_reconhecida_como_dccr(caso: Path) -> None:
    tabela = ler_dados(caso / "dados.csv")
    fatores = tabela.colunas[:3]
    ident = identificar_planejamento({f: list(tabela.coluna(f)) for f in fatores})
    assert ident.tipo == "composto_central"


# Efeitos publicados (Tabela 7 de R1, Statistica), na ordem dos termos abaixo:
# as três respostas que ficaram fora do caso por causa do limite de 5 respostas.
_TERMOS_R1 = [
    "extrato", "extrato^2", "fermento", "fermento^2", "gordura", "gordura^2",
    "extrato:fermento", "extrato:gordura", "fermento:gordura",
]  # fmt: skip
_EFEITOS_R1 = {
    "textura": [
        (-0.06793, 0.670924), (-1.20398, 0.015511), (4.26770, 0.001042),
        (-2.42253, 0.003899), (-0.38887, 0.106036), (-1.33183, 0.012729),
        (0.67549, 0.064307), (-0.15893, 0.470622), (0.56239, 0.089065),
    ],
    "aroma": [
        (-0.55449, 0.005639), (-0.84288, 0.002968), (2.34847, 0.000317),
        (-1.50874, 0.000929), (0.59627, 0.004882), (-1.10804, 0.001721),
        (0.87698, 0.003858), (1.13690, 0.002301), (-1.23810, 0.001941),
    ],
    "caract_interna_crosta": [
        (-0.039702, 0.890842), (-0.437650, 0.260116), (0.526796, 0.175498),
        (-0.487201, 0.225506), (0.715913, 0.107368), (-0.287390, 0.414515),
        (0.570284, 0.229883), (-0.355998, 0.398146), (-0.772665, 0.146813),
    ],
}  # fmt: skip


@pytest.mark.parametrize("resposta", list(_EFEITOS_R1))
def test_r1_respostas_fora_do_caso(resposta: str) -> None:
    tabela = ler_dados(R1 / "dados.csv")
    nomes = ["extrato", "fermento", "gordura"]
    plan = Planejamento(
        tipo="composto_central", fatores=[Fator(n, -1.0, 1.0) for n in nomes]
    )
    ajuste = analisar(
        tabela,
        plan,
        termos_do_modelo(nomes),
        [resposta],
        versao_ensaia="test",
        termo_erro="erro_puro",
    ).ajustes[0]
    coef = {c.termo: c for c in ajuste.coeficientes}
    for termo, (efeito, p) in zip(_TERMOS_R1, _EFEITOS_R1[resposta], strict=True):
        assert coef[termo].estimativa == pytest.approx(efeito / 2, rel=0.05)
        assert coef[termo].significativo is (p < 0.05)


def test_r2_modelo_reduzido_da_equacao_18() -> None:
    """Equação 18 e Tabela 12 (p. 22): os autores reduziram e reajustaram."""
    tabela = ler_dados(R2 / "dados.csv")
    nomes = ["rendimento_cmb", "vre", "hg"]
    plan = Planejamento(
        tipo="composto_central", fatores=[Fator(n, -1.0, 1.0) for n in nomes]
    )
    termos = [
        "Intercepto", "rendimento_cmb", "rendimento_cmb^2", "vre", "hg", "hg^2",
        "rendimento_cmb:hg",
    ]  # fmt: skip
    ajuste = analisar(
        tabela, plan, termos, ["consumo_kwh_mes"], versao_ensaia="test"
    ).ajustes[0]
    coef = {c.termo: c.estimativa for c in ajuste.coeficientes}
    publicados = {
        "Intercepto": 6128.94,
        "rendimento_cmb": -2832.67,
        "rendimento_cmb^2": 1242.36,
        "vre": 400.49,
        "hg": 789.79,
        "hg^2": 583.42,
        "rendimento_cmb:hg": -298.42,
    }
    for termo, valor in publicados.items():
        assert coef[termo] == pytest.approx(valor, abs=0.01)

    # Tabela 12: R² = 99,27%; regressão SQ 136.365.536,42 com 6 g.l., F = 180,67.
    assert ajuste.r2 == pytest.approx(0.9927, abs=5e-5)
    reg = ajuste.anova_regressao
    assert reg is not None
    regressao = next(li for li in reg.linhas if li.fonte == "Regressão")
    assert regressao.graus_liberdade == 6
    assert regressao.soma_quadrados == pytest.approx(136365536.42, rel=1e-6)
    assert regressao.valor_f == pytest.approx(180.67, abs=0.01)
