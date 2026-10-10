"""Opções do modelo: termo de erro, R² de predição, ANOVA da regressão,
equação, escolha de termos e redução backward."""

from __future__ import annotations

import itertools

import numpy as np
import pytest
from scipy import stats

# Importado pelo módulo: uma função `teste_*` importada no topo seria coletada
# pelo pytest como se fosse um teste.
from ensaia.core import anova
from ensaia.core.design import Fator, Planejamento
from ensaia.core.equacao import montar_equacao
from ensaia.core.model import ajustar_ols, matriz_modelo
from ensaia.core.pipeline import analisar
from ensaia.core.surface import prever
from ensaia.core.table import Table
from ensaia.core.termos import escolher_termos, reduzir_backward, termos_do_tipo


def _dccr() -> tuple[Table, Planejamento]:
    """DCCR k = 2 em unidades reais, com 5 pontos centrais e ruído fixo."""
    a = 1.414
    pontos = [*itertools.product([-1, 1], repeat=2), (-a, 0), (a, 0), (0, -a), (0, a)]
    pontos += [(0, 0)] * 5
    ruido = [0.4, -0.3, 0.2, -0.1, 0.5, -0.4, 0.3, -0.2, 0.1, -0.5, 0.2, 0.0, -0.1]
    temp = [60 + 10 * x for x, _ in pontos]
    ph = [7 + 2 * z for _, z in pontos]
    y = [
        80 + 4 * x - 2 * z - 3 * x**2 - 1 * z**2 + 0.8 * x * z + e
        for (x, z), e in zip(pontos, ruido, strict=True)
    ]
    plan = Planejamento(
        tipo="composto_central",
        fatores=[Fator("temp", 50, 70, "°C"), Fator("ph", 5, 9)],
        alfa_axial=a,
    )
    return Table.de_colunas({"temp": temp, "ph": ph, "y": y}), plan


TERMOS = ["Intercepto", "temp", "ph", "temp^2", "ph^2", "temp:ph"]


def _ajuste():
    tabela, plan = _dccr()
    matriz = matriz_modelo(tabela, plan, TERMOS)
    return tabela, plan, ajustar_ols(matriz, tabela.coluna("y"))


# --- termo de erro, R² de predição ----------------------------------------------


def test_erro_puro_so_das_replicas() -> None:
    tabela, _ = _dccr()
    sq, gl = anova.erro_puro(tabela, "y", ["temp", "ph"])
    centrais = np.array(tabela.coluna("y")[-5:])
    assert gl == 4
    assert sq == pytest.approx(float(((centrais - centrais.mean()) ** 2).sum()))


def test_estatisticas_t_com_erro_puro() -> None:
    tabela, _, ajuste = _ajuste()
    sq, gl = anova.erro_puro(tabela, "y", ["temp", "ph"])
    erros, t, p = ajuste.estatisticas_t(sq / gl, gl)
    erros_res, _, _ = ajuste.estatisticas_t()
    razao = np.sqrt((sq / gl) / (ajuste.soma_quadrados_residual / ajuste.gl_residuo))
    assert erros["temp"] == pytest.approx(erros_res["temp"] * razao)
    assert p["temp"] == pytest.approx(2 * stats.t.sf(abs(t["temp"]), gl))


def test_r2_predicao_bate_com_deixar_um_de_fora() -> None:
    tabela, plan, ajuste = _ajuste()
    tabela_x = matriz_modelo(tabela, plan, TERMOS)
    matriz = np.column_stack([tabela_x.coluna(t) for t in TERMOS])
    y = np.asarray(tabela.coluna("y"))
    press = 0.0
    for i in range(len(y)):
        dentro = np.arange(len(y)) != i
        beta, *_ = np.linalg.lstsq(matriz[dentro], y[dentro], rcond=None)
        press += float((y[i] - matriz[i] @ beta) ** 2)
    esperado = 1 - press / float(((y - y.mean()) ** 2).sum())
    assert ajuste.r2_predicao == pytest.approx(esperado)


# --- ANOVA da regressão ---------------------------------------------------------


def test_anova_regressao_fecha_as_somas() -> None:
    tabela, _, ajuste = _ajuste()
    falta = anova.teste_falta_ajuste(tabela, "y", ["temp", "ph"], ajuste)
    tabela_reg = anova.anova_regressao(ajuste, falta, alfa=0.05)
    linhas = {linha.fonte: linha for linha in tabela_reg.linhas}
    assert list(linhas) == [
        "Regressão", "Resíduo", "Falta de ajuste", "Erro puro", "Total"
    ]
    assert linhas["Regressão"].soma_quadrados + linhas["Resíduo"].soma_quadrados == (
        pytest.approx(linhas["Total"].soma_quadrados)
    )
    faj_mais_ep = (
        linhas["Falta de ajuste"].soma_quadrados + linhas["Erro puro"].soma_quadrados
    )
    assert faj_mais_ep == pytest.approx(linhas["Resíduo"].soma_quadrados)
    assert linhas["Regressão"].graus_liberdade == 5
    assert tabela_reg.f_tabelado == pytest.approx(stats.f.ppf(0.95, 5, 7))
    assert tabela_reg.razao_f == pytest.approx(
        linhas["Regressão"].valor_f / tabela_reg.f_tabelado
    )
    assert tabela_reg.regressao_significativa is True


# --- equação ---------------------------------------------------------------------


