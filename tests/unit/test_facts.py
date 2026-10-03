"""Testes da geração de fatos interpretativos (core/facts)."""

from __future__ import annotations

from ensaia.core.facts import fatos_do_ajuste
from ensaia.core.results import AjusteResposta, Coeficiente, FaltaDeAjuste


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
