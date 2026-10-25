"""Fatos verificados do resultado: frases curtas ancoradas em números.
São o texto sem IA (M0) e a única fonte que a IA recebe para escrever.
"""

from __future__ import annotations

from typing import Literal

from ensaia.core.anova import BLOCOS, REGRESSAO
from ensaia.core.design import INTERCEPTO
from ensaia.core.results import NOME_PLANEJAMENTO, AjusteResposta, AnalysisResult

ALFA_PADRAO = 0.05

# Seções do relatório que recebem fatos (a IA faz uma chamada por seção).
Secao = Literal["planejamento", "modelo", "anova", "diagnostico", "otimizacao"]

SECOES: tuple[Secao, ...] = (
    "planejamento",
    "modelo",
    "anova",
    "diagnostico",
    "otimizacao",
)



def fatos_do_ajuste(ajuste: AjusteResposta, *, alfa: float = ALFA_PADRAO) -> list[str]:
    """Fatos de uma resposta: significância, R², regressão e falta de ajuste."""
    fatos: list[str] = []
    fatos.extend(_fatos_significancia(ajuste, alfa))
    fatos.append(_fato_r2(ajuste))
    fatos.append(_fato_falta_ajuste(ajuste, alfa))
    return fatos


def fatos_por_secao(
    resultado: AnalysisResult, *, alfa: float = ALFA_PADRAO
) -> dict[Secao, list[str]]:
    """Fatos do resultado inteiro, agrupados por seção do relatório."""
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
                [
                    _fato_falta_ajuste(ajuste, alfa),
                    *_fatos_normalidade(ajuste, alfa),
                    *_fatos_curvatura(ajuste, alfa),
                    *_fatos_influencia(ajuste),
                ],
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
    """Quais termos são e quais não são significativos."""
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
    """Quanto da variação o modelo explica (R², ajustado e máximo)."""
    fato = (
        f"O modelo explica {_num(ajuste.r2 * 100, 1)}% da variação da resposta "
        f"{ajuste.resposta!r} (R² = {_num(ajuste.r2, 3)}; "
        f"R² ajustado = {_num(ajuste.r2_ajustado, 3)})."
    )
    if ajuste.r2_maximo is not None:
        fato += (
            f" Como há réplicas genuínas, o teto de variação explicável é "
            f"{_num(ajuste.r2_maximo * 100, 1)}% (R² máximo = "
            f"{_num(ajuste.r2_maximo, 3)}) — o erro puro impede qualquer "
            f"modelo de chegar a 100%."
        )
    return fato


def _fatos_termo_erro(ajuste: AjusteResposta) -> list[str]:
    """Avisa quando os testes usaram o erro puro."""
    if ajuste.termo_erro != "erro_puro":
        return []
    return ["Os testes de significância usaram o erro puro como termo de erro."]


