"""Testes da camada de relatório PDF.

Não comparam pixels (um PDF não é diff-ável); verificam que a geração roda, que
os gráficos saem como PNG válido, que o PDF é um PDF e que a formatação de
números segue o padrão brasileiro.
"""

from __future__ import annotations

from ensaia.ai.report import gerar_relatorio
from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    Coeficiente,
    FaltaDeAjuste,
    LinhaAnova,
    MetadadosExecucao,
)
from ensaia.report.builder import _fmt_p, gerar_pdf
from ensaia.report.charts import grafico_coeficientes, grafico_pareto
from ensaia.report.pdf import numero_ptbr

_PNG_MAGIC = bytes.fromhex("89504e470d0a1a0a")


def _ajuste(
    resposta: str = "rendimento", *, so_intercepto: bool = False
) -> AjusteResposta:
    coefs = [
        Coeficiente(
            termo="Intercepto",
            estimativa=50.0,
            erro_padrao=1.0,
            valor_t=50.0,
            valor_p=1e-9,
            significativo=True,
            ic_inferior=48.0,
            ic_superior=52.0,
        )
    ]
    if not so_intercepto:
        coefs += [
            Coeficiente(
                termo="temperatura",
                estimativa=5.2,
                erro_padrao=0.3,
                valor_t=17.3,
                valor_p=1e-6,
                significativo=True,
                ic_inferior=4.5,
                ic_superior=5.9,
            ),
            Coeficiente(
                termo="ph",
                estimativa=0.2,
                erro_padrao=0.3,
                valor_t=0.7,
                valor_p=0.51,
                significativo=False,
                ic_inferior=-0.4,
                ic_superior=0.8,
            ),
        ]
    return AjusteResposta(
        resposta=resposta,
        coeficientes=coefs,
        anova=[
            LinhaAnova(
                fonte="temperatura",
                soma_quadrados=100.0,
                graus_liberdade=1,
                quadrado_medio=100.0,
                valor_f=25.0,
                valor_p=0.001,
            )
        ],
        r2=0.962,
        r2_ajustado=0.945,
        falta_de_ajuste=FaltaDeAjuste(
            aplicavel=True, valor_p=0.33, significativa=False
        ),
        n_observacoes=17,
        graus_liberdade_residuo=7,
        termos_incluidos=[c.termo for c in coefs],
    )


def _resultado(ajustes: list[AjusteResposta] | None = None) -> AnalysisResult:
    ajustes = ajustes or [_ajuste()]
    return AnalysisResult(
        tipo_planejamento="composto_central",
        fatores=["temperatura", "ph"],
        respostas=[a.resposta for a in ajustes],
        ajustes=ajustes,
        metadados=MetadadosExecucao(versao_ensaia="0.1.0"),
    )


# --- gráficos -------------------------------------------------------------


def test_graficos_saem_como_png() -> None:
    aj = _ajuste()
    assert grafico_pareto(aj)[:8] == _PNG_MAGIC
    assert grafico_coeficientes(aj)[:8] == _PNG_MAGIC


def test_graficos_sem_efeitos_nao_quebram() -> None:
    aj = _ajuste(so_intercepto=True)
    assert grafico_pareto(aj)[:8] == _PNG_MAGIC
    assert grafico_coeficientes(aj)[:8] == _PNG_MAGIC


# --- PDF ------------------------------------------------------------------


def test_gera_pdf_valido() -> None:
    res = _resultado()
    pdf = gerar_pdf(res, gerar_relatorio(res, modo="m0"), gerado_em="05/10/2026")
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 5000  # tem conteúdo e imagens


def test_grava_em_destino(tmp_path) -> None:
    res = _resultado()
    destino = tmp_path / "relatorio.pdf"
    retorno = gerar_pdf(res, gerar_relatorio(res, modo="m0"), destino=destino)
    assert destino.exists()
    assert destino.read_bytes() == retorno


def test_pdf_com_texto_colado_leva_a_conferencia() -> None:
    from ensaia.ai.report import relatorio_colado

    res = _resultado()
    texto = "O modelo explicou 99,2% da variação.\nNenhum termo foi significativo."
    rel = relatorio_colado(res, texto)
    assert rel.fidelidade is not None and not rel.fidelidade.fiel
    pdf = gerar_pdf(res, rel, gerado_em="10/10/2026")
    assert pdf[:5] == b"%PDF-"


def test_multirresposta_gera_sem_erro() -> None:
    res = _resultado([_ajuste("rendimento"), _ajuste("pureza")])
    pdf = gerar_pdf(res, gerar_relatorio(res, modo="m0"))
    assert pdf[:5] == b"%PDF-"


# --- formatação -----------------------------------------------------------


def test_numero_ptbr_usa_virgula() -> None:
    assert numero_ptbr(0.9712, 3) == "0,971"
    assert numero_ptbr(-3.1, 2) == "-3,10"


def test_fmt_p_abaixo_do_limite() -> None:
    assert _fmt_p(1e-9, 4) == "< 0,0001"
    assert _fmt_p(0.0015, 4) == "0,0015"
