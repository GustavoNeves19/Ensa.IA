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

from typing import Literal

from ensaia.core.design import INTERCEPTO
from ensaia.core.results import NOME_PLANEJAMENTO, AjusteResposta, AnalysisResult

ALFA_PADRAO = 0.05

# As seções do relatório que recebem fatos. A camada de IA faz uma chamada por
# seção (spec §12.3), com contexto curto — só os fatos daquela seção. A
# "conclusão" da spec NÃO está aqui de propósito: ela é síntese que o LLM
# redige a partir das outras seções, não um fato determinístico novo.
Secao = Literal["planejamento", "modelo", "anova", "diagnostico", "otimizacao"]

SECOES: tuple[Secao, ...] = (
    "planejamento",
    "modelo",
    "anova",
    "diagnostico",
    "otimizacao",
)



def fatos_do_ajuste(ajuste: AjusteResposta, *, alfa: float = ALFA_PADRAO) -> list[str]:
    """Frases interpretativas sobre o ajuste de uma resposta.

    Cobre significância dos termos, qualidade do modelo (R²) e o teste de falta
    de ajuste. Cada frase é rastreável a um campo do `AjusteResposta`.

    É a visão achatada (todos os fatos de uma resposta numa lista só). Para o
    relatório por seção, use `fatos_por_secao`.
    """
    fatos: list[str] = []
    fatos.extend(_fatos_significancia(ajuste, alfa))
    fatos.append(_fato_r2(ajuste))
    fatos.append(_fato_falta_ajuste(ajuste, alfa))
    return fatos


def fatos_por_secao(
    resultado: AnalysisResult, *, alfa: float = ALFA_PADRAO
) -> dict[Secao, list[str]]:
    """Fatos verificados do resultado inteiro, agrupados por seção do relatório.

    Cada seção recebe só os fatos que lhe cabem, para a camada de IA fazer uma
    chamada curta por seção (spec §12.3). Seções sem fato (ex.: otimização sem
    ponto ótimo) vêm com lista vazia — a presença da chave é estável, o conteúdo
    é que varia. Com mais de uma resposta, os fatos por resposta (modelo,
    diagnóstico) são rotulados com o nome dela.
    """
    multi = len(resultado.ajustes) > 1

    modelo: list[str] = []
    anova: list[str] = []
    diagnostico: list[str] = []
    for ajuste in resultado.ajustes:
        modelo.extend(
            _rotular(
                _fatos_significancia(ajuste, alfa) + _fatos_termo_erro(ajuste),
                ajuste.resposta,
                multi=multi,
            )
        )
        # O fato de R² já cita a resposta; não precisa de rótulo extra.
        anova.append(_fato_r2(ajuste))
        anova.extend(
            _rotular(_fatos_regressao(ajuste, alfa), ajuste.resposta, multi=multi)
        )
        diagnostico.extend(
            _rotular(
                [_fato_falta_ajuste(ajuste, alfa), *_fatos_normalidade(ajuste, alfa)],
                ajuste.resposta,
                multi=multi,
            )
        )

    return {
        "planejamento": _fatos_planejamento(resultado),
        "modelo": modelo,
        "anova": anova,
        "diagnostico": diagnostico,
        "otimizacao": _fatos_otimizacao(resultado),
    }


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


def _fatos_termo_erro(ajuste: AjusteResposta) -> list[str]:
    if ajuste.termo_erro != "erro_puro":
        return []
    return ["Os testes de significância usaram o erro puro como termo de erro."]


def _fatos_regressao(ajuste: AjusteResposta, alfa: float) -> list[str]:
    """F da regressão contra o F tabelado (critério da literatura brasileira)."""
    fatos: list[str] = []
    anova = ajuste.anova_regressao
    if anova is not None and anova.razao_f is not None and anova.f_tabelado:
        regressao = anova.linhas[0]
        assert regressao.valor_f is not None and regressao.valor_p is not None
        if anova.regressao_significativa:
            fatos.append(
                f"A regressão é significativa ({_sig(regressao.valor_p, alfa)}): "
                f"F calculado = {_num(regressao.valor_f, 2)}, F tabelado = "
                f"{_num(anova.f_tabelado, 2)}, razão = {_num(anova.razao_f, 2)}."
            )
        else:
            fatos.append(
                f"A regressão não é significativa (p = {_num(regressao.valor_p, 4)} "
                f"≥ {_num(alfa, 2)}): F calculado = {_num(regressao.valor_f, 2)} "
                f"não supera o F tabelado = {_num(anova.f_tabelado, 2)}."
            )
    if ajuste.r2_predicao is not None:
        fatos.append(f"O R² de predição é {_num(ajuste.r2_predicao, 3)}.")
    return fatos


def _fatos_normalidade(ajuste: AjusteResposta, alfa: float) -> list[str]:
    d = ajuste.diagnostico
    if d is None or d.shapiro_p is None or d.shapiro_w is None:
        return []
    teste = f"W = {_num(d.shapiro_w, 3)}; p = {_num(d.shapiro_p, 4)}"
    if d.normalidade_rejeitada:
        return [
            f"O teste de Shapiro-Wilk indica que os resíduos não seguem uma "
            f"distribuição normal ({teste} < {_num(alfa, 2)})."
        ]
    return [
        f"O teste de Shapiro-Wilk não indica desvio da normalidade dos resíduos "
        f"({teste} ≥ {_num(alfa, 2)})."
    ]


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


def _fatos_planejamento(resultado: AnalysisResult) -> list[str]:
    tipo = NOME_PLANEJAMENTO.get(
        resultado.tipo_planejamento, resultado.tipo_planejamento
    )
    n_fatores = len(resultado.fatores)
    fatores = ", ".join(repr(f) for f in resultado.fatores)
    respostas = ", ".join(repr(r) for r in resultado.respostas)
    palavra_fator = "fator" if n_fatores == 1 else "fatores"
    palavra_resp = "resposta" if len(resultado.respostas) == 1 else "respostas"

    fatos = [
        f"O delineamento é um {tipo} com {n_fatores} {palavra_fator} "
        f"({fatores}) e {len(resultado.respostas)} {palavra_resp} ({respostas})."
    ]
    if resultado.ajustes:
        n = resultado.ajustes[0].n_observacoes
        fatos.append(f"A matriz experimental tem {n} ensaios.")
    return fatos


def _fatos_otimizacao(resultado: AnalysisResult) -> list[str]:
    otimo = resultado.ponto_otimo
    if otimo is None:
        return []

    coords = ", ".join(
        f"{fator} = {_num(valor, 3)}" for fator, valor in otimo.coordenadas.items()
    )
    previstas = ", ".join(
        f"{resp} = {_num(valor, 4)}"
        for resp, valor in otimo.resposta_prevista.items()
    )
    d = _num(otimo.desejabilidade_global, 3)
    return [
        f"A condição ótima (em níveis codificados) é {coords}.",
        f"Nessa condição, a resposta prevista é {previstas}.",
        f"A desejabilidade global no ótimo é D = {d}.",
    ]


def _rotular(fatos: list[str], resposta: str, *, multi: bool) -> list[str]:
    """Prefixa cada fato com o nome da resposta quando há mais de uma.

    Com uma resposta só, o relatório inteiro é sobre ela e o rótulo seria ruído.
    Com várias, sem o rótulo não dá para saber a que resposta cada fato pertence.
    """
    if not multi:
        return fatos
    return [f"Para a resposta {resposta!r}: {fato}" for fato in fatos]


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
