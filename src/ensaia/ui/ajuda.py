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


# chave → fórmula, para o modo "Dicas em fórmula". Mesma notação em todas:
# n = ensaios, p = parâmetros do modelo (com o intercepto), e = resíduo.
FORMULAS: dict[str, str] = {
    "r2": "R² = 1 − SQres / SQtotal",
    "r2_ajustado": "R²aj = 1 − (1 − R²) · (n − 1) / (n − p)",
    "r2_predicao": "R²pred = 1 − PRESS / SQtotal\nPRESS = Σ [eᵢ / (1 − hᵢᵢ)]²",
    "regressao": "F = MQreg / MQres\n   = [SQreg / (p − 1)] / [SQres / (n − p)]",
    "falta_ajuste": (
        "F = MQfaj / MQep\n   = [SQfaj / (m − p)] / [SQep / (n − m)]\n"
        "m = condições distintas"
    ),
    "normalidade": "W = (Σ aᵢ · e₍ᵢ₎)² / Σ (eᵢ − ē)²\ne₍ᵢ₎ = resíduos em ordem",
    "influentes": (
        "Dᵢ = rᵢ² · hᵢᵢ / [p · (1 − hᵢᵢ)]\n"
        "influente: Dᵢ > 1 e hᵢᵢ > 2p / n\noutlier: |tᵢ| > 3"
    ),
    "coeficientes": "b = (XᵀX)⁻¹ Xᵀ y\nt = bⱼ / EP(bⱼ)",
    "pareto": "tⱼ = |bⱼ| / EP(bⱼ)\nsignificativo se tⱼ > t(α/2; gl do resíduo)",
    "efeitos": "Efeito = ȳ(+1) − ȳ(−1) = 2 · b",
    "meio_normal": (
        "s₀ = 1,5 · mediana |cⱼ|\nPSE = 1,5 · mediana { |cⱼ| : |cⱼ| < 2,5 · s₀ }\n"
        "ME = t(0,975; m/3) · PSE"
    ),
    "efeitos_principais": "ȳ(nível) = média de y nos ensaios com o fator nesse nível",
    "interacao": "Efeito AB = [ȳ(++) − ȳ(−+) − ȳ(+−) + ȳ(−−)] / 2",
    "equacao": (
        "ŷ = b₀ + Σ bᵢxᵢ + Σ bᵢⱼxᵢxⱼ + Σ bᵢᵢxᵢ²\nxᵢ = (Xᵢ − centroᵢ) / meia-amplitudeᵢ"
    ),
    "anova": "F = MQreg / MQres,  com MQ = SQ / gl",
    "anova_tipo2": "F(termo) = [SQ(termo | demais termos) / gl] / MQres",
    "previsto_observado": "ŷᵢ = xᵢᵀ b  contra  yᵢ;  reta y = x",
    "residuos_previsto": "eᵢ = yᵢ − ŷᵢ  contra  ŷᵢ",
    "residuos_ordem": "eᵢ = yᵢ − ŷᵢ  na ordem de execução",
    "qq": "e₍ᵢ₎  contra  z = Φ⁻¹[(i − 3/8) / (n + 1/4)]",
    "superficie": "ŷ(x₁, x₂), com os demais fatores fixos",
    "desejabilidade": "D = (d₁^w₁ · d₂^w₂ · … · dₘ^wₘ)^(1 / Σwᵢ)\ndᵢ ∈ [0, 1]",
    "descritiva": "ȳ = Σ yᵢ / n\ns = √[Σ (yᵢ − ȳ)² / (n − 1)]\nCV = 100 · s / ȳ",
    "matriz": "x = (X − centro) / meia-amplitude",
}

# Modos de dica escolhidos no seletor da abertura, na ordem do controle.
MODOS_DICA: tuple[tuple[str, str], ...] = (
    ("nenhuma", "Sem Dicas"),
    ("texto", "Dicas em Texto"),
    ("formula", "Dicas em Fórmula"),
)


def _conteudo_dica(texto: str, formula: str | None) -> None:
    """O texto e, quando há, a fórmula: o modo escolhido decide qual aparece."""
    ui.label(texto).classes("ea-dica-txt")
    if formula:
        ui.label(formula).classes("ea-dica-form")


def ajuda(chave: str) -> None:
    """O "o que é?" ao lado de um título: abre a explicação ao clicar."""
    titulo, texto = EXPLICACOES[chave]
    formula = FORMULAS.get(chave)
    with (
        ui.button("o que é?").props("flat dense no-caps").classes("ea-ajuda"),
        ui.menu()
        .props("anchor='bottom left' self='top left'")
        .classes("ea-ajuda-pop" + (" ea-dica-com-formula" if formula else "")),
    ):
        ui.label(titulo).classes("ea-ajuda-titulo")
        with ui.element("div").classes("ea-ajuda-texto"):
            _conteudo_dica(texto, formula)


def dica(texto: str, formula: str | None = None) -> ui.icon:
    """Lâmpada discreta: a explicação aparece ao passar o mouse (ou no foco)."""
    with (
        ui.icon("lightbulb")
        .classes("ea-dica")
        .props(f'tabindex="0" role="img" aria-label="Dica: {escape(texto)}"') as icone,
        ui.tooltip()
        .classes("ea-dica-pop" + (" ea-dica-com-formula" if formula else ""))
        .props('anchor="top middle" self="bottom middle" :offset="[0, 6]"'),
    ):
        _conteudo_dica(texto, formula)
    return icone


def seletor_dicas() -> None:
    """Controle em degraus que escolhe como as dicas aparecem na página.

    O modo vira uma classe no <body> (ea-dicas-nenhuma, -texto ou -formula) e o
    CSS mostra ou esconde as lâmpadas, os "o que é?" e o texto ou a fórmula de
    cada dica. Vale só para esta aba do navegador; começa em "Dicas em Texto".
    """
    classes = [f"ea-dicas-{modo}" for modo, _ in MODOS_DICA]
    rotulos = [rotulo for _, rotulo in MODOS_DICA]

    def aplicar(indice: int) -> None:
        ui.query("body").classes(remove=" ".join(classes), add=classes[indice])

    with ui.element("div").classes("ea-seletor-dicas"):
        ui.label("Como mostrar as dicas").classes("ea-seletor-titulo")
        nomes = ", ".join(f"'{r}'" for r in rotulos)
        ui.slider(
            min=0,
            max=len(MODOS_DICA) - 1,
            step=1,
            value=1,
            on_change=lambda e: aplicar(int(e.value)),
        ).props(
            f"markers snap color=primary "
            f':marker-labels="v => [{nomes}][v]" '
            f'aria-label="Como mostrar as dicas"'
        ).classes("ea-seletor-slider")
    aplicar(1)


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
