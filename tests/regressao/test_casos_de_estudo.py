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

from lyra.validation.runner import listar_casos

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

    TODO(#8): implementar junto com o runner.
        resultado = validar_caso(caso)
        assert resultado["erro_coeficientes"].proporcao_dentro_tolerancia == 1.0
        assert resultado["concordancia"].taxa_concordancia >= 0.9
        assert resultado["r2"].dentro_tolerancia
    """
    pytest.skip("Aguardando o runner de validação — issue #8.")
