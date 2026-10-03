"""Testes das métricas de validação do §4.3.

Estas métricas são o instrumento de medida do TCC. Se elas estiverem erradas,
todo o capítulo de resultados fica errado — e de um jeito difícil de perceber,
porque um número plausível sai mesmo assim. Daí a cobertura pesada aqui,
inclusive dos casos degenerados.
"""

from __future__ import annotations

import pytest

from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    Coeficiente,
    FaltaDeAjuste,
    MetadadosExecucao,
    PontoOtimo,
)
from ensaia.validation.metrics import (
    comparacao_r2,
    concordancia_significancia,
    diferenca_condicao_otima,
    erro_relativo_coeficientes,
)


def _coef(termo: str, estimativa: float, significativo: bool = True) -> Coeficiente:
    return Coeficiente(
        termo=termo,
        estimativa=estimativa,
        erro_padrao=0.1,
        valor_t=10.0,
        valor_p=0.001 if significativo else 0.40,
        significativo=significativo,
    )


def _resultado(
    coeficientes: list[Coeficiente],
    r2: float = 0.95,
    r2_ajustado: float = 0.92,
    ponto_otimo: PontoOtimo | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        tipo_planejamento="composto_central",
        fatores=["temperatura", "ph"],
        respostas=["rendimento"],
        ajustes=[
            AjusteResposta(
                resposta="rendimento",
                coeficientes=coeficientes,
                anova=[],
                r2=r2,
                r2_ajustado=r2_ajustado,
                falta_de_ajuste=FaltaDeAjuste(aplicavel=False),
                n_observacoes=13,
                graus_liberdade_residuo=7,
                termos_incluidos=[c.termo for c in coeficientes],
            )
        ],
        metadados=MetadadosExecucao(versao_ensaia="0.1.0"),
        ponto_otimo=ponto_otimo,
    )


class TestErroRelativoCoeficientes:
    """§4.3(a)"""

    def test_concordancia_perfeita(self) -> None:
        resultado = _resultado([_coef("Intercepto", 50.0), _coef("temperatura", 3.0)])
        r = erro_relativo_coeficientes(
            resultado, "rendimento", {"Intercepto": 50.0, "temperatura": 3.0}
        )
        assert r.erro_relativo_maximo_pct == pytest.approx(0.0)
        assert r.proporcao_dentro_tolerancia == 1.0

    def test_erro_de_4_por_cento_passa_e_de_6_nao(self) -> None:
        resultado = _resultado([_coef("a", 104.0), _coef("b", 106.0)])
        r = erro_relativo_coeficientes(
            resultado, "rendimento", {"a": 100.0, "b": 100.0}
        )
        por_termo = {c.termo: c for c in r.comparacoes}
        assert por_termo["a"].dentro_tolerancia is True
        assert por_termo["b"].dentro_tolerancia is False
        assert r.proporcao_dentro_tolerancia == 0.5

    def test_limiar_de_5_por_cento_e_inclusivo(self) -> None:
        """Exatamente 5% passa — o documento diz "inferiores a 5%" como
        critério de aceitação, e tratamos a fronteira como aceitável."""
        resultado = _resultado([_coef("a", 105.0)])
        r = erro_relativo_coeficientes(resultado, "rendimento", {"a": 100.0})
        assert r.comparacoes[0].erro_relativo_pct == pytest.approx(5.0)
        assert r.comparacoes[0].dentro_tolerancia is True

    def test_referencia_zero_nao_vira_infinito(self) -> None:
        """Artigos reportam coeficiente não significativo como 0. Dividir por
        ele contaminaria a média com inf/NaN."""
        resultado = _resultado([_coef("a", 0.0), _coef("b", 110.0)])
        r = erro_relativo_coeficientes(resultado, "rendimento", {"a": 0.0, "b": 100.0})
        por_termo = {c.termo: c for c in r.comparacoes}
        assert por_termo["a"].erro_relativo_pct is None
        assert por_termo["a"].dentro_tolerancia is True
        # A média ignora o termo indefinido em vez de virar NaN.
        assert r.erro_relativo_medio_pct == pytest.approx(10.0)

    def test_termos_sem_par_sao_reportados_e_nao_entram_na_media(self) -> None:
        resultado = _resultado([_coef("a", 100.0), _coef("extra", 5.0)])
        r = erro_relativo_coeficientes(
            resultado, "rendimento", {"a": 100.0, "ausente": 2.0}
        )
        assert r.termos_ausentes_no_ensaia == ["ausente"]
        assert r.termos_extras_no_ensaia == ["extra"]
        assert r.erro_relativo_medio_pct == pytest.approx(0.0)

    def test_sinal_oposto_conta_como_erro_grande(self) -> None:
        """Coeficiente com sinal trocado é o erro mais grave possível — inverte
        a recomendação prática — e não pode passar despercebido."""
        resultado = _resultado([_coef("a", -3.0)])
        r = erro_relativo_coeficientes(resultado, "rendimento", {"a": 3.0})
        assert r.comparacoes[0].erro_relativo_pct == pytest.approx(200.0)
        assert r.comparacoes[0].dentro_tolerancia is False


