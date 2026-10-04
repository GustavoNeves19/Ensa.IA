"""Testes de arquitetura — travam a fronteira determinístico/LLM.

A tese do TCC depende de uma afirmação estrutural: o LLM narra, mas não
calcula. Comentário em README não sustenta isso — daqui a três meses, no meio
de uma correria de prazo, alguém importa `numpy` dentro de `narrative/` para
"só formatar um percentualzinho" e a garantia evapora sem ninguém perceber.

Estes testes falham o CI quando isso acontece. São a forma executável do
docs/decisoes/0001-fronteira-deterministica-llm.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent / "src" / "ensaia"

# A camada narrativa não pode tocar em ferramenta de cálculo. Se ela precisa
# de um número, o número vem pronto no AnalysisResult. Vale igual para a camada
# `ai/`, que é redatora (ADR 0001/0006): pode falar HTTP (httpx) e montar
# prompts (jinja2), mas não calcula nada.
PROIBIDOS_NA_REDACAO = {"numpy", "pandas", "statsmodels", "scipy", "sklearn"}

# O núcleo não pode depender da camada narrativa, nem de rede, nem de UI.
# Um núcleo que importa `requests` deixou de ser reprodutível offline.
# statsmodels e pandas ficam fora da produção (ADRs 0007 e 0008): ajuste e
# ANOVA são em numpy puro sobre a estrutura `Table`; os dois só são permitidos
# nos testes, como oráculo.
PROIBIDOS_EM_CORE = {
    "ensaia.narrative",
    "ensaia.ui",
    "langchain",
    "langchain_core",
    "langchain_google_genai",
    "openai",
    "google",
    "requests",
    "httpx",
    "streamlit",
    "statsmodels",
    "pandas",
}


def _modulos_importados(caminho: Path) -> set[str]:
    """Todos os módulos importados por um arquivo .py, via AST."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    importados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                importados.add(alias.name)
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            importados.add(no.module)
    return importados


def _arquivos_de(pacote: str) -> list[Path]:
    return sorted((RAIZ / pacote).rglob("*.py"))


def _viola(importado: str, proibidos: set[str]) -> bool:
    """True se `importado` é um dos proibidos ou submódulo de um deles."""
    return any(importado == p or importado.startswith(f"{p}.") for p in proibidos)


@pytest.mark.parametrize(
    "arquivo",
    _arquivos_de("narrative") + _arquivos_de("ai"),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_redacao_nao_calcula(arquivo: Path) -> None:
    """A camada de LLM não importa biblioteca de cálculo numérico."""
    violacoes = {
        imp for imp in _modulos_importados(arquivo) if _viola(imp, PROIBIDOS_NA_REDACAO)
    }
    assert not violacoes, (
        f"{arquivo.relative_to(RAIZ)} importa {sorted(violacoes)}.\n"
        f"A camada de redação não calcula: se o relatório precisa desse número, "
        f"ele deve vir pronto no AnalysisResult. Ver docs/decisoes/0001."
    )


@pytest.mark.parametrize("arquivo", _arquivos_de("core"), ids=lambda p: p.name)
def test_core_nao_depende_de_llm_nem_de_rede(arquivo: Path) -> None:
    """O núcleo determinístico roda offline e não conhece a camada de LLM."""
    violacoes = {
        imp for imp in _modulos_importados(arquivo) if _viola(imp, PROIBIDOS_EM_CORE)
    }
    assert not violacoes, (
        f"{arquivo.relative_to(RAIZ)} importa {sorted(violacoes)}.\n"
        f"O núcleo tem que produzir o mesmo resultado sem internet e sem "
        f"chave de API. Ver docs/decisoes/0001."
    )


def test_analysisresult_e_serializavel() -> None:
    """O contrato da fronteira precisa atravessar JSON sem perder nada.

    Se este teste quebrar, é sinal de que alguém pôs no AnalysisResult um tipo
    que não sobrevive à serialização (um DataFrame, um objeto do statsmodels).
    Isso reabre a porta para a camada narrativa receber capacidade de cálculo
    junto com os dados.
    """
    import json

    from ensaia.core.results import (
        AjusteResposta,
        AnalysisResult,
        Coeficiente,
        FaltaDeAjuste,
        LinhaAnova,
        MetadadosExecucao,
    )

    resultado = AnalysisResult(
        tipo_planejamento="fatorial_completo",
        fatores=["temperatura", "ph"],
        respostas=["rendimento"],
        ajustes=[
            AjusteResposta(
                resposta="rendimento",
                coeficientes=[
                    Coeficiente(
                        termo="Intercepto",
                        estimativa=50.0,
                        erro_padrao=1.0,
                        valor_t=50.0,
                        valor_p=0.0001,
                        significativo=True,
                    )
                ],
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
                r2=0.95,
                r2_ajustado=0.93,
                falta_de_ajuste=FaltaDeAjuste(
                    aplicavel=False,
                    motivo_inaplicavel="Sem repetições genuínas no delineamento.",
                ),
                n_observacoes=8,
                graus_liberdade_residuo=4,
                termos_incluidos=["Intercepto", "temperatura"],
            )
        ],
        metadados=MetadadosExecucao(versao_ensaia="0.1.0"),
    )

    texto = resultado.to_json()
    recarregado = json.loads(texto)

    assert recarregado["fatores"] == ["temperatura", "ph"]
    assert recarregado["ajustes"][0]["r2"] == 0.95
    assert recarregado["ajustes"][0]["falta_de_ajuste"]["aplicavel"] is False
    assert recarregado["metadados"]["alfa"] == 0.05
