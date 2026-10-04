"""Testes da geração de fatos interpretativos (core/facts)."""

from __future__ import annotations

from ensaia.core.facts import SECOES, fatos_do_ajuste, fatos_por_secao
from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    Coeficiente,
    FaltaDeAjuste,
    MetadadosExecucao,
    PontoOtimo,
)


def _coef(termo: str, p: float, *, sig: bool) -> Coeficiente:
    return Coeficiente(
        termo=termo,
        estimativa=1.0,
        erro_padrao=0.1,
        valor_t=10.0,
        valor_p=p,
        significativo=sig,
    )


def _ajuste(
    coefs: list[Coeficiente],
    *,
    r2: float = 0.97,
    r2_aj: float = 0.95,
    falta: FaltaDeAjuste | None = None,
) -> AjusteResposta:
    return AjusteResposta(
        resposta="rendimento",
        coeficientes=coefs,
        anova=[],
        r2=r2,
        r2_ajustado=r2_aj,
        falta_de_ajuste=falta or FaltaDeAjuste(aplicavel=False),
        n_observacoes=17,
        graus_liberdade_residuo=7,
        termos_incluidos=[c.termo for c in coefs],
    )


def test_fato_de_significancia_em_ptbr() -> None:
    ajuste = _ajuste(
        [
            _coef("Intercepto", 0.0, sig=True),
            _coef("temperatura", 0.0005, sig=True),
            _coef("ph", 0.42, sig=False),
        ]
    )
    fatos = fatos_do_ajuste(ajuste, alfa=0.05)
    assert "O termo 'temperatura' é significativo (p = 0,0005 < 0,05)." in fatos
    assert any("'ph' não é significativo" in f for f in fatos)
    # O intercepto nunca entra como efeito de fator.
    assert not any("Intercepto" in f for f in fatos)


def test_p_muito_pequeno_vira_menor_que() -> None:
    ajuste = _ajuste([_coef("x1", 1e-13, sig=True)])
    fatos = fatos_do_ajuste(ajuste)
    assert "O termo 'x1' é significativo (p < 0,0001)." in fatos


def test_fato_de_r2_em_ptbr() -> None:
    ajuste = _ajuste([_coef("x1", 0.01, sig=True)], r2=0.970, r2_aj=0.932)
    fatos = fatos_do_ajuste(ajuste)
    assert any(
        "explica 97,0% da variação" in f and "R² = 0,970" in f and "0,932" in f
        for f in fatos
    )


def test_falta_de_ajuste_inaplicavel_diz_o_motivo() -> None:
    falta = FaltaDeAjuste(aplicavel=False, motivo_inaplicavel="sem réplicas no centro")
    fatos = fatos_do_ajuste(_ajuste([_coef("x1", 0.01, sig=True)], falta=falta))
    assert any("não pôde ser feito: sem réplicas no centro" in f for f in fatos)


def test_falta_de_ajuste_nao_significativa() -> None:
    falta = FaltaDeAjuste(aplicavel=True, valor_p=0.37, significativa=False)
    fatos = fatos_do_ajuste(_ajuste([_coef("x1", 0.01, sig=True)], falta=falta))
    esperado = "Não há evidência de falta de ajuste (p = 0,3700 ≥ 0,05)"
    assert any(esperado in f for f in fatos)


def test_falta_de_ajuste_significativa_alerta() -> None:
    falta = FaltaDeAjuste(aplicavel=True, valor_p=0.002, significativa=True)
    fatos = fatos_do_ajuste(_ajuste([_coef("x1", 0.01, sig=True)], falta=falta))
    assert any(
        "Há evidência de falta de ajuste" in f and "pode não descrever" in f
        for f in fatos
    )


def test_nenhum_termo_significativo() -> None:
    fatos = fatos_do_ajuste(_ajuste([_coef("x1", 0.9, sig=False)]))
    assert any("Nenhum termo do modelo é significativo" in f for f in fatos)


# --- fatos por seção ------------------------------------------------------