class TestConcordanciaSignificancia:
    """§4.3(b)"""

    def test_concordancia_total(self) -> None:
        resultado = _resultado(
            [_coef("a", 1.0, significativo=True), _coef("b", 0.1, significativo=False)]
        )
        r = concordancia_significancia(resultado, "rendimento", {"a": True, "b": False})
        assert r.taxa_concordancia == 1.0
        assert r.divergencias == []

    def test_divergencia_reduz_a_taxa(self) -> None:
        resultado = _resultado(
            [_coef("a", 1.0, significativo=True), _coef("b", 1.0, significativo=True)]
        )
        r = concordancia_significancia(resultado, "rendimento", {"a": True, "b": False})
        assert r.taxa_concordancia == 0.5
        assert len(r.divergencias) == 1

    def test_termo_ausente_conta_como_divergencia(self) -> None:
        """Não pode ser ignorado: ignorar inflaria a taxa artificialmente."""
        resultado = _resultado([_coef("a", 1.0, significativo=True)])
        r = concordancia_significancia(resultado, "rendimento", {"a": True, "b": True})
        assert r.n_total == 2
        assert r.taxa_concordancia == 0.5

    def test_intercepto_fica_fora_da_concordancia(self) -> None:
        """O intercepto não é um efeito de fator e os artigos não o classificam.

        Mesmo presente nos coeficientes do EnsaIA (e ausente da referência, que o
        deixa em branco), ele não pode entrar na taxa nem virar divergência.
        """
        resultado = _resultado(
            [_coef("Intercepto", 50.0, significativo=True), _coef("a", 1.0)]
        )
        r = concordancia_significancia(resultado, "rendimento", {"a": True})
        assert r.n_total == 1
        assert r.taxa_concordancia == 1.0
        assert r.divergencias == []


class TestComparacaoR2:
    """§4.3(c)"""

    def test_dentro_da_tolerancia_de_001(self) -> None:
        resultado = _resultado([_coef("a", 1.0)], r2=0.950, r2_ajustado=0.920)
        r = comparacao_r2(resultado, "rendimento", 0.955, 0.925)
        assert r.diferenca_r2 == pytest.approx(0.005)
        assert r.dentro_tolerancia is True

    def test_fora_da_tolerancia(self) -> None:
        resultado = _resultado([_coef("a", 1.0)], r2=0.90)
        r = comparacao_r2(resultado, "rendimento", 0.95)
        assert r.dentro_tolerancia is False

    def test_r2_ajustado_ausente_na_referencia(self) -> None:
        """Comum: o artigo publica R² e omite o ajustado."""
        resultado = _resultado([_coef("a", 1.0)], r2=0.95)
        r = comparacao_r2(resultado, "rendimento", 0.95, None)
        assert r.diferenca_r2_ajustado is None
        assert r.dentro_tolerancia is True


class TestDiferencaCondicaoOtima:
    """§4.3(d)"""

    def test_diferenca_absoluta_e_percentual_da_faixa(self) -> None:
        otimo = PontoOtimo(
            coordenadas={"temperatura": 62.0},
            resposta_prevista={"rendimento": 88.0},
            desejabilidade_global=0.91,
        )
        resultado = _resultado([_coef("a", 1.0)], ponto_otimo=otimo)
        r = diferenca_condicao_otima(
            resultado, {"temperatura": 60.0}, {"temperatura": (40.0, 80.0)}
        )
        assert r.aplicavel is True
        assert r.diferencas[0].diferenca_absoluta == pytest.approx(2.0)
        assert r.diferencas[0].diferenca_pct_faixa == pytest.approx(5.0)

    def test_sem_ponto_otimo_devolve_inaplicavel_com_motivo(self) -> None:
        resultado = _resultado([_coef("a", 1.0)], ponto_otimo=None)
        r = diferenca_condicao_otima(resultado, {"temperatura": 60.0})
        assert r.aplicavel is False
        assert r.motivo_inaplicavel is not None