def test_equacao_real_preve_o_mesmo_que_a_codificada() -> None:
    tabela, plan = _dccr()
    resultado = analisar(tabela, plan, TERMOS, ["y"], versao_ensaia="t")
    ajuste = resultado.ajustes[0]
    eq = ajuste.equacao
    assert eq is not None
    assert eq.variaveis == {"X1": "temp", "X2": "ph"}
    assert eq.codificada.startswith("ŷ = ")
    assert "X1²" in eq.codificada and "X1·X2" in eq.codificada

    rng = np.random.default_rng(3)
    temp, ph = rng.uniform(45, 75, 20), rng.uniform(4, 10, 20)
    codificado = prever(
        ajuste, {"temp": (temp - 60) / 10, "ph": (ph - 7) / 2}
    )
    c = eq.coeficientes_reais
    real = (
        c["Intercepto"] + c["temp"] * temp + c["ph"] * ph + c["temp^2"] * temp**2
        + c["ph^2"] * ph**2 + c["temp:ph"] * temp * ph
    )
    assert real == pytest.approx(codificado)


def test_equacao_so_com_significativos() -> None:
    tabela, plan = _dccr()
    ajuste = analisar(tabela, plan, TERMOS, ["y"], versao_ensaia="t").ajustes[0]
    nao_sig = [c.termo for c in ajuste.coeficientes if not c.significativo]
    eq = montar_equacao(ajuste.coeficientes, plan.fatores)
    if nao_sig:
        assert len(eq.significativos) < len(eq.codificada)


# --- escolha de termos -----------------------------------------------------------


def test_termos_do_tipo() -> None:
    niveis = {"a": 3, "b": 2}
    assert termos_do_tipo(niveis, "linear") == ["Intercepto", "a", "b"]
    assert termos_do_tipo(niveis, "quadratico") == [
        "Intercepto", "a", "b", "a^2", "a:b"  # sem b^2: b tem só 2 níveis
    ]


def test_fracao_tira_interacoes_confundidas_com_aviso() -> None:
    pontos = [(a, b, c, a * b * c) for a, b, c in itertools.product([-1, 1], repeat=3)]
    pontos += [(0, 0, 0, 0)] * 4
    nomes = "abcd"
    tabela = Table.de_colunas(
        {n: [float(p[j]) for p in pontos] for j, n in enumerate(nomes)}
    )
    plan = Planejamento("fatorial_fracionado", [Fator(n, -1, 1) for n in nomes])
    sel = escolher_termos(tabela, plan, tipo_modelo="interacoes")
    assert "a:b" in sel.termos and "c:d" not in sel.termos  # AB = CD
    assert any("confundidos" in a for a in sel.avisos)


def test_rebaixa_quando_faltam_graus_de_liberdade() -> None:
    tabela, plan = _dccr()
    # 4 vértices + 1 ponto central: x1² e x2² viram a mesma coluna e, mesmo
    # sem ela, 5 termos não cabem em 5 ensaios.
    linhas = [0, 1, 2, 3, 8]
    pequena = Table.de_colunas(
        {c: [list(tabela.coluna(c))[i] for i in linhas] for c in tabela.colunas}
    )
    sel = escolher_termos(pequena, plan, tipo_modelo="quadratico")
    assert sel.tipo_modelo != "quadratico"
    assert any("não bastam" in a for a in sel.avisos)


def test_exclusao_do_linear_avisa_hierarquia() -> None:
    tabela, plan = _dccr()
    sel = escolher_termos(tabela, plan, tipo_modelo="quadratico", excluidos=["temp"])
    assert "temp" not in sel.termos
    assert any("não hierárquico" in a for a in sel.avisos)


def test_reducao_backward_tira_so_o_que_nao_importa() -> None:
    tabela, plan = _dccr()
    # ph^2 tem efeito pequeno (−1) e temp:ph (0,8) também; o resto é forte.
    mantidos, descartados = reduzir_backward(
        tabela, plan, TERMOS, tabela.coluna("y"), alfa=0.05
    )
    assert {"Intercepto", "temp", "ph", "temp^2"} <= set(mantidos)
    for termo in descartados:
        assert termo in TERMOS and termo not in mantidos


def test_pipeline_com_erro_puro_e_fallback_sem_replicas() -> None:
    tabela, plan = _dccr()
    r = analisar(tabela, plan, TERMOS, ["y"], versao_ensaia="t", termo_erro="erro_puro")
    assert r.ajustes[0].termo_erro == "erro_puro"
    assert r.ajustes[0].t_critico == pytest.approx(stats.t.ppf(0.975, 4))

    sem_rep = Table.de_colunas({c: list(tabela.coluna(c))[:9] for c in tabela.colunas})
    r2 = analisar(
        sem_rep, plan, TERMOS, ["y"], versao_ensaia="t", termo_erro="erro_puro"
    )
    assert r2.ajustes[0].termo_erro == "residuo"
    assert any("erro puro foi pedido" in a for a in r2.avisos)


def test_fatos_trazem_regressao_r2_predicao_e_normalidade() -> None:
    from ensaia.core.facts import fatos_por_secao

    tabela, plan = _dccr()
    resultado = analisar(tabela, plan, TERMOS, ["y"], versao_ensaia="t")
    fatos = fatos_por_secao(resultado)
    anova_txt = " ".join(fatos["anova"])
    assert "regressão é significativa" in anova_txt and "F tabelado" in anova_txt
    assert "R² de predição" in anova_txt
    assert any("Shapiro-Wilk" in f for f in fatos["diagnostico"])


def test_tipo2_com_termo_de_erro_nulo_nao_divide_por_zero() -> None:
    _, _, ajuste = _ajuste()
    linhas = ajuste.tabela_tipo2(qm_erro=0.0, gl_erro=4)
    termos = [linha for linha in linhas if linha.fonte != "Resíduo"]
    assert all(linha.valor_f is None for linha in termos)
    assert all(linha.valor_p in (0.0, 1.0) for linha in termos)