def _fatos_regressao(ajuste: AjusteResposta, alfa: float) -> list[str]:
    """F da regressão contra o F tabelado e a regra das 10 vezes."""
    fatos: list[str] = []
    anova = ajuste.anova_regressao
    blocos = (
        next((li for li in anova.linhas if li.fonte == BLOCOS), None)
        if anova is not None
        else None
    )
    if blocos is not None:
        fatos.append(
            f"Os ensaios foram feitos em {blocos.graus_liberdade + 1} blocos; a "
            f"diferença entre eles (SQ = {_num(blocos.soma_quadrados, 2)}) foi "
            "separada do erro antes de testar os fatores."
        )
    if anova is not None and anova.razao_f is not None and anova.f_tabelado:
        regressao = next(li for li in anova.linhas if li.fonte == REGRESSAO)
        assert regressao.valor_f is not None and regressao.valor_p is not None
        if anova.regressao_significativa:
            fatos.append(
                f"A regressão é significativa ({_sig(regressao.valor_p, alfa)}): "
                f"F calculado = {_num(regressao.valor_f, 2)}, F tabelado = "
                f"{_num(anova.f_tabelado, 2)}, razão = {_num(anova.razao_f, 2)}."
            )
            if anova.util_para_previsao:
                fatos.append(
                    "Essa razão é maior que 10: a regressão não é só "
                    "significativa, é útil para previsão."
                )
            elif anova.util_para_previsao is False:
                fatos.append(
                    "Essa razão não chega a 10: a regressão é significativa, "
                    "mas isso não garante que seja útil para previsão."
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
    """Resultado do teste de Shapiro-Wilk dos resíduos."""
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


def _fatos_curvatura(ajuste: AjusteResposta, alfa: float) -> list[str]:
    """Teste de curvatura dos pontos centrais (só em fatorial)."""
    ef = ajuste.efeitos_fatorial
    if ef is None or not ef.curvatura.aplicavel:
        return []
    c = ef.curvatura
    if c.valor_p is None or c.media_central is None or c.media_fatorial is None:
        return []
    medias = (
        f"média no centro = {_num(c.media_central, 3)}; "
        f"média nos vértices = {_num(c.media_fatorial, 3)}"
    )
    if c.significativa:
        return [
            f"Há curvatura significativa ({_sig(c.valor_p, alfa)}; {medias}): o "
            "modelo linear não basta e convém ampliar o planejamento."
        ]
    return [
        f"Não há evidência de curvatura (p = {_num(c.valor_p, 4)} ≥ "
        f"{_num(alfa, 2)}; {medias})."
    ]


def _fatos_influencia(ajuste: AjusteResposta) -> list[str]:
    """Ensaios influentes e possíveis outliers."""
    d = ajuste.diagnostico
    if d is None or not d.alavancagem:
        return []
    fatos: list[str] = []
    if d.ensaios_influentes:
        lista = ", ".join(str(i) for i in d.ensaios_influentes)
        fatos.append(f"O(s) ensaio(s) {lista} tem(têm) influência alta no ajuste.")
    if d.possiveis_outliers:
        lista = ", ".join(str(i) for i in d.possiveis_outliers)
        fatos.append(f"O(s) ensaio(s) {lista} destoa(m) do modelo (possível outlier).")
    return fatos


def _fato_falta_ajuste(ajuste: AjusteResposta, alfa: float) -> str:
    """Resultado do teste de falta de ajuste, ou por que não foi feito."""
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
    """Tipo de planejamento, fatores, respostas, ensaios e blocos."""
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
    """Ponto estacionário e condição ótima de cada resposta."""
    multi = len(resultado.ajustes) > 1
    fatos: list[str] = []
    for ajuste in resultado.ajustes:
        fatos.extend(
            _rotular(_fatos_estacionario(ajuste), ajuste.resposta, multi=multi)
        )

    otimo = resultado.ponto_otimo
    if otimo is None:
        return fatos
    coords = ", ".join(
        f"{fator} = {_num(valor, 3)}" for fator, valor in otimo.coordenadas.items()
    )
    previstas = ", ".join(
        f"{resp} = {_num(valor, 4)}"
        for resp, valor in otimo.resposta_prevista.items()
    )
    fatos += [
        f"A condição ótima (em unidades reais) é {coords}.",
        f"Nessa condição, a resposta prevista é {previstas}.",
    ]
    if otimo.metodo == "desejabilidade":
        fatos.append(
            "A desejabilidade global no ótimo é "
            f"D = {_num(otimo.desejabilidade_global, 3)}."
        )
    return fatos


def _fatos_estacionario(ajuste: AjusteResposta) -> list[str]:
    """Onde fica o ponto estacionário e se é máximo, mínimo ou sela."""
    ponto = ajuste.ponto_estacionario
    if ponto is None:
        return []
    natureza = {
        "maximo": "um máximo",
        "minimo": "um mínimo",
        "sela": "um ponto de sela",
    }
    coords = ", ".join(f"{f} = {_num(v, 3)}" for f, v in ponto.real.items())
    onde = (
        "dentro da região experimental"
        if ponto.dentro_da_regiao
        else "fora da região experimental (não extrapolar o modelo até lá)"
    )
    return [
        f"O ponto estacionário da superfície é {natureza[ponto.natureza]} em "
        f"{coords}, {onde}, com resposta prevista {_num(ponto.resposta_prevista, 4)}."
    ]


def _rotular(fatos: list[str], resposta: str, *, multi: bool) -> list[str]:
    """Põe o nome da resposta na frente dos fatos quando há várias."""
    if not multi:
        return fatos
    return [f"Para a resposta {resposta!r}: {fato}" for fato in fatos]


def _num(valor: float, casas: int) -> str:
    """Número com vírgula decimal e casas fixas."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _sig(p: float, alfa: float) -> str:
    """Texto do p-valor comparado a α (p = 0,0005 < 0,05)."""
    if p < 0.0001:
        return "p < 0,0001"
    return f"p = {_num(p, 4)} < {_num(alfa, 2)}"
