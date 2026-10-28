"""Conferência de números: número rotulado e falsa aceitação por acaso.

Reprodução de 28/10/2026 com o exemplo do metronidazol (MAZLOOMI, S. et al.
Scientific Reports, v. 13, art. 14654, 2023, CC BY 4.0), que saiu dos exemplos
da tela com o escopo só DCCR e fica aqui como fixture. R² de predição real:
0,786.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import pytest

from ensaia.ai.fidelity import valores_do_resultado, verificar_secao, verificar_texto
from ensaia.ai.report import gerar_relatorio
from ensaia.core.fluxo import analisar_tabela
from ensaia.core.results import AnalysisResult, TipoModelo
from ensaia.core.table import Table
from ensaia.exemplos import carregar_exemplo
from ensaia.io.readers import ler_dados_de_bytes

_METRONIDAZOL = (
    Path(__file__).parents[1] / "fixtures" / "mazloomi_2023_metronidazol.csv"
)


def _analisar(
    tabela: Table, n_respostas: int, tipo_modelo: TipoModelo | None = None
) -> AnalysisResult:
    colunas = list(tabela.colunas)
    fatores, respostas = colunas[:-n_respostas], colunas[-n_respostas:]
    return analisar_tabela(
        tabela,
        fatores,
        respostas,
        versao_ensaia="t",
        tipo_modelo=tipo_modelo,
        objetivos={r: "maximizar" for r in respostas},
    ).resultado


@cache
def _metronidazol() -> AnalysisResult:
    tabela = ler_dados_de_bytes(_METRONIDAZOL.read_bytes(), _METRONIDAZOL.name)
    return _analisar(tabela, 1, tipo_modelo="quadratico")


@cache
def _exemplo(nome: str) -> AnalysisResult:
    tabela, _ = carregar_exemplo(nome)
    return _analisar(tabela, 3 if nome == "acai" else 1)


def test_fixture_reproduz_o_r2_de_predicao_do_relato() -> None:
    assert _metronidazol().ajustes[0].r2_predicao == pytest.approx(0.786, abs=5e-4)


@pytest.mark.parametrize(
    "valor", ["0,91", "0,93", "0,95", "0,94", "0,88", "0,99", "0,97", "0,83"]
)
def test_r2_de_predicao_inventado_nao_confere(valor: str) -> None:
    texto = f"O R² de predição foi de {valor}."
    fid = verificar_texto(texto, _metronidazol())
    (falso,) = fid.nao_rastreaveis
    assert texto[falso.inicio : falso.fim] == valor
    assert not fid.fiel


@pytest.mark.parametrize(
    "texto",
    [
        "O R² de predição foi de 0,786.",
        "O R² de predição foi de cerca de 0,79.",
        "O R² predito (78,6%) ficou abaixo do R².",
    ],
)
def test_r2_de_predicao_real_confere(texto: str) -> None:
    assert verificar_texto(texto, _metronidazol()).fiel


@pytest.mark.parametrize(
    ("texto", "fiel"),
    [
        ("O R² foi de 0,985 e o R² ajustado foi de 0,959.", True),
        # Os mesmos números trocados de rótulo: cada um existe, mas não ali.
        ("O R² foi de 0,959.", False),
        ("O R² ajustado foi de 0,985.", False),
        # Lista depois de dois rótulos: o rótulo pode ser do vizinho.
        ("O R² e o R² ajustado de 0,985 e 0,959, respectivamente.", True),
        ("O modelo explicou 98,5% da variação.", True),
        ("O modelo explicou 93% da variação.", False),
    ],
)
def test_numero_rotulado_so_confere_com_a_sua_estatistica(
    texto: str, fiel: bool
) -> None:
    assert verificar_texto(texto, _metronidazol()).fiel is fiel


@pytest.mark.parametrize(
    "texto",
    [
        # 37,27 é o F da regressão: existe no resultado, mas não é p-valor nem W.
        "A regressão teve p = 37,27.",
        "O teste de Shapiro-Wilk deu W = 37,27.",
        "A desejabilidade global foi de 37,27.",
    ],
)
def test_valor_de_outra_estatistica_nao_passa_pelo_rotulo(texto: str) -> None:
    assert not verificar_texto(texto, _metronidazol()).fiel


def test_vetores_por_ensaio_ficam_fora_dos_permitidos() -> None:
    # Um valor marcado em todo vetor por ensaio não pode virar número permitido.
    # (O valor real não serve: o predito no centro é o próprio intercepto.)
    resultado = _metronidazol()
    ajuste = resultado.ajustes[0]
    assert ajuste.diagnostico is not None
    marca = 123.456789
    vetores = [
        "observados",
        "preditos",
        "residuos",
        "alavancagem",
        "residuos_studentizados",
        "distancia_cook",
    ]
    n = len(ajuste.diagnostico.residuos)
    diagnostico = ajuste.diagnostico.model_copy(
        update=dict.fromkeys(vetores, [marca] * n)
    )
    marcado = resultado.model_copy(
        update={"ajustes": [ajuste.model_copy(update={"diagnostico": diagnostico})]}
    )
    assert marca not in valores_do_resultado(marcado).todos


@pytest.mark.parametrize("nome", ["metronidazol", "tylosin", "acai"])
def test_texto_m0_confere_todos_os_numeros(nome: str) -> None:
    resultado = _metronidazol() if nome == "metronidazol" else _exemplo(nome)
    fid = gerar_relatorio(resultado, modo="m0").fidelidade
    assert fid is not None and fid.total > 0
    assert fid.rastreaveis == fid.total


def test_portao_da_ia_tambem_confere_pelo_rotulo() -> None:
    fatos = [
        "O modelo explica 95,0% da variação (R² = 0,950; R² ajustado = 0,930).",
        "O R² de predição é 0,786.",
    ]
    assert verificar_secao("O R² de predição foi de 0,79.", fatos).fiel
    v = verificar_secao("O R² de predição foi de 0,93.", fatos)
    assert not v.fiel and v.numeros_sem_correspondencia == pytest.approx([0.93])
