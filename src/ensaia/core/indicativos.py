"""Indicativos iniciais e próximos passos (US-06 e US-17): a primeira leitura.

Antes de mergulhar em tabelas e gráficos, o usuário iniciante quer saber: o
modelo explica a resposta? Dá para confiar nele? O que eu faço agora?

Nada aqui cria limiar novo. Cada sinal de "atenção" é uma decisão que o núcleo
já tomou ao nível α escolhido (regressão significativa, falta de ajuste,
normalidade dos resíduos, ensaios influentes) ou um fato matemático (R² de
predição negativo: o modelo prevê pior que a média). Os próximos passos seguem
as regras da própria especificação (§11.4): deslocar a região quando o ótimo
ou o ponto estacionário caem fora ou na borda, subir a ordem do modelo quando
há falta de ajuste ou curvatura, e sempre confirmar com um ensaio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ensaia.core.design import nome_legivel
from ensaia.core.results import AjusteResposta, AnalysisResult

Situacao = Literal["ok", "atencao", "info"]

# Folga para dizer que uma coordenada codificada "está na borda" da região.
_NA_BORDA = 0.02


@dataclass(frozen=True)
class Indicativo:
    """Um sinal da primeira leitura: o que é, quanto deu e se pede atenção."""

    chave: str  # identificador estável (ajuda contextual na tela)
    analise: str  # ID do catálogo que o produz (só aparece se marcado)
    rotulo: str
    valor: str
    situacao: Situacao
    leitura: str


def indicativos(ajuste: AjusteResposta, alfa: float) -> list[Indicativo]:
    """Os indicadores principais de uma resposta, com o sinal de cada um."""
    itens = [
        Indicativo(
            "r2",
            "C3",
            "R²",
            _num(ajuste.r2, 3),
            "info",
            f"O modelo explica {_num(ajuste.r2 * 100, 1)}% da variação da resposta.",
        ),
        Indicativo(
            "r2_ajustado",
            "C3",
            "R² ajustado",
            _num(ajuste.r2_ajustado, 3),
            "info",
            "O R² descontado pelo número de termos do modelo.",
        ),
    ]
    if ajuste.r2_predicao is not None:
        negativo = ajuste.r2_predicao < 0
        itens.append(
            Indicativo(
                "r2_predicao",
                "C3",
                "R² de predição",
                _num(ajuste.r2_predicao, 3),
                "atencao" if negativo else "info",
                "Negativo: o modelo prevê ensaios novos pior que a simples média."
                if negativo
                else "Quanto o modelo acerta ensaios que ele não viu.",
            )
        )
    reg = ajuste.anova_regressao
    if reg is not None and reg.regressao_significativa is not None:
        linha = next((li for li in reg.linhas if li.valor_p is not None), None)
        valor = (
            f"p = {_p(linha.valor_p)}" if linha and linha.valor_p is not None else "—"
        )
        itens.append(
            Indicativo(
                "regressao",
                "C2",
                "Regressão",
                valor,
                "ok" if reg.regressao_significativa else "atencao",
                f"Significativa ao nível de {_num(alfa, 2)}: o modelo explica a "
                "resposta."
                if reg.regressao_significativa
                else "Não significativa: o modelo não explica a resposta melhor que o "
                "acaso.",
            )
        )
    falta = ajuste.falta_de_ajuste
    if falta.aplicavel and falta.valor_p is not None:
        itens.append(
            Indicativo(
                "falta_ajuste",
                "C4",
                "Falta de ajuste",
                f"p = {_p(falta.valor_p)}",
                "atencao" if falta.significativa else "ok",
                "Significativa: o modelo não descreve bem a forma da resposta."
                if falta.significativa
                else "Não significativa: o modelo descreve bem os dados.",
            )
        )
    d = ajuste.diagnostico
    if d is not None and d.shapiro_p is not None:
        itens.append(
            Indicativo(
                "normalidade",
                "D2",
                "Normalidade dos resíduos",
                f"p = {_p(d.shapiro_p)}",
                "atencao" if d.normalidade_rejeitada else "ok",
                "Os resíduos não parecem normais: leia os p-valores com cautela."
                if d.normalidade_rejeitada
                else "Sem evidência contra a normalidade (Shapiro-Wilk).",
            )
        )
    if d is not None and d.alavancagem:
        suspeitos = sorted({*d.ensaios_influentes, *d.possiveis_outliers})
        itens.append(
            Indicativo(
                "influentes",
                "D4",
                "Ensaios influentes",
                ", ".join(map(str, suspeitos)) if suspeitos else "nenhum",
                "atencao" if suspeitos else "ok",
                "Confira esses ensaios no caderno de laboratório."
                if suspeitos
                else "Nenhum ensaio sozinho puxa o modelo.",
            )
        )
    return itens


def proximos_passos(
    resultado: AnalysisResult, *, limite_codificado: float = 1.0
) -> list[str]:
    """Sugestões do que fazer a seguir, a partir do resultado (spec §11.4)."""
    passos: list[str] = []
    for ajuste in resultado.ajustes:
        passos.extend(_passos_do_ajuste(ajuste, len(resultado.ajustes) > 1))
    otimo = resultado.ponto_otimo
    if otimo is not None:
        na_borda = [
            f
            for f, c in otimo.coordenadas_codificadas.items()
            if abs(c) >= limite_codificado - _NA_BORDA
        ]
        if na_borda:
            nomes = ", ".join(map(nome_legivel, na_borda))
            passos.append(
                f"A melhor condição está na borda da região estudada em {nomes}: "
                "vale estender os níveis nessa direção num novo planejamento."
            )
        condicao = "; ".join(
            f"{nome_legivel(f)} = {_num_curto(v)}" for f, v in otimo.coordenadas.items()
        )
        passos.append(
            f"Faça um ensaio de confirmação na melhor condição ({condicao}) e compare "
            "o resultado com a previsão do modelo."
        )
    elif any(a.ponto_estacionario is not None for a in resultado.ajustes):
        passos.append(
            'Use "Encontrar a melhor condição" para ver onde trabalhar e, depois, '
            "confirme com um ensaio."
        )
    return list(dict.fromkeys(passos))


def _passos_do_ajuste(ajuste: AjusteResposta, varias: bool) -> list[str]:
    da = f" ({nome_legivel(ajuste.resposta)})" if varias else ""
    passos: list[str] = []
    reg = ajuste.anova_regressao
    if reg is not None and reg.regressao_significativa is False:
        passos.append(
            f"O modelo não explica a resposta{da}: revise as faixas dos fatores "
            "(talvez estreitas demais) ou inclua outros fatores."
        )
    if ajuste.falta_de_ajuste.significativa:
        passos.append(
            f"Há falta de ajuste{da}: experimente um modelo de ordem maior ou um "
            "planejamento com mais níveis."
        )
    ef = ajuste.efeitos_fatorial
    if ef is not None and ef.curvatura.significativa:
        passos.append(
            f"Há curvatura{da}: amplie o fatorial para um composto central ou um "
            "Box-Behnken, que ajustam um modelo quadrático."
        )
    pe = ajuste.ponto_estacionario
    if pe is not None and (not pe.dentro_da_regiao or pe.natureza == "sela"):
        motivo = (
            "é um ponto de sela" if pe.natureza == "sela" else "fica fora da região"
        )
        passos.append(
            f"O ponto estacionário{da} {motivo}: a melhor resposta está na borda; "
            "desloque a região experimental na direção dela."
        )
    d = ajuste.diagnostico
    if d is not None and (d.ensaios_influentes or d.possiveis_outliers):
        ensaios = ", ".join(
            map(str, sorted({*d.ensaios_influentes, *d.possiveis_outliers}))
        )
        passos.append(
            f"Confira no caderno de laboratório o(s) ensaio(s) {ensaios}{da}: um erro "
            "de execução ou de anotação ali muda o modelo."
        )
    return passos


def _num(valor: float, casas: int) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def _p(valor: float) -> str:
    return "< 0,0001" if valor < 1e-4 else _num(valor, 4)


def _num_curto(valor: float) -> str:
    texto = f"{valor:.4g}"
    return texto.replace(".", ",") if "e" not in texto else _num(valor, 4)
