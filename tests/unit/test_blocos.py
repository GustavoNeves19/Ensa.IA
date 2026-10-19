"""Blocos: a diferença entre blocos sai do erro, sem mudar os efeitos.

Dois conjuntos publicados servem de referência:

- **npk** (Yates; `datasets::npk` do R): fatorial 2³ em 6 blocos de 4, com a
  interação N:P:K confundida com os blocos. A análise clássica com o bloco no
  modelo (`summary(aov(yield ~ block + N*P*K, npk))`) dá p = 0,00437 para N e
  p = 0,0288 para K; sem o bloco, K deixa de ser significativo.
- **ChemReact** (Myers, Montgomery e Anderson-Cook, Tabela 7.6; `rsm::ChemReact`):
  composto central em 2 blocos. Com o bloco, R² = 0,9981 e o ponto
  estacionário é um máximo em Time ≈ 86,86 e Temp ≈ 176,67.

O statsmodels (só dependência de teste) é o oráculo independente para os
coeficientes, os erros-padrão e a soma de quadrados dos blocos.
"""

from __future__ import annotations

import pytest

from ensaia.core.blocos import com_blocos, ler_blocos
from ensaia.core.catalogo import disponibilidade
from ensaia.core.fluxo import analisar_tabela, sugerir_mapeamento
from ensaia.core.identificacao import identificar_planejamento
from ensaia.core.model import matriz_modelo, termos_redundantes
from ensaia.core.table import Table

# npk (R: datasets::npk), na ordem do R.
_NPK = {
    "rownames": list(range(1, 25)),
    "block": [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6],
    "N": [0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0],
    "P": [1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0],
    "K": [1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0],
    "yield": [
        49.5,
        62.8,
        46.8,
        57.0,
        59.8,
        58.5,
        55.5,
        56.0,
        62.8,
        55.8,
        69.5,
        55.0,
        62.0,
        48.8,
        45.5,
        44.2,
        52.0,
        51.5,
        49.8,
        48.8,
        57.2,
        59.0,
        53.2,
        56.0,
    ],
}

# ChemReact (R: rsm::ChemReact).
_CHEMREACT = {
    "Time": [80, 80, 90, 90, 85, 85, 85, 85, 85, 85, 92.07, 77.93, 85, 85],
    "Temp": [
        170,
        180,
        170,
        180,
        175,
        175,
        175,
        175,
        175,
        175,
        175,
        175,
        182.07,
        167.93,
    ],
    "Block": ["B1"] * 7 + ["B2"] * 7,
    "Yield": [
        80.5,
        81.5,
        82,
        83.5,
        83.9,
        84.3,
        84,
        79.7,
        79.8,
        79.5,
        78.4,
        75.6,
        78.5,
        77,
    ],
}


def _npk() -> Table:
    return Table.de_colunas(_NPK)


def _analisar_npk(coluna_bloco: str | None):
    return analisar_tabela(
        _npk(),
        ["N", "P", "K"],
        ["yield"],
        versao_ensaia="teste",
        coluna_bloco=coluna_bloco,
    ).resultado


def _p(ajuste, termo: str) -> float:
    return next(c.valor_p for c in ajuste.coeficientes if c.termo == termo)


# --- npk -----------------------------------------------------------------------


def test_npk_com_bloco_reproduz_a_analise_classica() -> None:
    ajuste = _analisar_npk("block").ajustes[0]
    assert ajuste.graus_liberdade_residuo == 12
    assert _p(ajuste, "N") == pytest.approx(0.00437, abs=5e-5)
    assert _p(ajuste, "K") == pytest.approx(0.0288, abs=5e-4)
    assert ajuste.r2 == pytest.approx(0.7886, abs=1e-4)


def test_npk_sem_bloco_perde_o_efeito_de_k() -> None:
    ajuste = _analisar_npk(None).ajustes[0]
    assert _p(ajuste, "K") > 0.05  # o ruído dos blocos esconde o potássio


