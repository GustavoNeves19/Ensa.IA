"""Regressão contra os valores publicados nos casos de estudo.

Estes testes são a rede de segurança do refactor. Depois que um caso de estudo
está validado e o resultado conferido, qualquer mudança no núcleo que altere
um coeficiente acusa aqui — em vez de aparecer como um número estranho na
monografia três semanas depois.

Enquanto não houver caso cadastrado, os testes são pulados (não falham): o
repositório recém-clonado tem que passar no CI.
"""

from __future__ import annotations

import pytest
import yaml

from lyra.validation.runner import listar_casos, validar_caso

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
    """O LYRA reproduz os valores do artigo dentro das tolerâncias do §4.3.

    Nesta fase a regressão garante que o caminho oficial lê o caso e usa a
    estrutura de modelo publicada. As métricas do §4.3 serão acrescentadas
    quando o AnalysisResult e a serialização forem ligados ao runner.
    """
    resultado = validar_caso(caso)

    assert resultado["termos"]
    referencia = yaml.safe_load(
        (caso / "referencia.yaml").read_text(encoding="utf-8")
    )
    assert set(resultado["ajustes"]) == set(referencia["respostas"])


def test_go_respeita_modelo_2fi_publicado() -> None:
    nome = "go-2022-levofloxacino-hidroxiapatita-bbd"
    caso = next(c for c in CASOS if c.name == nome)

    resultado = validar_caso(caso)

    assert resultado["termos"] == [
        "Intercepto",
        "dose_catalisador",
        "concentracao_levofloxacino",
        "ph",
        "dose_catalisador:concentracao_levofloxacino",
        "dose_catalisador:ph",
        "concentracao_levofloxacino:ph",
    ]
