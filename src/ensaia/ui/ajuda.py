"""Ajuda dentro da tela (US-16 e US-18): "o que é isto?" e o glossário.

Ao lado de cada indicador, tabela e gráfico, um "o que é?" abre uma explicação
curta: o que é, como ler e por que importa. Para quem está aprendendo
planejamento de experimentos enquanto analisa os próprios dados, a resposta
precisa estar ali, sem sair da página.

O glossário e o guia de leitura são os mesmos textos que o servidor MCP serve
como recursos (`ensaia/conteudo/`): a tela e o assistente de IA ensinam igual.
"""

from __future__ import annotations

from html import escape
from importlib.resources import files

from nicegui import ui

_CONTEUDO = files("ensaia") / "conteudo"

# chave → (título, o que é e como ler). Frases curtas, sem jargão sem tradução.
EXPLICACOES: dict[str, tuple[str, str]] = {
    "r2": (
        "R²",
        "Fração da variação da resposta que o modelo explica, de 0 a 1. Perto de 1 "
        "é bom, mas sozinho engana: todo termo a mais aumenta o R².",
    ),
    "r2_ajustado": (
        "R² ajustado",
        "O R² descontado pelo número de termos. Se ele cai muito em relação ao R², "
        "o modelo tem termos demais para a quantidade de ensaios.",
    ),
    "r2_predicao": (
        "R² de predição",
        "Quanto o modelo acerta um ensaio que ele não viu (cada ensaio é previsto "
        "sem ele no ajuste). Muito abaixo do R² ajustado indica um modelo que "
        "decorou os dados; negativo indica que prevê pior que a média.",
    ),
    "regressao": (
        "Regressão (ANOVA)",
        "Testa se o modelo, como um todo, explica a resposta além do acaso. "
        "p menor que α: explica. F calculado / F tabelado maior que 1 diz o mesmo.",
    ),
    "falta_ajuste": (
        "Falta de ajuste",
        "Compara o erro do modelo com o erro puro das réplicas (pontos centrais). "
        "Significativa quer dizer que a forma do modelo não acompanha a resposta. "
        "O desejável é p maior ou igual a α.",
    ),
    "normalidade": (
        "Normalidade dos resíduos",
        "Os testes do modelo supõem resíduos com distribuição normal. O teste de "
        "Shapiro-Wilk com p menor que α indica que não são; aí os p-valores pedem "
        "cautela.",
    ),
    "influentes": (
        "Ensaios influentes",
        "Ensaios que, sozinhos, puxam o modelo (distância de Cook maior que 1 com "
        "alavancagem alta) ou que destoam muito (resíduo studentizado maior que 3). "
        "Vale conferir no caderno se foram executados como planejado.",
    ),
    "coeficientes": (
        "Coeficientes",
        "O peso de cada termo na equação, na escala codificada (−1 a +1). O sinal "
        "diz a direção: positivo aumenta a resposta. O p-valor diz se o termo é "
        "significativo.",
    ),
    "pareto": (
        "Pareto dos efeitos",
        "Os termos ordenados pelo tamanho do efeito padronizado (|t|). Barra que "
        "passa da linha tracejada (t crítico) é efeito significativo. Clique numa "
        "barra para ver a superfície daquele termo.",
    ),
    "efeitos": (
        "Efeitos",
        "Quanto a resposta muda, em média, quando o fator vai do nível baixo (−1) "
        "ao alto (+1). Em fatoriais, é o dobro do coeficiente.",
    ),
    "meio_normal": (
        "Gráfico meio-normal",
        "Para fatoriais sem réplicas: efeitos que são só ruído se alinham perto da "
        "origem; os que se afastam para a direita da margem de Lenth são ativos.",
    ),
    "efeitos_principais": (
        "Efeitos principais",
        "A média da resposta em cada nível de cada fator, na mesma escala. Quanto "
        "mais inclinada a linha, maior o efeito daquele fator.",
    ),
    "interacao": (
        "Interação",
        "Uma linha por nível do segundo fator. Linhas paralelas: os fatores agem "
        "cada um por si. Linhas que se abrem ou se cruzam: o efeito de um depende "
        "do nível do outro.",
    ),
    "equacao": (
        "Equação do modelo",
        "A fórmula que o modelo ajustou. Na forma codificada os coeficientes são "
        "comparáveis entre si; na forma real você usa direto os valores do "
        "laboratório para prever a resposta.",
    ),
    "anova": (
        "ANOVA da regressão",
        "Divide a variação da resposta entre o que o modelo explica (regressão) e o "
        "que sobra (resíduo, que se separa em falta de ajuste e erro puro quando há "
        "réplicas).",
    ),
    "anova_tipo2": (
        "ANOVA por termo (Tipo II)",
        "O teste de cada termo do modelo, descontados os demais. p menor que α: o "
        "termo contribui para explicar a resposta.",
    ),
    "previsto_observado": (
        "Previsto × observado",
        "Cada ponto é um ensaio. Sobre a linha y = x, o modelo acertou; quanto mais "
        "longe da linha, maior o erro naquele ensaio.",
    ),
    "residuos_previsto": (
        "Resíduos × previsto",
        "O erro de cada ensaio contra o valor previsto. Os pontos devem se espalhar "
        "ao acaso em torno do zero; funil, curva ou tendência mostram algo que o "
        "modelo deixou de fora.",
    ),
    "residuos_ordem": (
        "Resíduos × ordem de execução",
        "Os erros na ordem em que os ensaios foram feitos. Subida ou descida aos "
        "poucos indica deriva do equipamento, do reagente ou do operador.",
    ),
    "qq": (
        "Gráfico Q-Q normal",
        "Compara os resíduos com o que se esperaria de uma distribuição normal. "
        "Pontos perto da reta: resíduos normais. Afastamento nas pontas indica "
        "desvio da normalidade.",
    ),
    "superficie": (
        "Superfície de resposta",
        "A resposta prevista pelo modelo em função de dois fatores, com os demais "
        "fixos. Nas curvas de contorno, cada faixa de cor é uma faixa de valores; "
        "mais escuro, maior a resposta.",
    ),
    "desejabilidade": (
        "Desejabilidade",
        "Uma nota de 0 a 1 de quanto uma condição atende à meta de cada resposta "
        "(maximizar, minimizar ou atingir um alvo). Com várias respostas, a "
        "desejabilidade global D combina todas.",
    ),
    "descritiva": (
        "Estatística descritiva",
        "Um resumo de cada resposta antes de qualquer modelo. O coeficiente de "
        "variação (CV) mostra quanto ela mudou entre os ensaios.",
    ),
    "matriz": (
        "Matriz do planejamento",
        "Os níveis de cada ensaio em unidades reais e, entre parênteses, na escala "
        "codificada (−1, 0, +1) que o modelo usa.",
    ),
}


