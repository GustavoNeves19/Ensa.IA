"""PDF completo da spec §13: seções por análise marcada, matriz e gráficos."""

from __future__ import annotations

import re

import pytest

from ensaia.ai.report import gerar_relatorio
from ensaia.core.descritiva import matriz_ensaios
from ensaia.core.pipeline import analisar, fatores_do_contrato
from ensaia.core.results import AnalysisResult
from ensaia.core.termos import escolher_termos
from ensaia.report import gerar_pdf
from ensaia.report.charts import grafico_diagnostico, numero_curto
from ensaia.report.pdf import numero_sig

_PNG = bytes.fromhex("89504e470d0a1a0a")


def _exemplo(analises: list[str] | None = None):
    # Sem exemplo DCCR curado ainda (ver ensaia/exemplos/__init__.py), reusa o
    # DCCR k=2 sintético já usado nos testes do núcleo (test_modelo_opcoes).
    from tests.unit.test_modelo_opcoes import _dccr

    tabela, plan = _dccr()
    res = analisar(
        tabela,
        plan,
        escolher_termos(tabela, plan).termos,
        ["y"],
        versao_ensaia="t",
        objetivos={"y": "maximizar"},
        analises=analises,
    )
    return res, matriz_ensaios(tabela, plan, res.respostas, "dccr.csv"), plan


def _paginas(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page(?!s)", pdf))


def _pdf(res: AnalysisResult, dados=None) -> bytes:
    return gerar_pdf(res, gerar_relatorio(res, modo="m0"), dados=dados)


def test_pdf_completo_com_matriz_tem_todas_as_secoes() -> None:
    res, dados, _ = _exemplo()
    pdf = _pdf(res, dados)
    assert pdf[:5] == b"%PDF-"
    assert _paginas(pdf) >= 6


def test_so_as_analises_marcadas_entram() -> None:
    completo, dados, _ = _exemplo()
    so_modelo, _, _ = _exemplo(analises=["C1"])
    assert _paginas(_pdf(so_modelo, dados)) < _paginas(_pdf(completo, dados))


def test_fatores_voltam_do_contrato_com_a_mesma_codificacao() -> None:
    res, _, plan = _exemplo()
    assert res.planejamento is not None
    for original, refeito in zip(
        plan.fatores, fatores_do_contrato(res.planejamento), strict=True
    ):
        assert refeito.nome == original.nome
        assert refeito.minimo == pytest.approx(original.minimo)
        assert refeito.maximo == pytest.approx(original.maximo)


def test_matriz_dos_ensaios_tem_real_codificado_e_respostas() -> None:
    _, dados, plan = _exemplo()
    assert dados.n_ensaios == 13
    assert set(dados.codificada) == set(dados.real)
    limite = plan.alfa_axial or 1.0  # DCCR: a estrela vai até ±α, não só ±1
    assert all(
        abs(v) <= limite + 1e-9 for col in dados.codificada.values() for v in col
    )
    assert dados.nome_arquivo is not None and dados.nome_arquivo.endswith(".csv")


def test_painel_de_diagnostico_so_com_os_graficos_pedidos() -> None:
    res, _, _ = _exemplo()
    ajuste = res.ajustes[0]
    assert grafico_diagnostico(ajuste, ["D2"])[:8] == _PNG
    # Sem ordem de execução no contrato, o D3 sozinho não tem o que desenhar.
    assert grafico_diagnostico(ajuste, ["D3"]) is None


@pytest.mark.parametrize(
    ("valor", "texto"),
    [
        (92.933, "92,93"),
        (0.001234, "0,001234"),
        (1234.6, "1235"),
        (-8.4167, "-8,417"),
        (1.5e-7, "1,500e-07"),
        (0.0, "0"),
    ],
)
def test_numero_com_quatro_algarismos_significativos(valor: float, texto: str) -> None:
    assert numero_sig(valor) == texto


def test_rotulo_de_eixo_curto_e_com_virgula() -> None:
    assert numero_curto(0.625) == "0,625"
    assert numero_curto(37.5) == "37,5"