def test_bloco_nao_muda_os_coeficientes_dos_fatores() -> None:
    com = {
        c.termo: c.estimativa for c in _analisar_npk("block").ajustes[0].coeficientes
    }
    sem = {c.termo: c.estimativa for c in _analisar_npk(None).ajustes[0].coeficientes}
    assert com.keys() == sem.keys()  # nenhuma coluna de bloco nos coeficientes
    for termo in com:
        assert com[termo] == pytest.approx(sem[termo], abs=1e-10)


def test_anova_tem_linha_de_blocos_e_fecha_o_total() -> None:
    reg = _analisar_npk("block").ajustes[0].anova_regressao
    assert reg is not None
    fontes = [li.fonte for li in reg.linhas]
    assert fontes[:3] == ["Blocos", "Regressão", "Resíduo"]
    por_fonte = {li.fonte: li for li in reg.linhas}
    assert por_fonte["Blocos"].graus_liberdade == 5
    assert por_fonte["Blocos"].soma_quadrados == pytest.approx(343.295, abs=1e-3)
    assert por_fonte["Blocos"].valor_f is None  # bloco não é testado como fator
    soma = sum(por_fonte[f].soma_quadrados for f in ("Blocos", "Regressão", "Resíduo"))
    assert soma == pytest.approx(por_fonte["Total"].soma_quadrados, rel=1e-10)
    assert por_fonte["Regressão"].graus_liberdade == 6


def test_efeitos_de_bloco_somam_zero_e_vao_no_contrato() -> None:
    resultado = _analisar_npk("block")
    efeitos = resultado.ajustes[0].efeitos_bloco
    assert list(efeitos) == ["1", "2", "3", "4", "5", "6"]
    assert sum(efeitos.values()) == pytest.approx(0.0, abs=1e-10)
    assert resultado.planejamento is not None
    assert resultado.planejamento.coluna_bloco == "block"
    assert resultado.planejamento.n_blocos == 6


def test_sem_replica_no_mesmo_bloco_falta_de_ajuste_nao_se_aplica() -> None:
    # Cada combinação aparece uma vez por bloco: as réplicas estão em blocos
    # diferentes e não são erro puro.
    falta = _analisar_npk("block").ajustes[0].falta_de_ajuste
    assert not falta.aplicavel


def test_interacao_tripla_confundida_com_os_blocos_e_detectada() -> None:
    tabela = _npk()
    fatores = {n: [float(v) for v in tabela.coluna(n)] for n in "NPK"}
    planejamento = identificar_planejamento(fatores).planejamento
    termos = ["Intercepto", "N", "P", "K", "N:P:K"]
    matriz = com_blocos(
        matriz_modelo(tabela, planejamento, termos), ler_blocos(tabela, "block")
    )
    assert termos_redundantes(matriz) == ["N:P:K"]


def test_oraculo_statsmodels_npk() -> None:
    smf = pytest.importorskip("statsmodels.formula.api")
    pd = pytest.importorskip("pandas")
    dados = pd.DataFrame(_NPK)
    for fator in "NPK":
        dados[fator] = 2 * dados[fator] - 1  # codificado ±1, como o EnsaIA
    oraculo = smf.ols(
        "Q('yield') ~ C(block, Sum) + N + P + K + N:P + N:K + P:K", data=dados
    ).fit()
    ajuste = _analisar_npk("block").ajustes[0]
    for c in ajuste.coeficientes:
        nome = "Intercept" if c.termo == "Intercepto" else c.termo
        assert c.estimativa == pytest.approx(oraculo.params[nome], abs=1e-9)
        assert c.erro_padrao == pytest.approx(oraculo.bse[nome], rel=1e-9)
        assert c.valor_p == pytest.approx(oraculo.pvalues[nome], rel=1e-7)
    assert ajuste.r2 == pytest.approx(oraculo.rsquared, rel=1e-10)


# --- ChemReact -----------------------------------------------------------------


def _chemreact(coluna_bloco: str | None):
    return analisar_tabela(
        Table.de_colunas(_CHEMREACT),
        ["Time", "Temp"],
        ["Yield"],
        versao_ensaia="teste",
        coluna_bloco=coluna_bloco,
    ).resultado.ajustes[0]