def _resultado(
    ajustes: list[AjusteResposta],
    *,
    tipo: str = "box_behnken",
    fatores: list[str] | None = None,
    respostas: list[str] | None = None,
    ponto_otimo: PontoOtimo | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        tipo_planejamento=tipo,  # type: ignore[arg-type]
        fatores=fatores or ["temperatura", "ph"],
        respostas=respostas or [a.resposta for a in ajustes],
        ajustes=ajustes,
        metadados=MetadadosExecucao(versao_ensaia="0.1.0"),
        ponto_otimo=ponto_otimo,
    )


def test_por_secao_tem_todas_as_chaves() -> None:
    resultado = _resultado([_ajuste([_coef("x1", 0.01, sig=True)])])
    por_secao = fatos_por_secao(resultado)
    assert tuple(por_secao.keys()) == SECOES


def test_secao_planejamento() -> None:
    resultado = _resultado(
        [_ajuste([_coef("x1", 0.01, sig=True)])],
        tipo="box_behnken",
        fatores=["temperatura", "ph", "tempo"],
        respostas=["rendimento"],
    )
    planejamento = fatos_por_secao(resultado)["planejamento"]
    assert any("Box-Behnken" in f and "3 fatores" in f for f in planejamento)
    assert any("1 resposta " in f for f in planejamento)
    assert any("17 ensaios" in f for f in planejamento)


def test_secoes_separam_modelo_anova_diagnostico() -> None:
    falta = FaltaDeAjuste(aplicavel=True, valor_p=0.37, significativa=False)
    ajuste = _ajuste(
        [_coef("temperatura", 0.0005, sig=True)], r2=0.97, r2_aj=0.95, falta=falta
    )
    por_secao = fatos_por_secao(_resultado([ajuste]))

    diagnostico = por_secao["diagnostico"]
    assert any("'temperatura' é significativo" in f for f in por_secao["modelo"])
    assert any("explica 97,0% da variação" in f for f in por_secao["anova"])
    assert any("Não há evidência de falta de ajuste" in f for f in diagnostico)
    # Cada fato numa seção só, sem vazar entre elas.
    assert not any("significativo" in f for f in por_secao["anova"])


def test_otimizacao_vazia_sem_ponto_otimo() -> None:
    resultado = _resultado([_ajuste([_coef("x1", 0.01, sig=True)])])
    assert fatos_por_secao(resultado)["otimizacao"] == []


def test_otimizacao_com_ponto_otimo() -> None:
    otimo = PontoOtimo(
        coordenadas={"temperatura": 1.0, "ph": -0.5},
        resposta_prevista={"rendimento": 92.5},
        desejabilidade_global=0.873,
    )
    resultado = _resultado(
        [_ajuste([_coef("x1", 0.01, sig=True)])], ponto_otimo=otimo
    )
    otimizacao = fatos_por_secao(resultado)["otimizacao"]
    assert any("temperatura = 1,000" in f and "ph = -0,500" in f for f in otimizacao)
    assert any("rendimento = 92,5000" in f for f in otimizacao)
    assert any("D = 0,873" in f for f in otimizacao)


def test_multirresposta_rotula_fatos_por_resposta() -> None:
    a1 = _ajuste([_coef("x1", 0.001, sig=True)])
    a2 = AjusteResposta(
        resposta="pureza",
        coeficientes=[_coef("x1", 0.002, sig=True)],
        anova=[],
        r2=0.90,
        r2_ajustado=0.88,
        falta_de_ajuste=FaltaDeAjuste(aplicavel=False),
        n_observacoes=17,
        graus_liberdade_residuo=7,
        termos_incluidos=["x1"],
    )
    resultado = _resultado([a1, a2], respostas=["rendimento", "pureza"])
    por_secao = fatos_por_secao(resultado)

    assert any("Para a resposta 'rendimento':" in f for f in por_secao["modelo"])
    assert any("Para a resposta 'pureza':" in f for f in por_secao["modelo"])
