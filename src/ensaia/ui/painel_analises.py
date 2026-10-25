"""Escolha das análises em etapas (modelo, diagnóstico, otimização).
Cada análise é um cartão; as que não cabem nos dados ficam apagadas com o motivo.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from nicegui import ui

from ensaia.core.blocos import ler_blocos
from ensaia.core.catalogo import CATALOGO, IDS, disponibilidade
from ensaia.core.fluxo import Papel
from ensaia.core.table import Table
from ensaia.ui.ajuda import FORMULAS, dica

# Sempre calculadas e sempre no laudo: não viram cartão.
_SEMPRE_INCLUIDAS = frozenset({"A1", "A2", "A3"})


class FonteMapeamento(Protocol):
    """O que o painel precisa do mapeamento de colunas."""

    tabela: Table
    ouvintes: list[Callable[[], None]]

    def colunas(self, papel: Papel) -> list[str]: ...
    def tem_ordem(self) -> bool: ...


# Cada etapa: rótulo, pergunta que responde e para que serve.
ETAPAS: dict[str, tuple[str, str, str]] = {
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
        "Confere se os dados formam um DCCR: parte fatorial, pontos axiais e "
        "pontos centrais.",
        "O EnsaIA reconhece o DCCR pela posição dos pontos e confere se o α "
        "axial é o rotacional. Se não for um DCCR, diz o que falta.",
    ),
    "A3": (
        "Os níveis de cada ensaio em unidades reais e na escala −1, 0, +1.",
        "A escala codificada põe todos os fatores na mesma régua, para comparar "
        "o efeito do pH com o da dose, por exemplo, de igual para igual.",
    ),
    "C1": (
        "Os coeficientes do modelo, com erro-padrão e p-valor, e o Pareto dos "
        "efeitos padronizados.",
        "Cada coeficiente diz quanto o termo soma à resposta. p menor que α: o "
        "termo é significativo. No Pareto, a barra que passa da linha "
        "tracejada é significativa.",
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


# Fórmula de cada análise para o modo de fórmulas.
FORMULA_ANALISE: dict[str, str] = {
    "A1": FORMULAS["descritiva"],
    "A2": ("Parte fatorial: ±1;  axiais: ±α;  centro: 0\nRotacional: α = n_fat^(1/4)"),
    "A3": FORMULAS["matriz"],
    "C1": FORMULAS["coeficientes"] + "\n" + FORMULAS["pareto"],
    "C2": FORMULAS["regressao"],
    "C3": "\n".join(
        FORMULAS[c] for c in ("r2", "r2_ajustado", "r2_predicao", "r2_maximo")
    ),
    "C4": FORMULAS["falta_ajuste"],
    "C5": FORMULAS["equacao"],
    "C6": FORMULAS["previsto_observado"],
    "D1": FORMULAS["residuos_previsto"],
    "D2": FORMULAS["normalidade"],
    "D3": FORMULAS["residuos_ordem"],
    "D4": FORMULAS["influentes"],
    "E1": FORMULAS["superficie"],
    "E2": "Curvas  ŷ(x₁, x₂) = c,  para vários valores de c",
    "E3": "xₛ = −½ · B⁻¹ · b\nb: coeficientes lineares;  B: quadráticos e interações",
    "E4": "x* = o x que maximiza (ou minimiza) ŷ(x)\ndentro da região estudada",
    "E5": FORMULAS["desejabilidade"],
}


class _Cartao:
    """Cartão de uma análise: clicar inclui ou tira do laudo."""

    def __init__(self, id_: str, nome: str, ao_mudar: Callable[[], None]) -> None:
        """Cria o cartão com nome, texto, dica e motivo."""
        self.id = id_
        self.incluida = True
        self.motivo: str | None = None
        self._ao_mudar = ao_mudar
        mostra, como_ler = GUIA[id_]
        self.el = ui.element("div").classes("ea-analise-cartao")
        with self.el:
            with ui.element("div").classes("ea-analise-topo"):
                ui.label(nome).classes("ea-analise-nome")
                # A lâmpada só abre a dica; não alterna o cartão.
                dica(como_ler, FORMULA_ANALISE.get(id_)).on(
                    "click", js_handler="(e) => e.stopPropagation()"
                )
            ui.label(mostra).classes("ea-analise-texto")
            self.porque = ui.label().classes("ea-analise-motivo")
        self.el.on("click", self.alternar)
        self.el.on("keydown.enter.prevent", self.alternar)
        self.el.on("keydown.space.prevent", self.alternar)

    def alternar(self) -> None:
        """Inclui ou tira a análise, se ela estiver disponível."""
        if self.motivo is not None:
            return
        self.incluida = not self.incluida
        self.desenhar()
        self._ao_mudar()

    def definir(self, motivo: str | None) -> None:
        """Atualiza o cartão com a disponibilidade nova."""
        self.motivo = motivo
        self.incluida = motivo is None
        self.desenhar()

    def desenhar(self) -> None:
        """Aplica o visual de incluída, excluída ou indisponível."""
        aplica = self.motivo is None
        self.el.classes(
            add="ea-analise-on" if self.incluida else "ea-analise-off",
            remove="ea-analise-off" if self.incluida else "ea-analise-on",
        )
        self.el.classes(**{"add" if aplica else "remove": "ea-analise-aplica"})
        self.el.classes(**{"remove" if aplica else "add": "ea-analise-na"})
        if aplica:
            marcado = str(self.incluida).lower()
            self.el.props(f'role="switch" tabindex="0" aria-checked="{marcado}"')
            self.el.props(remove="aria-disabled")
        else:
            self.el.props('role="switch" tabindex="-1" aria-checked="false"')
            self.el.props('aria-disabled="true"')
        self.porque.set_text(f"Por quê: {self.motivo}." if self.motivo else "")
        self.porque.set_visibility(not aplica)


class PainelAnalises:
    """Análises em etapas, recalculadas a cada mudança no mapeamento."""

    def __init__(self, mapa: FonteMapeamento) -> None:
        """Cria as etapas e os cartões."""
        self.mapa = mapa
        self.cartoes: dict[str, _Cartao] = {}
        self.contagens: dict[str, ui.label] = {}
        self.botoes: dict[str, ui.button] = {}

        with ui.element("div").classes("ea-analises"):
            ui.label("Análises").classes("ea-secao-titulo")
            ui.label(
                "Escolha o que entra no laudo, etapa por etapa. Clique numa análise "
                "para incluir ou tirar."
            ).classes("ea-secao-sub")
            for i, (grupo, (curto, pergunta, serve)) in enumerate(ETAPAS.items(), 1):
                self._etapa(grupo, i, curto, pergunta, serve)
        mapa.ouvintes.append(self.atualizar)
        self.atualizar()

    def _etapa(
        self, grupo: str, numero: int, curto: str, pergunta: str, serve: str
    ) -> None:
        """Cria uma etapa recolhível com seus cartões."""
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
            self.botoes[grupo] = (
                ui.button(on_click=lambda g=grupo: self._alternar_todas(g))
                .props("outline dense no-caps")
                .classes("ea-etapa-todas")
            )

    def _aplicaveis(self, grupo: str) -> list[_Cartao]:
        """Cartões disponíveis de um grupo."""
        return [
            c for i, c in self.cartoes.items() if i[0] == grupo and c.motivo is None
        ]

    def _alternar_todas(self, grupo: str) -> None:
        """Inclui todas as análises da etapa, ou tira todas."""
        aplicaveis = self._aplicaveis(grupo)
        incluir = not all(c.incluida for c in aplicaveis)
        for cartao in aplicaveis:
            cartao.incluida = incluir
            cartao.desenhar()
        self._rotular()

    def atualizar(self) -> None:
        """Recalcula a disponibilidade com o mapeamento atual."""
        tabela = self.mapa.tabela
        fatores = {
            c: [float(v) for v in tabela.coluna(c)] for c in self.mapa.colunas("fator")
        }
        disponivel = disponibilidade(
            fatores,
            n_respostas=len(self.mapa.colunas("resposta")),
            tem_ordem=self.mapa.tem_ordem(),
            blocos=self._rotulos_bloco(),
        )
        for id_, motivo in disponivel.items():
            if id_ in self.cartoes:
                self.cartoes[id_].definir(motivo)
        self._rotular()

    def _rotulos_bloco(self) -> list[str] | None:
        """Bloco de cada ensaio, se a coluna for válida."""
        coluna = next(iter(self.mapa.colunas("bloco")), None)
        if coluna is None:
            return None
        try:
            return list(ler_blocos(self.mapa.tabela, coluna).rotulos)
        except ValueError:  # coluna que não serve de bloco: avisa ao analisar
            return None

    def _rotular(self) -> None:
        """Atualiza as contagens de cada etapa."""
        for grupo, contagem in self.contagens.items():
            aplicaveis = self._aplicaveis(grupo)
            dentro = sum(1 for c in aplicaveis if c.incluida)
            contagem.set_text(f"{dentro}/{len(aplicaveis)}")
            contagem.props(
                f'aria-label="{dentro} de {len(aplicaveis)} análises incluídas"'
            )
            todas = bool(aplicaveis) and dentro == len(aplicaveis)
            botao = self.botoes[grupo]
            botao.set_text("Tirar todas" if todas else "Incluir todas")
            botao.props(f"icon={'remove_done' if todas else 'done_all'}")
            botao.set_enabled(bool(aplicaveis))

    def marcadas(self) -> list[str]:
        """IDs das análises que vão para o laudo."""
        escolhidas = {
            id_ for id_, c in self.cartoes.items() if c.incluida and c.motivo is None
        }
        return [id_ for id_ in IDS if id_ in _SEMPRE_INCLUIDAS or id_ in escolhidas]
