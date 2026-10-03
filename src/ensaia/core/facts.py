"""Fatos interpretativos verificados a partir de um ajuste.

A camada de IA do EnsaIA é redatora, não analista (ADR 0001, spec seção 12): ela
reescreve em prosa fatos que o núcleo já produziu e já são verdadeiros. Este
módulo é quem produz esses fatos — frases curtas, cada uma ancorada num número
do `AjusteResposta`, no padrão brasileiro (vírgula decimal).

São determinísticas e puras: o mesmo ajuste gera sempre os mesmos fatos. É isso
que permite, depois, checar a fidelidade do texto do LLM contra eles (§4.3(e)) —
se o modelo escrever um número que não está aqui, a checagem acusa.

Nada de cálculo estatístico novo acontece aqui: só leitura e redação do que já
foi calculado.
"""

from __future__ import annotations

from ensaia.core.design import INTERCEPTO
from ensaia.core.results import AjusteResposta

ALFA_PADRAO = 0.05


def fatos_do_ajuste(ajuste: AjusteResposta, *, alfa: float = ALFA_PADRAO) -> list[str]:
    """Frases interpretativas sobre o ajuste de uma resposta.

    Cobre significância dos termos, qualidade do modelo (R²) e o teste de falta
    de ajuste. Cada frase é rastreável a um campo do `AjusteResposta`.
    """
    fatos: list[str] = []
    fatos.extend(_fatos_significancia(ajuste, alfa))
    fatos.append(_fato_r2(ajuste))
    fatos.append(_fato_falta_ajuste(ajuste, alfa))
    return fatos


def _fatos_significancia(ajuste: AjusteResposta, alfa: float) -> list[str]:
    efeitos = [c for c in ajuste.coeficientes if c.termo != INTERCEPTO]
    significativos = [c for c in efeitos if c.significativo]
    nao = [c for c in efeitos if not c.significativo]

    fatos = [
        f"O termo {c.termo!r} é significativo ({_sig(c.valor_p, alfa)})."
        for c in significativos
    ]
    if not significativos:
        fatos.append(
            f"Nenhum termo do modelo é significativo ao nível de {_num(alfa, 2)}."
        )
    if nao:
        termos = ", ".join(repr(c.termo) for c in nao)
        verbo = "não é significativo" if len(nao) == 1 else "não são significativos"
        fatos.append(f"{termos} {verbo} ao nível de {_num(alfa, 2)}.")
    return fatos


def _fato_r2(ajuste: AjusteResposta) -> str:
    return (
        f"O modelo explica {_num(ajuste.r2 * 100, 1)}% da variação da resposta "
        f"{ajuste.resposta!r} (R² = {_num(ajuste.r2, 3)}; "
        f"R² ajustado = {_num(ajuste.r2_ajustado, 3)})."
    )


def _fato_falta_ajuste(ajuste: AjusteResposta, alfa: float) -> str:
    falta = ajuste.falta_de_ajuste
    if not falta.aplicavel:
        motivo = falta.motivo_inaplicavel or "não há réplicas genuínas no delineamento"
        return f"O teste de falta de ajuste não pôde ser feito: {motivo.rstrip('.')}."
    # Aplicável: valor_p e significativa estão preenchidos.
    assert falta.valor_p is not None  # garantido quando aplicavel é True
    if falta.significativa:
        return (
            f"Há evidência de falta de ajuste ({_sig(falta.valor_p, alfa)}): "
            f"o modelo pode não descrever bem os dados."
        )
    return (
        f"Não há evidência de falta de ajuste "
        f"(p = {_num(falta.valor_p, 4)} ≥ {_num(alfa, 2)})."
    )


def _num(valor: float, casas: int) -> str:
    """Número no padrão brasileiro (vírgula decimal), com casas fixas."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _sig(p: float, alfa: float) -> str:
    """Parêntese de significância: 'p < 0,0001' ou 'p = 0,0005 < 0,05'.

    Abaixo de 0,0001 evita notação científica e dispensa repetir o α, já que a
    desigualdade com o α fica óbvia.
    """
    if p < 0.0001:
        return "p < 0,0001"
    return f"p = {_num(p, 4)} < {_num(alfa, 2)}"
