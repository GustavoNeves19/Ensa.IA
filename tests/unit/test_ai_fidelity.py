"""Testes da checagem automática de fidelidade por seção (ai/fidelity)."""

from __future__ import annotations

from ensaia.ai.fidelity import verificar_secao

FATOS = [
    "O termo 'temperatura' é significativo (p = 0,0005 < 0,05).",
    "O modelo explica 95,0% da variação (R² = 0,950).",
]


def test_texto_so_com_numeros_dos_fatos_e_fiel() -> None:
    texto = (
        "A temperatura foi significativa (p = 0,0005) e o modelo explicou "
        "95,0% da variação (R² = 0,950)."
    )
    v = verificar_secao(texto, FATOS)
    assert v.fiel
    assert v.numeros_sem_correspondencia == []


def test_numero_inventado_derruba_a_fidelidade() -> None:
    texto = "O modelo explicou 99,9% da variação."  # 99,9 não está nos fatos
    v = verificar_secao(texto, FATOS)
    assert not v.fiel
    assert 99.9 in v.numeros_sem_correspondencia


def test_arredondamento_dentro_da_tolerancia_passa() -> None:
    # 95% ~ 0,95 do fato "95,0%"/"0,950"; dentro da tolerância relativa.
    texto = "O modelo explicou cerca de 95% da variação."
    assert verificar_secao(texto, FATOS).fiel


def test_texto_sem_numeros_e_fiel() -> None:
    assert verificar_secao("A temperatura teve efeito relevante.", FATOS).fiel


def test_fatos_vazios_qualquer_numero_e_infiel() -> None:
    v = verificar_secao("O valor foi 3,14.", [])
    assert not v.fiel
    assert 3.14 in v.numeros_sem_correspondencia
