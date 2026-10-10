"""PDF completo da spec §13: seções por análise marcada, matriz e gráficos."""

from __future__ import annotations

import re

import pytest

from ensaia.ai.report import gerar_relatorio
from ensaia.core.descritiva import matriz_ensaios
from ensaia.core.identificacao import identificar_planejamento
from ensaia.core.pipeline import analisar, fatores_do_contrato
from ensaia.core.results import AnalysisResult
from ensaia.core.termos import escolher_termos
from ensaia.exemplos import carregar_exemplo
from ensaia.report import gerar_pdf
from ensaia.report.charts import grafico_diagnostico, numero_curto
from ensaia.report.pdf import numero_sig

_PNG = bytes.fromhex("89504e470d0a1a0a")


def _exemplo(analises: list[str] | None = None):
    tabela, nome = carregar_exemplo("metronidazol")
    colunas = list(tabela.colunas)
    fatores, resposta = colunas[:-1], colunas[-1]
    plan = identificar_planejamento(
        {f: [float(v) for v in tabela.coluna(f)] for f in fatores}
    ).planejamento
    res = analisar(
        tabela,
        plan,
        escolher_termos(tabela, plan).termos,
        [resposta],
        versao_ensaia="t",
        objetivos={resposta: "maximizar"},
        analises=analises,
    )
    return res, matriz_ensaios(tabela, plan, res.respostas, nome), plan


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
    _, dados, _ = _exemplo()
    assert dados.n_ensaios == 15
    assert set(dados.codificada) == set(dados.real)
    assert all(abs(v) <= 1.0 + 1e-9 for col in dados.codificada.values() for v in col)
    assert dados.nome_arquivo is not None and dados.nome_arquivo.endswith(".csv")


def test_painel_de_diagnostico_so_com_os_graficos_pedidos() -> None:
    res, _, _ = _exemplo()
    ajuste = res.ajustes[0]
    assert grafico_diagnostico(ajuste, ["D2"])[:8] == _PNG  # type: ignore[index]
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
