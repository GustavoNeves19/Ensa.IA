"""Regressão contra os valores publicados nos casos de estudo.

Estes testes são a rede de segurança do refactor. Depois que um caso de estudo
está validado e o resultado conferido, qualquer mudança no núcleo que altere
um coeficiente acusa aqui — em vez de aparecer como um número estranho na
monografia três semanas depois.

Enquanto não houver caso cadastrado, os testes são pulados (não falham): o
repositório recém-clonado tem que passar no CI.
"""

from __future__ import annotations

import json

import pytest
import yaml

from ensaia.validation.runner import (
    gravar_resultados,
    listar_casos,
    validar_caso,
)

CASOS = listar_casos()

pytestmark = pytest.mark.skipif(
    not CASOS,
    reason=(
        "Nenhum caso de estudo cadastrado. "
        "Ver casos_de_estudo/README.md para adicionar o primeiro."
    ),
)


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.name)
def test_caso_reproduz_valores_publicados(caso) -> None:
    """O EnsaIA reproduz os valores do artigo dentro das tolerâncias do §4.3.

    Os três critérios computáveis sem a desejabilidade — (a) erro relativo dos
    coeficientes, (b) concordância de significância e (c) diferença de R² —
    têm que passar para toda resposta de todo caso cadastrado. O critério (d),
    condição ótima, depende da issue #6 e é verificado à parte como inaplicável.
    """
    resultado = validar_caso(caso)

    referencia = yaml.safe_load((caso / "referencia.yaml").read_text(encoding="utf-8"))
    respostas_ajustadas = {a.resposta for a in resultado["analise"].ajustes}
    assert respostas_ajustadas == set(referencia["respostas"])

    for resposta, metricas in resultado["metricas"].items():
        erro = metricas["erro_coeficientes"]
        r2 = metricas["comparacao_r2"]
        sig = metricas["concordancia_significancia"]

        assert erro.proporcao_dentro_tolerancia == 1.0, (
            f"{caso.name}/{resposta}: coeficientes fora de 5% — "
            f"máx {erro.erro_relativo_maximo_pct}"
        )
        assert r2.dentro_tolerancia, (
            f"{caso.name}/{resposta}: R² fora de 0,01 — Δ={r2.diferenca_r2}"
        )
        assert sig.taxa_concordancia == 1.0, (
            f"{caso.name}/{resposta}: significância divergente — {sig.divergencias}"
        )

    # (d) a condição ótima é comparada com a publicada; a spec (§14.1) não fixa
    # tolerância para ela — a diferença é registrada e discutida na monografia
    # (artigos costumam publicar uma condição arredondada e prática). Aqui se
    # garante que a comparação existe e cobre todos os fatores do artigo.
    condicao = resultado["condicao_otima"]
    if (referencia.get("condicao_otima") or {}).get("objetivos"):
        assert condicao.aplicavel
        publicados = set(referencia["condicao_otima"]["coordenadas"])
        assert {d.fator for d in condicao.diferencas} == publicados
        for d in condicao.diferencas:
            assert d.diferenca_pct_faixa is not None


def test_gravar_resultados_produz_jsons_validos(tmp_path) -> None:
    """A gravação cria os dois JSONs de evidência e eles são relegíveis.

    Usa tmp_path para não depender nem sujar os resultados versionados: o caso
    é copiado para um diretório temporário antes de gravar.
    """
    import shutil

    origem = CASOS[0]
    caso = tmp_path / origem.name
    shutil.copytree(origem, caso)

    resultado = validar_caso(caso)
    arquivos = gravar_resultados(caso, resultado)

    # Os dois JSONs de evidência saem sempre; o relatório M0 sai quando a camada
    # de IA (extra [llm]) está instalada, como no ambiente de desenvolvimento.
    nomes = [a.name for a in arquivos]
    assert "analysis_result.json" in nomes
    assert "metricas_validacao.json" in nomes
    assert "relatorio_m0.md" in nomes

    analise = json.loads(
        (caso / "resultados" / "analysis_result.json").read_text("utf-8")
    )
    assert analise["metadados"]["schema_version"]
    # executado_em fica None por padrão, mantendo o JSON reproduzível.
    assert analise["metadados"]["executado_em"] is None

    metricas = json.loads(
        (caso / "resultados" / "metricas_validacao.json").read_text("utf-8")
    )
    assert metricas["dentro_das_tolerancias"] is True

    relatorio = (caso / "resultados" / "relatorio_m0.md").read_text("utf-8")
    assert "modo M0" in relatorio
    assert "## " in relatorio  # tem seções
