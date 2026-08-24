"""Testes da pré-checagem de fidelidade — §4.3(e)."""

from __future__ import annotations

from lyra.core.results import (
    AjusteResposta,
    AnalysisResult,
    Coeficiente,
    FaltaDeAjuste,
    MetadadosExecucao,
)
from lyra.validation.fidelity import (
    prechecar_numeros,
    segmentar_afirmacoes,
)


def _resultado_simples() -> AnalysisResult:
    return AnalysisResult(
        tipo_planejamento="fatorial_completo",
        fatores=["temperatura"],
        respostas=["rendimento"],
        ajustes=[
            AjusteResposta(
                resposta="rendimento",
                coeficientes=[
                    Coeficiente(
                        termo="temperatura",
                        estimativa=3.25,
                        erro_padrao=0.4,
                        valor_t=8.1,
                        valor_p=0.002,
                        significativo=True,
                    )
                ],
                anova=[],
                r2=0.947,
                r2_ajustado=0.921,
                falta_de_ajuste=FaltaDeAjuste(aplicavel=False),
                n_observacoes=8,
                graus_liberdade_residuo=6,
                termos_incluidos=["temperatura"],
            )
        ],
        metadados=MetadadosExecucao(versao_lyra="0.1.0"),
    )


class TestSegmentacao:
    def test_separa_sentencas(self) -> None:
        afirmacoes = segmentar_afirmacoes(
            "O modelo explicou 94,7% da variância. A temperatura foi significativa."
        )
        assert len(afirmacoes) == 2

    def test_extrai_numeros_no_formato_brasileiro(self) -> None:
        afirmacoes = segmentar_afirmacoes("O R² foi de 0,947 no ajuste.")
        assert 0.947 in afirmacoes[0].numeros_citados


class TestPrechecagem:
    def test_numero_presente_no_resultado_e_reconhecido(self) -> None:
        rel = prechecar_numeros("O R² do modelo foi 0,947.", _resultado_simples())
        assert 0.947 in rel.afirmacoes[0].numeros_encontrados_no_resultado

    def test_numero_inventado_e_sinalizado(self) -> None:
        rel = prechecar_numeros("O R² do modelo foi 0,999.", _resultado_simples())
        assert 0.999 in rel.afirmacoes[0].numeros_sem_correspondencia

    def test_nada_sai_classificado_automaticamente(self) -> None:
        """A classificação é humana por definição do §4.3(e). Se a ferramenta
        classificasse sozinha, um LLM estaria avaliando outro LLM e o
        argumento da monografia viraria circular."""
        rel = prechecar_numeros("O R² foi 0,947.", _resultado_simples())
        assert all(a.classificacao == "pendente" for a in rel.afirmacoes)

    def test_fidelidade_global_e_none_ate_classificar_tudo(self) -> None:
        rel = prechecar_numeros(
            "O R² foi 0,947. A temperatura importou.", _resultado_simples()
        )
        assert rel.fidelidade_global is None

        rel.afirmacoes[0].classificacao = "correta"
        assert rel.fidelidade_global is None, "ainda falta classificar uma"

        rel.afirmacoes[1].classificacao = "nao_sustentada"
        assert rel.fidelidade_global == 0.5