def test_chemreact_com_bloco_reproduz_o_publicado() -> None:
    ajuste = _chemreact("Block")
    assert ajuste.r2 == pytest.approx(0.9981, abs=1e-4)
    pe = ajuste.ponto_estacionario
    assert pe is not None and pe.natureza == "maximo"
    assert pe.real["Time"] == pytest.approx(86.86, abs=0.01)
    assert pe.real["Temp"] == pytest.approx(176.67, abs=0.01)


def test_chemreact_erro_puro_dentro_dos_blocos() -> None:
    # 3 pontos centrais em cada bloco: 2 + 2 = 4 gl de erro puro (sem bloco
    # seriam 5, misturando a diferença entre blocos com o erro).
    assert _chemreact("Block").falta_de_ajuste.graus_liberdade_erro_puro == 4
    assert _chemreact(None).falta_de_ajuste.graus_liberdade_erro_puro == 5


def test_oraculo_statsmodels_chemreact() -> None:
    smf = pytest.importorskip("statsmodels.formula.api")
    pd = pytest.importorskip("pandas")
    dados = pd.DataFrame(_CHEMREACT)
    dados["x1"] = (dados["Time"] - 85) / 5  # ±1 = 2º e 4º níveis (80 e 90)
    dados["x2"] = (dados["Temp"] - 175) / 5
    oraculo = smf.ols(
        "Yield ~ C(Block, Sum) + x1 + x2 + I(x1**2) + I(x2**2) + x1:x2", data=dados
    ).fit()
    nomes = {
        "Intercepto": "Intercept",
        "Time": "x1",
        "Temp": "x2",
        "Time^2": "I(x1 ** 2)",
        "Temp^2": "I(x2 ** 2)",
        "Time:Temp": "x1:x2",
    }
    for c in _chemreact("Block").coeficientes:
        assert c.estimativa == pytest.approx(oraculo.params[nomes[c.termo]], abs=1e-6)
        assert c.erro_padrao == pytest.approx(oraculo.bse[nomes[c.termo]], rel=1e-6)


# --- leitura, sugestão e catálogo ----------------------------------------------


def test_ler_blocos_recusa_colunas_que_nao_sao_bloco() -> None:
    tabela = Table.de_colunas({"b": [1, 1, 1, 1], "c": [1, 2, 3, 4], "y": [1, 2, 3, 4]})
    with pytest.raises(ValueError, match="único bloco"):
        ler_blocos(tabela, "b")
    with pytest.raises(ValueError, match="numeração dos ensaios"):
        ler_blocos(tabela, "c")


def test_bloco_nao_pode_ser_tambem_fator() -> None:
    with pytest.raises(ValueError, match="bloco e fator"):
        analisar_tabela(
            _npk(),
            ["N", "P", "block"],
            ["yield"],
            versao_ensaia="teste",
            coluna_bloco="block",
        )


def test_sugestao_reconhece_bloco_e_indice() -> None:
    papeis = sugerir_mapeamento(_npk())
    assert papeis["rownames"] == "ignorar"  # índice, não fator
    assert papeis["block"] == "bloco"
    assert papeis["yield"] == "resposta"
    assert [c for c, p in papeis.items() if p == "fator"] == ["N", "P", "K"]


def test_catalogo_falta_de_ajuste_exige_replica_no_mesmo_bloco() -> None:
    tabela = _npk()
    fatores = {n: [float(v) for v in tabela.coluna(n)] for n in "NPK"}
    sem = disponibilidade(fatores, n_respostas=1, tem_ordem=False)
    com = disponibilidade(
        fatores,
        n_respostas=1,
        tem_ordem=False,
        blocos=list(ler_blocos(tabela, "block").rotulos),
    )
    assert sem["C4"] is None  # há réplicas (em blocos diferentes)
    assert com["C4"] is not None and "mesmo bloco" in com["C4"]
