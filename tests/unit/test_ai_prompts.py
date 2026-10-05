"""Testes da montagem de prompts da camada de IA.

Tudo offline: só verifica o texto montado, sem chamar modelo nenhum.
"""

from __future__ import annotations

import pytest

from ensaia.ai.prompts import (
    _CONFIG,
    MAX_PALAVRAS_PADRAO,
    montar_mensagens,
    montar_texto_para_copiar,
)
from ensaia.core.facts import SECOES


def test_todas_as_secoes_tem_prompt() -> None:
    """Nenhuma seção pode ficar sem configuração de prompt."""
    assert set(_CONFIG) == set(SECOES)


@pytest.mark.parametrize("secao", SECOES)
def test_mensagens_tem_estrutura_few_shot(secao: str) -> None:
    fatos = ["Um fato qualquer da seção."]
    mensagens = montar_mensagens(secao, fatos)  # type: ignore[arg-type]

    papeis = [m.papel for m in mensagens]
    assert papeis == ["system", "user", "assistant", "user"]
    # O último turno de usuário carrega os fatos reais.
    assert "Um fato qualquer da seção." in mensagens[-1].conteudo
    # O turno do assistente é o exemplo configurado da seção.
    assert mensagens[2].conteudo == _CONFIG[secao].exemplo.saida  # type: ignore[index]


def test_system_tem_titulo_regras_e_limite() -> None:
    mensagens = montar_mensagens("modelo", ["fato"])
    system = mensagens[0].conteudo

    assert _CONFIG["modelo"].titulo in system
    assert str(MAX_PALAVRAS_PADRAO) in system
    assert "SOMENTE" in system  # a regra de não inventar número
    assert "vírgula decimal" in system


def test_limite_de_palavras_customizado() -> None:
    mensagens = montar_mensagens("anova", ["fato"], max_palavras=60)
    assert "60" in mensagens[0].conteudo
    assert str(MAX_PALAVRAS_PADRAO) not in mensagens[0].conteudo


def test_bloco_de_fatos_lista_cada_fato() -> None:
    fatos = ["Primeiro fato.", "Segundo fato."]
    conteudo = montar_mensagens("planejamento", fatos)[-1].conteudo
    assert "- Primeiro fato." in conteudo
    assert "- Segundo fato." in conteudo
    assert conteudo.startswith("FATOS:")


def test_fatos_vazios_nao_quebram() -> None:
    conteudo = montar_mensagens("otimizacao", [])[-1].conteudo
    assert "sem fatos nesta seção" in conteudo


def test_texto_para_copiar_tem_instrucao_exemplo_e_fatos() -> None:
    fatos = ["Fato real da análise."]
    texto = montar_texto_para_copiar("diagnostico", fatos)

    assert _CONFIG["diagnostico"].titulo in texto  # instruções
    assert _CONFIG["diagnostico"].exemplo.saida in texto  # exemplo resolvido
    assert "Fato real da análise." in texto  # fatos reais
    assert "Entrada:" in texto and "Saída:" in texto


def test_exemplos_seguem_a_regra_da_virgula_decimal() -> None:
    """Os few-shot não podem ensinar ponto decimal (contrariariam a regra 3)."""
    for cfg in _CONFIG.values():
        # Não deve haver dígito-ponto-dígito (ex.: "0.95") na saída de exemplo.
        import re

        assert not re.search(r"\d\.\d", cfg.exemplo.saida), cfg.titulo
