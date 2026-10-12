"""Escolha das análises (spec §9, passo 4 do fluxo), em etapas e com explicação.

Em vez de uma parede de caixas de seleção, as análises ficam em etapas que
abrem e fecham — dados, triagem, modelo, diagnóstico, otimização —, cada uma
com a pergunta que ela responde. Cada análise é um cartão que diz o que ela mostra;
a lâmpada traz como ler o resultado. Clicar no cartão inclui ou tira a análise
do laudo.

A disponibilidade continua vindo de `core.catalogo.disponibilidade`: o que não
se aplica aos dados fica apagado, com o motivo escrito no próprio cartão.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from nicegui import ui

from ensaia.core.catalogo import CATALOGO, disponibilidade
from ensaia.core.fluxo import Papel
from ensaia.core.table import Table
from ensaia.ui.ajuda import dica


class FonteMapeamento(Protocol):
    """O que o painel precisa do mapeamento de colunas."""

    tabela: Table
    ouvintes: list[Callable[[], None]]

    def colunas(self, papel: Papel) -> list[str]: ...


# Cada etapa: (rótulo curto do passo, pergunta que ela responde, para que serve).
ETAPAS: dict[str, tuple[str, str, str]] = {
    "A": (
        "Dados",
        "O que foi feito no experimento?",
        "Conhecer os dados e o planejamento antes de ajustar qualquer modelo.",
    ),
    "B": (
        "Triagem",
        "Quais fatores importam?",
        "Para fatoriais de 2 níveis: separar os fatores fortes dos fracos.",
    ),
    "C": (
        "Modelo",
        "O modelo explica a resposta?",
        "O ajuste, a ANOVA e o quanto o modelo acerta.",
    ),
    "D": (
        "Diagnóstico",
        "Dá para confiar no modelo?",
        "Conferir se os erros do modelo se comportam como deveriam.",
    ),
    "E": (
        "Otimização",
        "Qual é a melhor condição?",
        "Ver a forma da resposta e procurar a melhor combinação de fatores.",
    ),
}

# Cada análise: (o que ela mostra, como ler — vai na lâmpada).
GUIA: dict[str, tuple[str, str]] = {
    "A1": (
        "Média, desvio-padrão, mínimo e máximo de cada resposta.",
        "O primeiro olhar nos dados: quanto a resposta variou entre os ensaios. "
        "Um coeficiente de variação (CV) alto indica que algo mexeu bastante "
        "nela.",
    ),
    "A2": (
        "Qual planejamento os dados formam: fatorial, Box-Behnken, composto central…",
        "O EnsaIA reconhece o tipo pela posição dos pontos. É ele que decide "
        "qual modelo faz sentido ajustar.",
    ),
    "A3": (
        "Os níveis de cada ensaio em unidades reais e na escala −1, 0, +1.",
        "A escala codificada põe todos os fatores na mesma régua, para comparar "
        "o efeito do pH com o da dose, por exemplo, de igual para igual.",
    ),
    "B1": (
        "Quanto a resposta muda quando cada fator vai do nível baixo ao alto.",
        "Efeito positivo: subir o fator aumenta a resposta. Interação: o efeito "
        "de um fator depende do nível do outro.",
    ),
    "B2": (
        "A força de cada termo em barras, da maior para a menor.",
        "Barra que passa da linha tracejada é significativa. É o jeito mais "
        "rápido de ver quais fatores importam.",
    ),
    "B3": (
        "Separa efeitos reais de ruído quando não há réplicas.",
        "Efeitos que são só ruído se alinham perto da origem; os que se afastam "
        "da linha são ativos.",
    ),
    "B4": (
        "A média da resposta em cada nível e as linhas de interação.",
        "Linha inclinada: o fator importa. Linhas de interação que se abrem ou "
        "se cruzam: os fatores agem juntos.",
    ),
    "B5": (
        "Compara o ponto central com os vértices.",
        "Se o centro foge do esperado, a resposta faz curva: o modelo linear não "
        "basta e vale ampliar para um composto central.",
    ),
    "C1": (
        "Os coeficientes do modelo, com erro-padrão e p-valor.",
        "Cada coeficiente diz quanto o termo soma à resposta. p menor que α: o "
        "termo é significativo.",
    ),
    "C2": (
        "Testa se o modelo explica a resposta além do acaso.",
        "Olhe o p da regressão: menor que α, o modelo explica. A tabela também "
        "mostra o peso de cada termo.",
    ),
    "C3": (
        "Quanto da variação o modelo explica e quanto acerta ensaios novos.",
        "R² perto de 1 é bom, mas confira o ajustado e o de predição: muito "
        "abaixo do R², o modelo decorou os dados.",
    ),
    "C4": (
        "Compara o erro do modelo com o erro das réplicas.",
        "O desejável é não ser significativa (p ≥ α): aí a forma do modelo "
        "acompanha a resposta.",
    ),
    "C5": (
        "A fórmula do modelo, codificada e em unidades reais.",
        "Com a equação em unidades reais, dá para calcular a resposta direto "
        "com os valores do laboratório.",
    ),
    "C6": (
        "O que o modelo previu contra o que foi medido, ensaio a ensaio.",
        "Pontos sobre a reta y = x são ensaios que o modelo acerta; longe dela, "
        "ele erra.",
    ),
    "D1": (
        "Os erros do modelo em cada ensaio.",
        "Os pontos devem se espalhar ao acaso em torno do zero. Funil ou curva "
        "indicam algo que o modelo deixou de fora.",
    ),
    "D2": (
        "Gráfico Q-Q e teste de Shapiro-Wilk dos resíduos.",
        "Os p-valores do modelo supõem resíduos normais. Se o teste rejeitar, "
        "leia-os com cautela.",
    ),
    "D3": (
        "Os erros na ordem em que os ensaios foram feitos.",
        "Uma tendência ao longo do tempo indica deriva do equipamento, do "
        "reagente ou do operador.",
    ),
    "D4": (
        "Ensaios que, sozinhos, puxam o modelo ou destoam muito.",
        "Vale conferir no caderno se esses ensaios foram feitos como planejado.",
    ),
    "E1": (
        "A resposta como um relevo sobre dois fatores.",
        "Mostra a forma da resposta: picos, vales e selas. Gire para ver de "
        "outros ângulos.",
    ),
    "E2": (
        "O mesmo relevo visto de cima, em linhas de mesmo valor.",
        "Cada linha liga condições com a mesma resposta; anéis fechados indicam "
        "um máximo ou um mínimo.",
    ),
    "E3": (
        "Onde a superfície fica plana: máximo, mínimo ou sela.",
        "Diz se existe um ótimo dentro da região estudada e de que tipo ele é.",
    ),
    "E4": (
        "A combinação de fatores que maximiza, minimiza ou atinge um alvo.",
        "Sempre confirme a condição encontrada com um ensaio antes de adotá-la.",
    ),
    "E5": (
        "O melhor meio-termo quando há várias respostas.",
        "Cada resposta ganha uma nota de 0 a 1; a desejabilidade global D "
        "combina todas.",
    ),
}


class _Cartao:
    """Uma análise: clicar (ou Enter/Espaço) inclui ou tira do laudo."""

    def __init__(self, id_: str, nome: str, ao_mudar: Callable[[], None]) -> None:
        self.id = id_
        self.incluida = True
        self.motivo: str | None = None
        self._ao_mudar = ao_mudar
        mostra, como_ler = GUIA[id_]
        self.el = ui.element("div").classes("ea-analise-cartao")
        with self.el:
            with ui.element("div").classes("ea-analise-topo"):
                ui.label(nome).classes("ea-analise-nome")
                # A lâmpada não alterna o cartão: só abre a dica.
                dica(como_ler).on("click", js_handler="(e) => e.stopPropagation()")
                self.selo = ui.label().classes("ea-analise-selo")
            ui.label(mostra).classes("ea-analise-texto")
            self.porque = ui.label().classes("ea-analise-motivo")
        self.el.on("click", self.alternar)
        self.el.on("keydown.enter.prevent", self.alternar)
        self.el.on("keydown.space.prevent", self.alternar)

    def alternar(self) -> None:
        if self.motivo is not None:
            return
        self.incluida = not self.incluida
        self.desenhar()
        self._ao_mudar()

    def definir(self, motivo: str | None) -> None:
        """Novo mapeamento: compatível volta incluída; incompatível sai."""
        self.motivo = motivo
        self.incluida = motivo is None
        self.desenhar()

    def desenhar(self) -> None:
        aplica = self.motivo is None
        self.el.classes(
            add="ea-analise-on" if self.incluida else "ea-analise-off",
            remove="ea-analise-off" if self.incluida else "ea-analise-on",
        )
        self.el.classes(**{"add" if aplica else "remove": "ea-analise-aplica"})
        self.el.classes(**{"remove" if aplica else "add": "ea-analise-na"})
        if aplica:
            self.selo.set_text("Incluída" if self.incluida else "Fora")
            marcado = str(self.incluida).lower()
            self.el.props(f'role="switch" tabindex="0" aria-checked="{marcado}"')
            self.el.props(remove="aria-disabled")
        else:
            self.selo.set_text("Não se aplica")
            self.el.props('role="switch" tabindex="-1" aria-checked="false"')
            self.el.props('aria-disabled="true"')
        self.porque.set_text(f"Por quê: {self.motivo}." if self.motivo else "")
        self.porque.set_visibility(not aplica)


class PainelAnalises:
    """As análises em etapas, recalculadas a cada mudança no mapeamento.

    Cada etapa é um dropdown: o cabeçalho diz a pergunta que ela responde e
    quantas análises estão incluídas; aberto, mostra os cartões.
    """

    def __init__(self, mapa: FonteMapeamento) -> None:
        self.mapa = mapa
        self.cartoes: dict[str, _Cartao] = {}
        self.contagens: dict[str, ui.label] = {}

        with ui.element("div").classes("ea-analises"):
            with ui.element("div").classes("ea-titulo-linha"):
                ui.label("Análises").classes("ea-secao-titulo")
                dica(
                    "Cada análise é um cartão: clique para incluir ou tirar do "
                    "laudo. As que não se aplicam aos seus dados ficam apagadas, "
                    "com o motivo escrito."
                )
            ui.label("Escolha o que entra no laudo, etapa por etapa.").classes(
                "ea-secao-sub"
            )
            for i, (grupo, (curto, pergunta, serve)) in enumerate(ETAPAS.items(), 1):
                self._etapa(grupo, i, curto, pergunta, serve)
        mapa.ouvintes.append(self.atualizar)
        self.atualizar()

    def _etapa(
        self, grupo: str, numero: int, curto: str, pergunta: str, serve: str
    ) -> None:
        etapa = ui.expansion().classes("ea-etapa w-full").props("dense")
        with (
            etapa.add_slot("header"),
            ui.element("div").classes("ea-etapa-cabeca"),
        ):
            ui.label(str(numero)).classes("ea-etapa-num")
            with ui.element("div").classes("ea-etapa-textos"):
                ui.label(curto).classes("ea-etapa-nome")
                ui.label(pergunta).classes("ea-etapa-pergunta")
            self.contagens[grupo] = ui.label().classes("ea-etapa-conta")
        with etapa:
            ui.label(serve).classes("ea-ler")
            with ui.element("div").classes("ea-analise-grade"):
                for analise in (a for a in CATALOGO if a.grupo == grupo):
                    self.cartoes[analise.id] = _Cartao(
                        analise.id, analise.nome, self._rotular
                    )
            with ui.element("div").classes("ea-acoes"):
                ui.button(
                    "Incluir todas desta etapa",
                    on_click=lambda g=grupo: self._todas(g, True),
                ).props("flat dense no-caps").classes("ea-botao-sec")
                ui.button(
                    "Tirar todas",
                    on_click=lambda g=grupo: self._todas(g, False),
                ).props("flat dense no-caps").classes("ea-botao-sec")

    def _todas(self, grupo: str, incluir: bool) -> None:
        for id_, cartao in self.cartoes.items():
            if id_[0] == grupo and cartao.motivo is None:
                cartao.incluida = incluir
                cartao.desenhar()
        self._rotular()

    def atualizar(self) -> None:
        tabela = self.mapa.tabela
        fatores = {
            c: [float(v) for v in tabela.coluna(c)] for c in self.mapa.colunas("fator")
        }
        disponivel = disponibilidade(
            fatores,
            n_respostas=len(self.mapa.colunas("resposta")),
            tem_ordem=bool(self.mapa.colunas("ordem")),
        )
        for id_, motivo in disponivel.items():
            self.cartoes[id_].definir(motivo)
        self._rotular()

    def _rotular(self) -> None:
        for grupo, contagem in self.contagens.items():
            do_grupo = [c for i, c in self.cartoes.items() if i[0] == grupo]
            aplicaveis = [c for c in do_grupo if c.motivo is None]
            dentro = sum(1 for c in aplicaveis if c.incluida)
            contagem.set_text(f"{dentro}/{len(aplicaveis)} incluídas")

    def marcadas(self) -> list[str]:
        return [
            id_ for id_, c in self.cartoes.items() if c.incluida and c.motivo is None
        ]