def ajuda(chave: str) -> None:
    """O "o que é?" ao lado de um título: abre a explicação ao clicar."""
    titulo, texto = EXPLICACOES[chave]
    with (
        ui.button("o que é?").props("flat dense no-caps").classes("ea-ajuda"),
        ui.menu().props("anchor='bottom left' self='top left'").classes("ea-ajuda-pop"),
    ):
        ui.label(titulo).classes("ea-ajuda-titulo")
        ui.label(texto).classes("ea-ajuda-texto")


def dica(texto: str) -> ui.icon:
    """Lâmpada discreta: a explicação aparece ao passar o mouse (ou no foco)."""
    with (
        ui.icon("lightbulb")
        .classes("ea-dica")
        .props(f'tabindex="0" role="img" aria-label="Dica: {escape(texto)}"') as icone
    ):
        ui.tooltip(texto).classes("ea-dica-pop").props(
            'anchor="top middle" self="bottom middle" :offset="[0, 6]"'
        )
    return icone


def titulo_com_ajuda(texto: str, chave: str, classe: str = "ea-grafico-titulo") -> None:
    """Título de tabela ou gráfico com o "o que é?" ao lado."""
    with ui.element("div").classes("ea-titulo-linha"):
        ui.label(texto).classes(classe)
        ajuda(chave)


def botao_glossario() -> None:
    """Abre o glossário e o guia de leitura numa janela, sem sair da página."""
    with ui.dialog() as janela, ui.card().classes("ea-glossario"):
        with ui.tabs().props("no-caps").classes("ea-abas") as abas:
            aba_glossario = ui.tab("Glossário")
            aba_guia = ui.tab("Como ler os resultados")
        with ui.tab_panels(abas, value=aba_glossario).classes(
            "w-full ea-glossario-texto"
        ):
            with ui.tab_panel(aba_glossario):
                ui.markdown(_texto("glossario.md"))
            with ui.tab_panel(aba_guia):
                ui.markdown(_texto("guia-interpretacao.md"))
        ui.button("Fechar", on_click=janela.close).props("flat no-caps").classes(
            "ea-botao-sec"
        )
    ui.button("Glossário e guia de planejamento de experimentos").props(
        "flat dense no-caps"
    ).classes("ea-botao-sec ea-glossario-link").on_click(janela.open)


def _texto(nome: str) -> str:
    return (_CONTEUDO / nome).read_text(encoding="utf-8")
