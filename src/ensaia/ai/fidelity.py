"""Checagem automática de fidelidade de uma seção (spec §12.5).

É o portão do *fallback*: um parágrafo gerado pelo LLM só pode entrar no
relatório se todo número que ele cita estiver nos FATOS daquela seção. Como os
fatos são a única fonte que o modelo recebeu, um número que não bate com nenhum
deles é candidato a alucinação — e a seção é rejeitada em favor do texto M0.

Diferente de `validation/fidelity.py`, que estrutura a avaliação MANUAL do
§4.3(e) (classificação humana, planilha): aqui é uma decisão automática,
binária, em tempo de execução. As duas compartilham a extração de números de
`core/numeros.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ensaia.core.numeros import numero_rastreavel, numeros_no_texto


@dataclass(frozen=True)
class VerificacaoSecao:
    """Veredito da checagem de uma seção."""

    fiel: bool
    numeros_sem_correspondencia: list[float]


def verificar_secao(
    texto: str,
    fatos: Sequence[str],
    *,
    tolerancia_relativa: float = 0.01,
) -> VerificacaoSecao:
    """Confere se o texto gerado só cita números presentes nos fatos da seção.

    Os números permitidos são os que aparecem nos próprios fatos (que já vieram
    prontos e verificados do núcleo). Qualquer número do texto que não bata com
    nenhum deles, a menos de arredondamento, derruba a fidelidade da seção.
    """
    permitidos = [n for fato in fatos for n in numeros_no_texto(fato)]
    sem_correspondencia = [
        n
        for n in numeros_no_texto(texto)
        if not numero_rastreavel(n, permitidos, tolerancia_relativa=tolerancia_relativa)
    ]
    return VerificacaoSecao(
        fiel=not sem_correspondencia,
        numeros_sem_correspondencia=sem_correspondencia,
    )
