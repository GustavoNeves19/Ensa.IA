"""Passos 3 e 4 do fluxo (spec §4): mapear colunas, analisar e mostrar o laudo.

Depois que `ui/upload.py` lê a planilha numa `Table`, esta tela:

1. **Mapear** — para cada coluna, o usuário diz se é fator (entrada), resposta
   (saída) ou se deve ser ignorada. O padrão é inteligente: colunas numéricas
   viram fatores, a última numérica vira resposta, texto é ignorado.
2. **Analisar** — reconhece o planejamento a partir dos próprios dados
   (`core.identificacao`: codificação de cada fator, com os ±1 certos no
   composto central, e o tipo pela geometria dos pontos), escolhe os termos do
   modelo conforme o tipo e roda o núcleo determinístico (`core.pipeline`).
3. **Mostrar** — por resposta, abas Efeitos (Pareto + coeficientes), ANOVA,
   Diagnóstico (preditos × observados, resíduos, Q-Q) e Superfície (contorno e
   3D com os demais fatores ajustáveis). Cada aba só é montada quando aberta
   (spec §7.3: a NiceGUI guarda no servidor a árvore de cada aba aberta).
4. **Relatório** — o texto (sem IA, colado de uma IA qualquer, Ollama local ou
   nuvem; ver `ui/narrar.py`) e os downloads de PDF e JSON.

Nada é calculado aqui: a conta é toda do núcleo; esta camada só coleta escolhas,
chama o pipeline e desenha o resultado.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from html import escape, unescape
from typing import Any, cast

from nicegui import run, ui
from nicegui.events import EChartPointClickEventArguments

from ensaia import __version__
from ensaia.ai.report import gerar_relatorio
from ensaia.core.catalogo import IDS
from ensaia.core.descritiva import matriz_codificada, matriz_ensaios
from ensaia.core.design import (
    INTERCEPTO,
    Fator,
    Planejamento,
    interpretar_termo,
    nome_legivel,
)
from ensaia.core.desirability import metas_padrao, otimizar
from ensaia.core.diagnostico import pontos_qq
from ensaia.core.fatorial import pontos_meio_normal
from ensaia.core.fluxo import Papel, analisar_tabela, sugerir_mapeamento
from ensaia.core.indicativos import indicativos, proximos_passos
from ensaia.core.pipeline import limite_da_regiao
from ensaia.core.results import (
    NOME_PLANEJAMENTO,
    AjusteResposta,
    AnalysisResult,
    Diagnostico,
    EfeitosFatorial,
    LinhaAnova,
    PontoOtimo,
    Sentido,
    TermoErro,
    TesteCurvatura,
    TipoModelo,
)
from ensaia.core.surface import (
    PONTOS_PADRAO,
    grade_superficie,
    ordem_por_forca,
    par_inicial,
    prever_condicao,
)
from ensaia.core.table import Table
from ensaia.core.termos import NOME_MODELO
from ensaia.ui import graficos
from ensaia.ui.ajuda import ajuda, titulo_com_ajuda
from ensaia.ui.narrar import construir_narracao
from ensaia.ui.painel_analises import PainelAnalises
from ensaia.ui.sessao import Sessao

# Os grupos do quadro de mapear, na ordem da tela: (papel, título).
_GRUPOS_MAPA: list[tuple[Papel, str]] = [
    ("resposta", "Variáveis Dependentes"),
    ("fator", "Variáveis Independentes"),
    ("ordem", "Ordem dos ensaios"),
    ("ignorar", "Não usar"),
]

# Prefixo do dado arrastado: o drop só aceita o que saiu de um cartão do quadro,
# não um texto qualquer arrastado de outra janela.
_ARRASTO = "ensaia-coluna:"

_MODELOS = {
    "auto": "Automático (pelo planejamento)",
    "linear": "Linear",
    "interacoes": "Com interações",
    "quadratico": "Quadrático",
}


@dataclass
class _Opcoes:
    """Escolhas do usuário sobre o modelo (spec §4, opções avançadas)."""

    tipo_modelo: str = "auto"
    termo_erro: str = "residuo"
    alfa: float = 0.05
    reduzir: bool = False
    excluidos: list[str] = field(default_factory=list)


def construir_analise(tabela: Table, nome_arquivo: str | None = None) -> None:
    """Monta o fluxo mapear → analisar → resultados para a `Table` carregada.

    `nome_arquivo` vai para a capa do PDF.
    """
    mapa = _Mapeamento(tabela)

    with ui.element("div").classes("ea-mapear"):
        ui.label("Mapear colunas").classes("ea-secao-titulo")
        ui.label(
            "Arraste cada coluna para o seu grupo, ou clique nela e escolha o grupo."
        ).classes("ea-secao-sub")
        _QuadroMapeamento(mapa)

    painel_analises = PainelAnalises(mapa)
    opcoes = _Opcoes()
    _painel_opcoes(opcoes)

    def analisar_e_mostrar() -> None:
        fatores = mapa.colunas("fator")
        respostas = mapa.colunas("resposta")
        ordens = mapa.colunas("ordem")
        if not fatores:
            ui.notify("Escolha ao menos uma coluna como Fator.", type="warning")
            return
        if not respostas:
            ui.notify("Escolha ao menos uma coluna como Resposta.", type="warning")
            return
        try:
            analise, planejamento, candidatos = _rodar_analise(
                tabela,
                fatores,
                respostas,
                opcoes,
                ordens[0] if ordens else None,
                painel_analises.marcadas(),
            )
        except ValueError as erro:
            ui.notify(str(erro), type="negative", position="top", timeout=9000)
            return
        except Exception as erro:
            ui.notify(
                f"Não foi possível analisar: {erro}",
                type="negative",
                position="top",
                timeout=9000,
            )
            return
        resultado.clear()
        with resultado:
            _mostrar_resultados(
                analise,
                planejamento,
                candidatos,
                opcoes,
                analisar_e_mostrar,
                tabela,
                nome_arquivo,
            )

    def ao_analisar() -> None:
        opcoes.excluidos.clear()  # nova análise parte do modelo completo
        analisar_e_mostrar()

    ui.button("Analisar", on_click=ao_analisar).props("unelevated").classes("ea-botao")
    # Os resultados aparecem ABAIXO do botão, na ordem de leitura.
    resultado = ui.column().classes("w-full ea-slot")


class _Mapeamento:
    """O papel de cada coluna da planilha, ponto de partida do passo "mapear".

    Começa na sugestão do núcleo (`sugerir_mapeamento`) e avisa os `ouvintes`
    a cada mudança: o quadro se redesenha e o painel de análises recalcula o
    que se aplica.
    """

    def __init__(self, tabela: Table) -> None:
        self.tabela = tabela
        self.papeis: dict[str, Papel] = sugerir_mapeamento(tabela)
        self.ouvintes: list[Callable[[], None]] = []

    def colunas(self, papel: Papel) -> list[str]:
        """As colunas de um papel, na ordem em que aparecem na planilha."""
        return [c for c in self.tabela.colunas if self.papeis[c] == papel]

    def pode_mover(self, coluna: str) -> bool:
        """Coluna de texto só pode ser ignorada: o modelo precisa de números."""
        return self.tabela.e_numerica(coluna)

    def mover(self, coluna: str, papel: Papel) -> None:
        if self.papeis[coluna] == papel:
            return
        if not self.pode_mover(coluna) and papel != "ignorar":
            ui.notify(
                f"{coluna!r} tem texto: só colunas numéricas entram na análise.",
                type="warning",
            )
            return
        if papel == "ordem":  # só uma ordem: a que estava lá deixa de ser usada
            for outra in self.colunas("ordem"):
                self.papeis[outra] = "ignorar"
        self.papeis[coluna] = papel
        for ouvinte in self.ouvintes:
            ouvinte()


class _QuadroMapeamento:
    """Os grupos de colunas, com arrastar e soltar (e um menu, sem mouse).

    O arrasto acontece todo no navegador; só o soltar vai ao servidor, levando
    a posição da coluna na planilha. O menu "Mover para" de cada cartão faz o
    mesmo pelo clique ou pelo teclado, e no celular, onde o arrastar do HTML
    nem sempre funciona.
    """

    def __init__(self, mapa: _Mapeamento) -> None:
        self.mapa = mapa
        self.listas: dict[Papel, ui.element] = {}
        with ui.element("div").classes("ea-quadro"):
            for papel, titulo in _GRUPOS_MAPA:
                self.listas[papel] = self._zona(papel, titulo)
        mapa.ouvintes.append(self.desenhar)
        self.desenhar()

    def _zona(self, papel: Papel, titulo: str) -> ui.element:
        principal = papel in ("resposta", "fator")
        zona = ui.element("div").classes(
            f"ea-zona ea-zona-{papel}" + ("" if principal else " ea-zona-menor")
        )
        zona.props(f'role="group" aria-label="{escape(titulo)}"')
        with zona:
            with ui.element("div").classes("ea-zona-topo"):
                ui.label(titulo).classes("ea-zona-titulo")
                with ui.element("div").classes("ea-zona-soltar"):
                    ui.icon("move_to_inbox")
                    ui.label("soltar aqui")
            lista = ui.element("div").classes("ea-zona-lista")
        # Arrastar por cima: realce e permissão para soltar, sem ir ao servidor.
        zona.on(
            "dragover",
            js_handler="(e) => { e.preventDefault(); "
            "e.currentTarget.classList.add('ea-zona-alvo'); }",
        )
        zona.on(
            "dragleave",
            js_handler="(e) => { if (!e.currentTarget.contains(e.relatedTarget)) "
            "e.currentTarget.classList.remove('ea-zona-alvo'); }",
        )
        zona.on(
            "drop",
            lambda e, p=papel: self._soltar(e.args, p),
            js_handler="(e) => { e.preventDefault(); "
            "e.currentTarget.classList.remove('ea-zona-alvo'); "
            "const dado = e.dataTransfer.getData('text/plain'); "
            f"if (dado.startsWith('{_ARRASTO}')) "
            f"emit(dado.slice({len(_ARRASTO)})); }}",
        )
        return lista

    def _soltar(self, indice: Any, papel: Papel) -> None:
        colunas = self.mapa.tabela.colunas
        try:
            coluna = colunas[int(indice)]
        except (TypeError, ValueError, IndexError):
            return
        self.mapa.mover(coluna, papel)

    def desenhar(self) -> None:
        for papel, lista in self.listas.items():
            lista.clear()
            with lista:
                colunas = self.mapa.colunas(papel)
                for coluna in colunas:
                    self._cartao(coluna)
                if not colunas:
                    ui.label("Nenhuma Coluna").classes("ea-zona-vazia")

    def _cartao(self, coluna: str) -> None:
        indice = self.mapa.tabela.colunas.index(coluna)
        movel = self.mapa.pode_mover(coluna)
        cartao = ui.element("div").classes(
            "ea-cartao" + ("" if movel else " ea-cartao-fixo")
        )
        with cartao:
            ui.icon("drag_indicator" if movel else "text_fields").classes(
                "ea-cartao-alca"
            )
            ui.label(coluna).classes("ea-cartao-nome")
        if not movel:
            cartao.props('title="Coluna de texto: fica fora da análise."')
            return
        cartao.props(
            f'draggable="true" tabindex="0" role="button" '
            f'aria-label="{escape(coluna)}: clique para escolher o grupo"'
        )
        cartao.on(
            "dragstart",
            js_handler="(e) => { e.dataTransfer.effectAllowed = 'move'; "
            f"e.dataTransfer.setData('text/plain', '{_ARRASTO}{indice}'); "
            "e.currentTarget.classList.add('ea-arrastando'); }",
        )
        cartao.on(
            "dragend",
            js_handler="(e) => e.currentTarget.classList.remove('ea-arrastando')",
        )
        atual = self.mapa.papeis[coluna]
        with cartao, ui.menu().classes("ea-cartao-menu"):
            ui.label("Mover para").classes("ea-cartao-menu-titulo")
            for papel, titulo in _GRUPOS_MAPA:
                if papel != atual:
                    ui.menu_item(titulo, lambda p=papel: self.mapa.mover(coluna, p))


def _painel_opcoes(opcoes: _Opcoes) -> None:
    """Opções avançadas, recolhidas: o padrão já serve a quem está começando."""
    with ui.expansion("Opções do modelo").classes("ea-opcoes w-full").props(
        "dense switch-toggle-side"
    ):
        with ui.element("div").classes("ea-controles"):
            ui.select(_MODELOS, label="Modelo").props("dense outlined").bind_value(
                opcoes, "tipo_modelo"
            )
            ui.toggle({"residuo": "Resíduo", "erro_puro": "Erro puro"}).props(
                "no-caps unelevated dense color=white text-color=primary "
                "toggle-color=primary toggle-text-color=white"
            ).classes("ea-forma").bind_value(opcoes, "termo_erro")
            ui.toggle({0.05: "α = 0,05", 0.10: "α = 0,10"}).props(
                "no-caps unelevated dense color=white text-color=primary "
                "toggle-color=primary toggle-text-color=white"
            ).classes("ea-forma").bind_value(opcoes, "alfa")
        ui.checkbox("Remover termos não significativos e reajustar").bind_value(
            opcoes, "reduzir"
        )
        ui.html(
            '<div class="ea-ler">Para reproduzir um artigo, use o mesmo termo de '
            "erro dele: o Minitab costuma usar o <b>resíduo</b>; o Statistica e "
            "muitos artigos brasileiros, o <b>erro puro</b> (exige réplicas, "
            "como os pontos centrais).</div>"
        )


def _rodar_analise(
    tabela: Table,
    fatores: list[str],
    respostas: list[str],
    opcoes: _Opcoes,
    coluna_ordem: str | None = None,
    analises: list[str] | None = None,
) -> tuple[AnalysisResult, Planejamento, list[str]]:
    """Roda o fluxo do núcleo com as opções da tela (o mesmo do servidor MCP).

    Devolve também o `Planejamento` (a superfície precisa das faixas dos fatores)
    e os termos candidatos do modelo, para o usuário escolher o que excluir.
    """
    pedido = None if opcoes.tipo_modelo == "auto" else opcoes.tipo_modelo
    feita = analisar_tabela(
        tabela,
        fatores,
        respostas,
        versao_ensaia=__version__,
        alfa=opcoes.alfa,
        tipo_modelo=cast(TipoModelo | None, pedido),
        excluidos=opcoes.excluidos,
        termo_erro=cast(TermoErro, opcoes.termo_erro),
        reduzir=opcoes.reduzir,
        coluna_ordem=coluna_ordem,
        analises=analises,
    )
    return feita.resultado, feita.planejamento, feita.candidatos


def _mostrar_resultados(
    analise: AnalysisResult,
    planejamento: Planejamento,
    candidatos: list[str],
    opcoes: _Opcoes,
    reanalisar: Callable[[], None],
    tabela: Table,
    nome_arquivo: str | None = None,
) -> None:
    tipo = NOME_PLANEJAMENTO.get(analise.tipo_planejamento, analise.tipo_planejamento)
    primeiro = analise.ajustes[0]
    partes = [tipo[:1].upper() + tipo[1:], f"{primeiro.n_observacoes} ensaios"]
    info = analise.planejamento
    if info is not None:
        if info.n_pontos_centrais:
            partes[-1] += f" ({info.n_pontos_centrais} no ponto central)"
        if info.alfa_axial is not None:
            partes.append(f"α axial = {_fmt(info.alfa_axial, 3)}")
    modelo = analise.metadados.tipo_modelo
    nome_modelo = f"modelo {NOME_MODELO[modelo]}" if modelo else "modelo"
    partes.append(f"{nome_modelo} com {len(primeiro.termos_incluidos)} termos")
    ui.html('<div class="ea-secao-titulo">Resultados</div>')
    ui.html(f'<div class="ea-secao-sub">{escape(" · ".join(partes))}</div>')
    _ajustar_modelo(candidatos, opcoes, reanalisar)
    sel = _marcadas(analise)
    if sel & {"A1", "A3"}:
        _dados_experimento(analise, planejamento, tabela, sel)

    for ajuste in analise.ajustes:
        with ui.element("div").classes("ea-resultado"):
            ui.html(f'<div class="ea-resp-nome">{escape(ajuste.resposta)}</div>')
            _painel_indicativos(ajuste, analise.metadados.alfa, sel)
            notas = []
            if ajuste.termo_erro == "erro_puro":
                notas.append("Testes feitos com o erro puro das réplicas.")
            if ajuste.termos_descartados:
                removidos = ", ".join(
                    nome_legivel(t) for t in ajuste.termos_descartados
                )
                notas.append(f"Removidos pela redução: {removidos}.")
            if notas:
                ui.html(f'<div class="ea-ler">{escape(" ".join(notas))}</div>')
            _abas_resposta(
                ajuste, planejamento.fatores, alfa=analise.metadados.alfa, sel=sel
            )

    for aviso in analise.avisos:
        ui.html(f'<div class="ea-aviso">{escape(aviso)}</div>')

    sessao = Sessao(
        analise,
        dados=matriz_ensaios(
            tabela, planejamento, analise.respostas, nome_arquivo
        ),
    )
    if sel & {"E4", "E5"}:
        _bloco_otimizacao(sessao, planejamento)
    if "C1" in sel:
        _bloco_prever(analise, planejamento)
    _bloco_proximos_passos(sessao, limite_da_regiao(planejamento))

    construir_narracao(sessao)
    _bloco_baixar(sessao)


_SITUACAO = {"ok": "em ordem", "atencao": "atenção", "info": ""}


def _painel_indicativos(
    ajuste: AjusteResposta, alfa: float, sel: frozenset[str]
) -> None:
    """Primeira leitura de uma resposta (US-06): os indicadores e seus sinais."""
    itens = [i for i in indicativos(ajuste, alfa) if i.analise in sel]
    if not itens:
        return
    with ui.element("div").classes("ea-indicativos"):
        for item in itens:
            with ui.element("div").classes(f"ea-ind ea-ind-{item.situacao}"):
                with ui.element("div").classes("ea-ind-rotulo"):
                    ui.label(item.rotulo)
                    ajuda(item.chave)
                ui.label(item.valor).classes("ea-ind-valor")
                if item.situacao != "info":
                    ui.label(_SITUACAO[item.situacao]).classes("ea-ind-sit")
                ui.label(item.leitura).classes("ea-ind-leitura")


def _bloco_proximos_passos(sessao: Sessao, limite: float) -> None:
    """O que fazer agora (US-17), refeito quando a melhor condição é calculada."""
    with ui.element("div").classes("ea-otimizacao"):
        ui.html('<div class="ea-secao-titulo">Próximos passos</div>')
        lista = ui.element("div").classes("ea-passos-sugeridos")

    def mostrar() -> None:
        lista.clear()
        passos = proximos_passos(sessao.analise, limite_codificado=limite)
        with lista:
            for passo in passos or [
                "Nada pede ajuste: o modelo está pronto para prever e otimizar."
            ]:
                ui.label(passo).classes("ea-passo-sugerido")

    sessao.ouvintes["proximos"] = mostrar
    mostrar()


def _marcadas(analise: AnalysisResult) -> frozenset[str]:
    """Análises marcadas; um resultado antigo sem a lista mostra tudo."""
    return frozenset(analise.metadados.analises or IDS)


def _dados_experimento(
    analise: AnalysisResult,
    planejamento: Planejamento,
    tabela: Table,
    sel: frozenset[str],
) -> None:
    """Estatística descritiva (A1) e matriz real × codificada (A3), recolhidas."""
    with ui.expansion("Dados do experimento").classes("ea-opcoes w-full").props(
        "dense switch-toggle-side"
    ):
        if analise.descritiva and "A1" in sel:
            titulo_com_ajuda("Estatística descritiva", "descritiva", "ea-tabela-rotulo")
            colunas = [
                {
                    "name": c,
                    "label": r,
                    "field": c,
                    "align": "left" if c == "r" else "right",
                }
                for c, r in [
                    ("r", "Resposta"),
                    ("n", "n"),
                    ("media", "Média"),
                    ("dp", "Desvio-padrão"),
                    ("min", "Mín."),
                    ("max", "Máx."),
                    ("cv", "CV (%)"),
                ]
            ]
            linhas = [
                {
                    "r": d.resposta,
                    "n": d.n,
                    "media": _fmt(d.media, 3),
                    "dp": _fmt(d.desvio_padrao, 3),
                    "min": _fmt(d.minimo, 3),
                    "max": _fmt(d.maximo, 3),
                    "cv": _fmt(d.cv_percentual, 1),
                }
                for d in analise.descritiva
            ]
            ui.table(columns=colunas, rows=linhas, row_key="r").props(
                "flat bordered dense hide-bottom"
            ).classes("ensaia-previa w-full")

        if "A3" not in sel:
            return
        titulo_com_ajuda(
            "Matriz do planejamento (real e, entre parênteses, codificado)",
            "matriz",
            "ea-tabela-rotulo",
        )
        codificada = matriz_codificada(tabela, planejamento)
        nomes = [f.nome for f in planejamento.fatores]
        ensaio = {"name": "n", "label": "Ensaio", "field": "n", "align": "left"}
        colunas_m = [ensaio] + [
            {"name": n, "label": nome_legivel(n), "field": n, "align": "right"}
            for n in nomes
        ]
        linhas_m = [
            {
                "n": i + 1,
                **{
                    n: f"{_fmt_curto(float(tabela.coluna(n)[i]))} "
                    f"({_fmt_curto(codificada[n][i])})"
                    for n in nomes
                },
            }
            for i in range(len(tabela))
        ]
        ui.table(
            columns=colunas_m,
            rows=linhas_m,
            row_key="n",
            pagination={"rowsPerPage": 10},
        ).props("flat bordered dense").classes("ensaia-previa w-full")


_SENTIDOS = {
    "maximizar": "Maximizar",
    "minimizar": "Minimizar",
    "alvo": "Atingir um alvo",
    "ignorar": "Não otimizar",
}


def _bloco_otimizacao(sessao: Sessao, planejamento: Planejamento) -> None:
    """Melhor condição (spec §9, E4/E5): metas por resposta e a busca no núcleo."""
    analise = sessao.analise
    with ui.element("div").classes("ea-otimizacao"):
        titulo_com_ajuda("Melhor condição", "desejabilidade", "ea-secao-titulo")
        ui.html(
            '<div class="ea-secao-sub">Diga o que você quer de cada resposta. O '
            "EnsaIA procura, dentro da região estudada, a combinação de fatores "
            "que melhor atende a todas.</div>"
        )
        escolhas: dict[str, tuple[ui.select, ui.number]] = {}
        with ui.element("div").classes("ea-mapa-grade"):
            for i, ajuste in enumerate(analise.ajustes):
                observados = ajuste.diagnostico.observados if ajuste.diagnostico else []
                meio = (min(observados) + max(observados)) / 2 if observados else None
                with ui.element("div").classes("ea-mapa-item"):
                    ui.html(f'<div class="ea-col-nome">{escape(ajuste.resposta)}</div>')
                    sentido = ui.select(
                        _SENTIDOS, value="maximizar" if i == 0 else "ignorar"
                    ).props("dense outlined")
                    alvo = ui.number("Valor-alvo", value=meio, format="%.4g").props(
                        "dense outlined"
                    )
                    alvo.bind_visibility_from(sentido, "value", value="alvo")
                    escolhas[ajuste.resposta] = (sentido, alvo)

        def buscar() -> None:
            sentidos = {
                r: cast(Sentido, sel.value)
                for r, (sel, _) in escolhas.items()
                if sel.value != "ignorar"
            }
            if not sentidos:
                ui.notify("Escolha a meta de ao menos uma resposta.", type="warning")
                return
            alvos = {
                r: float(campo.value)
                for r, (sel, campo) in escolhas.items()
                if sel.value == "alvo" and campo.value is not None
            }
            try:
                metas = metas_padrao(analise.ajustes, sentidos, alvos)
                ponto, avisos = otimizar(
                    analise.ajustes,
                    planejamento.fatores,
                    metas,
                    limite_codificado=limite_da_regiao(planejamento),
                )
            except ValueError as erro:
                ui.notify(str(erro), type="negative", position="top", timeout=9000)
                return
            sessao.trocar_analise(
                analise.model_copy(
                    update={"ponto_otimo": ponto, "avisos": [*analise.avisos, *avisos]}
                )
            )
            area.clear()
            with area:
                _mostrar_otimo(ponto, avisos, planejamento)

        ui.button("Encontrar a melhor condição", on_click=buscar).props(
            "unelevated"
        ).classes("ea-botao")
        # O resultado aparece ABAIXO do botão, na ordem de leitura.
        area = ui.column().classes("w-full ea-slot")


def _bloco_prever(analise: AnalysisResult, planejamento: Planejamento) -> None:
    """Prever uma condição (US-15, "e se?"): valores dos fatores → respostas."""
    with ui.element("div").classes("ea-otimizacao"):
        ui.html('<div class="ea-secao-titulo">Prever uma condição</div>')
        ui.html(
            '<div class="ea-secao-sub">Digite os valores dos fatores, nas unidades do '
            "laboratório, e veja o que o modelo prevê. Útil para planejar o próximo "
            "ensaio ou conferir o ensaio de confirmação.</div>"
        )
        campos: dict[str, ui.number] = {}
        with ui.element("div").classes("ea-mapa-grade"):
            for fator in planejamento.fatores:
                rotulo = nome_legivel(fator.nome)
                if fator.unidade:
                    rotulo += f" ({fator.unidade})"
                campos[fator.nome] = ui.number(
                    rotulo, value=round(fator.centro, 6), format="%.6g"
                ).props("dense outlined")

        def prever() -> None:
            valores = {
                n: float(c.value) for n, c in campos.items() if c.value is not None
            }
            try:
                previstas, extrapola = prever_condicao(
                    analise.ajustes,
                    planejamento.fatores,
                    valores,
                    limite_codificado=limite_da_regiao(planejamento),
                )
            except ValueError as erro:
                ui.notify(str(erro), type="warning", position="top")
                return
            area.clear()
            with area:
                linhas = [
                    {"r": r, "v": _fmt(v, 3)} for r, v in previstas.items()
                ]
                colunas = [
                    {"name": "r", "label": "Resposta", "field": "r", "align": "left"},
                    {"name": "v", "label": "Prevista", "field": "v", "align": "right"},
                ]
                ui.table(columns=colunas, rows=linhas, row_key="r").props(
                    "flat bordered dense hide-bottom"
                ).classes("ensaia-previa w-full")
                if extrapola:
                    ui.html(
                        '<div class="ea-aviso">Essa condição sai da região estudada: '
                        "o modelo está extrapolando e a previsão pode não valer. "
                        "Confirme com um ensaio antes de confiar nela.</div>"
                    )

        ui.button("Prever", on_click=prever).props("unelevated").classes("ea-botao")
        area = ui.column().classes("w-full ea-slot")


def _mostrar_otimo(
    ponto: PontoOtimo | None, avisos: list[str], planejamento: Planejamento
) -> None:
    for aviso in avisos:
        ui.html(f'<div class="ea-aviso">{escape(aviso)}</div>')
    if ponto is None:
        return
    unidades = {f.nome: f.unidade for f in planejamento.fatores}
    linhas = [
        {
            "item": nome_legivel(nome),
            "valor": _fmt_curto(valor),
            "extra": unidades.get(nome) or "",
        }
        for nome, valor in ponto.coordenadas.items()
    ]
    linhas += [
        {
            "item": f"{nome} (prevista)",
            "valor": _fmt(valor, 3),
            "extra": (
                f"d = {_fmt(ponto.desejabilidades_individuais[nome], 3)}"
                if ponto.metodo == "desejabilidade"
                else _SENTIDOS.get(ponto.metas.get(nome, ""), "")
            ),
        }
        for nome, valor in ponto.resposta_prevista.items()
    ]
    colunas = [
        {"name": "item", "label": "", "field": "item", "align": "left"},
        {"name": "valor", "label": "Valor", "field": "valor", "align": "right"},
        {"name": "extra", "label": "", "field": "extra", "align": "left"},
    ]
    ui.table(columns=colunas, rows=linhas, row_key="item").props(
        "flat bordered dense hide-bottom"
    ).classes("ensaia-previa w-full")
    leitura = (
        f"Desejabilidade global D = <b>{_fmt(ponto.desejabilidade_global, 3)}</b> "
        "(1 = todas as metas plenamente atendidas). "
        if ponto.metodo == "desejabilidade"
        else ""
    )
    ui.html(
        f'<div class="ea-ler">{leitura}Valores dentro da região estudada; '
        "confirme com um ensaio nessa condição antes de adotá-la.</div>"
    )


def _bloco_baixar(sessao: Sessao) -> None:
    """Passo 7 do fluxo (spec §4): baixar o relatório em PDF e os resultados em JSON."""
    with ui.element("div").classes("ea-baixar"):
        with ui.element("div").classes("ea-acoes"):
            botao_pdf = (
                ui.button("Baixar relatório (PDF)")
                .props("unelevated")
                .classes("ea-botao")
            )
            ui.button(
                "ou baixar os resultados (JSON)",
                on_click=lambda: _baixar_json(sessao.analise),
            ).props("flat").classes("ea-botao-sec")
        ui.html(
            '<div class="ea-ler">O PDF leva o texto que estiver na tela; sem texto '
            "gerado, vai o texto fiel (sem IA). Nada fica guardado: o arquivo é "
            "montado na memória e entregue direto ao seu navegador.</div>"
        )
    botao_pdf.on_click(lambda: _baixar_pdf(sessao, botao_pdf))


async def _baixar_pdf(sessao: Sessao, botao: ui.button) -> None:
    try:
        from ensaia.report import gerar_pdf  # extra [report]: fpdf2 + matplotlib
    except ImportError:
        ui.notify(
            "Para gerar o PDF, instale o extra [report] (fpdf2 e matplotlib).",
            type="warning",
            position="top",
            timeout=9000,
        )
        return

    analise = sessao.analise
    texto = sessao.texto or gerar_relatorio(analise, modo="m0")
    agora = datetime.now()
    botao.props("loading")
    try:
        # Fora da thread da interface: o matplotlib leva um instante na 1ª vez.
        pdf = await run.io_bound(
            lambda: gerar_pdf(
                analise,
                texto,
                gerado_em=agora.strftime("%d/%m/%Y %H:%M"),
                dados=sessao.dados,
            )
        )
    except Exception as erro:
        ui.notify(
            f"Não foi possível gerar o PDF: {erro}",
            type="negative",
            position="top",
            timeout=9000,
        )
        return
    finally:
        botao.props(remove="loading")
    if pdf is None:  # o servidor encerrou no meio da geração
        return
    ui.download.content(
        pdf, f"ensaia-relatorio-{agora:%Y-%m-%d-%H%M}.pdf", "application/pdf"
    )


def _baixar_json(analise: AnalysisResult) -> None:
    agora = datetime.now()
    ui.download.content(
        analise.to_json(),
        f"ensaia-resultados-{agora:%Y-%m-%d-%H%M}.json",
        "application/json",
    )


def _ajustar_modelo(
    candidatos: list[str], opcoes: _Opcoes, reanalisar: Callable[[], None]
) -> None:
    """Tirar termos do modelo e reajustar, vendo os indicadores mudarem (RF-09)."""
    with ui.element("div").classes("ea-controles ea-ajustar"):
        fora = (
            ui.select(
                {t: nome_legivel(t) for t in candidatos},
                multiple=True,
                value=[t for t in opcoes.excluidos if t in candidatos],
                label="Termos fora do modelo",
            )
            .props("dense outlined")
            .classes("ea-fora")
        )

        def reajustar() -> None:
            opcoes.excluidos[:] = list(fora.value or [])
            reanalisar()

        ui.button("Reajustar", on_click=reajustar).props("flat").classes(
            "ea-botao-sec"
        )


_ABA_EFEITOS = "Efeitos"
_PONTOS_CONTORNO = 61
_ABA_ANOVA = "ANOVA"
_ABA_DIAGNOSTICO = "Diagnóstico"
_ABA_SUPERFICIE = "Superfície"


_POR_ABA = {
    _ABA_EFEITOS: {"B1", "B2", "B3", "B4", "B5", "C1", "C5"},
    _ABA_ANOVA: {"C2", "C4"},
    _ABA_DIAGNOSTICO: {"C6", "D1", "D2", "D3", "D4"},
    _ABA_SUPERFICIE: {"E1", "E2", "E3"},
}


def _abas_resposta(
    ajuste: AjusteResposta,
    fatores: list[Fator],
    *,
    alfa: float,
    sel: frozenset[str] = frozenset(IDS),
) -> None:
    """Abas de uma resposta, cada uma montada só na primeira vez que é aberta.

    O clique numa barra do Pareto leva à superfície daquele termo (o "zoom" do
    efeito para a forma da resposta): uma interação a × b abre a superfície com
    a e b nos eixos.
    """
    tem_superficie = len(fatores) >= 2 and bool(sel & _POR_ABA[_ABA_SUPERFICIE])
    nomes = [
        nome
        for nome in (_ABA_EFEITOS, _ABA_ANOVA, _ABA_DIAGNOSTICO, _ABA_SUPERFICIE)
        if sel & _POR_ABA[nome] and (nome != _ABA_SUPERFICIE or tem_superficie)
    ]
    if not nomes:
        return

    abas = (
        ui.tabs()
        .props(
            "no-caps dense inline-label align=left narrow-indicator "
            "active-color=primary indicator-color=primary"
        )
        .classes("ea-abas w-full")
    )
    with abas:
        for nome in nomes:
            ui.tab(nome)
    caixas: dict[str, ui.column] = {}
    with ui.tab_panels(abas, value=nomes[0], animated=False).classes(
        "w-full ea-paineis"
    ):
        for nome in nomes:
            with ui.tab_panel(nome):
                caixas[nome] = ui.column().classes("w-full ea-painel-aba")

    montadas: set[str] = set()
    painel: dict[str, _PainelSuperficie] = {}

    def abrir(nome: str) -> None:
        if nome in montadas:
            return
        montadas.add(nome)
        with caixas[nome]:
            if nome == _ABA_EFEITOS:
                _aba_efeitos(
                    ajuste, alfa, ao_clicar_termo if tem_superficie else None, sel
                )
            elif nome == _ABA_ANOVA:
                _aba_anova(ajuste, alfa, sel)
            elif nome == _ABA_DIAGNOSTICO:
                _aba_diagnostico(ajuste, alfa, sel)
            else:
                painel["superficie"] = _PainelSuperficie(ajuste, fatores, sel)

    def ao_clicar_termo(termo: str) -> None:
        envolvidos = list(dict.fromkeys(n for n, _ in interpretar_termo(termo)))
        abas.set_value(_ABA_SUPERFICIE)
        abrir(_ABA_SUPERFICIE)
        painel["superficie"].focar(envolvidos)

    abas.on_value_change(lambda e: abrir(e.value))
    abrir(nomes[0])


def _grafico(
    opcoes: dict[str, Any],
    altura: int,
    descricao: str,
    on_point_click: Callable[[EChartPointClickEventArguments], None] | None = None,
) -> ui.echart:
    """Um gráfico ECharts com texto alternativo para leitores de tela (RNF-04).

    O canvas não tem texto que um leitor de tela consiga ler; `descricao` diz o
    que o gráfico mostra e fica no próprio elemento, valendo também quando as
    opções do gráfico são trocadas depois (superfície).
    """
    grafico = (
        ui.echart(opcoes, on_point_click=on_point_click)
        .classes("ea-grafico")
        .style(f"height:{altura}px")
    )
    grafico.props["role"] = "img"
    grafico.props["aria-label"] = descricao
    return grafico


def _aba_efeitos(
    ajuste: AjusteResposta,
    alfa: float,
    ao_clicar: Callable[[str], None] | None,
    sel: frozenset[str] = frozenset(IDS),
) -> None:
    if "B2" in sel:
        _pareto(ajuste, alfa, ao_clicar)
    if ajuste.efeitos_fatorial is not None:
        _bloco_fatorial(ajuste, alfa, sel)
    if "C1" in sel:
        titulo_com_ajuda(
            "Coeficientes (escala codificada)", "coeficientes", "ea-tabela-rotulo"
        )
        _tabela_coeficientes(ajuste)
    if "C5" in sel:
        _equacao(ajuste)


def _pareto(
    ajuste: AjusteResposta, alfa: float, ao_clicar: Callable[[str], None] | None
) -> None:
    titulo_com_ajuda("Pareto dos efeitos padronizados", "pareto")

    def clique(evento: EChartPointClickEventArguments) -> None:
        if ao_clicar and isinstance(evento.data, dict) and evento.data.get("termo"):
            ao_clicar(str(evento.data["termo"]))

    efeitos = [c for c in ajuste.coeficientes if c.termo != INTERCEPTO]
    fortes = [nome_legivel(c.termo) for c in efeitos if c.significativo]
    _grafico(
        graficos.opcoes_pareto(ajuste, alfa=alfa),
        graficos.altura_pareto(ajuste),
        f"Pareto dos efeitos de {nome_legivel(ajuste.resposta)}: "
        f"{len(fortes)} de {len(efeitos)} termos passam do t crítico"
        + (f" ({', '.join(fortes)})." if fortes else "."),
        on_point_click=clique,
    )
    dica = (
        " Clique numa barra para ver a superfície daquele termo."
        if ao_clicar
        else ""
    )
    if ajuste.t_critico is None:
        corte = "Sem grau de liberdade no resíduo, não há linha de corte."
    else:
        corte = (
            "Barra que passa da <b>linha tracejada</b> (t crítico = "
            f"{_fmt(ajuste.t_critico, 2)}) é significativa a α = {_fmt(alfa, 2)}."
        )
    ui.html(
        '<div class="ea-ler">Quanto maior a barra, mais o termo mexe na resposta. '
        f"{corte}{dica}</div>"
    )


def _bloco_fatorial(
    ajuste: AjusteResposta, alfa: float, sel: frozenset[str] = frozenset(IDS)
) -> None:
    """Efeitos (B1), meio-normal (B3), efeito e interação (B4) e curvatura (B5)."""
    ef = ajuste.efeitos_fatorial
    assert ef is not None
    if "B1" in sel:
        _tabela_efeitos(ef)
    if ef.lenth is not None and "B3" in sel:
        _meio_normal(ef)
    if "B4" in sel:
        _efeitos_principais(ef)
        _interacao(ef)
    if "B5" in sel:
        ui.html(f'<div class="ea-ler">{_texto_curvatura(ef.curvatura, alfa)}</div>')


def _tabela_efeitos(ef: EfeitosFatorial) -> None:
    titulo_com_ajuda("Efeitos (de −1 a +1)", "efeitos", "ea-tabela-rotulo")
    colunas = [
        {"name": "termo", "label": "Termo", "field": "termo", "align": "left"},
        {"name": "ef", "label": "Efeito", "field": "ef", "align": "right"},
        {"name": "ep", "label": "Erro padrão", "field": "ep", "align": "right"},
        {"name": "p", "label": "p-valor", "field": "p", "align": "right"},
        {"name": "sig", "label": "Signif.", "field": "sig", "align": "center"},
    ]
    linhas = [
        {
            "termo": nome_legivel(e.termo),
            "ef": _fmt(e.efeito, 4),
            "ep": _fmt(e.erro_padrao, 4),
            "p": _fmt_p_tabela(e.valor_p),
            "sig": "sim" if e.significativo else "—",
        }
        for e in sorted(ef.efeitos, key=lambda e: abs(e.efeito), reverse=True)
    ]
    ui.table(columns=colunas, rows=linhas, row_key="termo").props(
        "flat bordered dense hide-bottom"
    ).classes("ensaia-previa w-full")


def _meio_normal(ef: EfeitosFatorial) -> None:
    assert ef.lenth is not None
    ativos = {e.termo for e in ef.efeitos if e.ativo_lenth}
    titulo_com_ajuda("Gráfico meio-normal dos efeitos", "meio_normal")
    _grafico(
        graficos.opcoes_meio_normal(
            pontos_meio_normal(ef.efeitos), ef.lenth.me, ativos
        ),
        300,
        "Gráfico meio-normal dos efeitos: "
        + (
            f"ativos pelo método de Lenth: {', '.join(map(nome_legivel, ativos))}."
            if ativos
            else "nenhum efeito ativo pelo método de Lenth."
        ),
    )
    ui.html(
        '<div class="ea-ler">Efeitos que são só ruído se alinham perto da origem; '
        "os que se afastam para a direita da <b>linha tracejada</b> (margem de "
        f"Lenth, ME = {_fmt(ef.lenth.me, 3)}) são ativos. Útil quando não há "
        "réplicas para estimar o erro.</div>"
    )


def _efeitos_principais(ef: EfeitosFatorial) -> None:
    if not ef.medias_principais:
        return
    todas = [v for m in ef.medias_principais for v in m.medias]
    baixo, alto = min(todas), max(todas)
    folga = (alto - baixo) * 0.12 or 1.0
    titulo_com_ajuda("Efeitos principais", "efeitos_principais")
    with ui.element("div").classes("ea-multiplos"):
        for m in ef.medias_principais:
            _grafico(
                graficos.opcoes_medias(m, baixo - folga, alto + folga),
                200,
                f"Média da resposta em cada nível de {nome_legivel(m.fator)}.",
            )
    ui.html(
        '<div class="ea-ler">Média da resposta em cada nível, na mesma escala: '
        "quanto mais inclinada a linha, maior o efeito do fator.</div>"
    )


def _interacao(ef: EfeitosFatorial) -> None:
    if not ef.medias_interacoes:
        return
    efeito_de = {e.termo: abs(e.efeito) for e in ef.efeitos}
    mais_forte = max(
        ef.medias_interacoes,
        key=lambda m: efeito_de.get(f"{m.fator_a}:{m.fator_b}", 0.0),
    )
    titulo_com_ajuda(
        f"Interação {nome_legivel(mais_forte.fator_a)} × "
        f"{nome_legivel(mais_forte.fator_b)}",
        "interacao",
    )
    _grafico(
        graficos.opcoes_interacao(mais_forte),
        280,
        f"Interação entre {nome_legivel(mais_forte.fator_a)} e "
        f"{nome_legivel(mais_forte.fator_b)}: uma linha por nível do segundo fator.",
    )
    ui.html(
        '<div class="ea-ler">A interação mais forte do modelo. Linhas paralelas: '
        "os fatores agem cada um por si; linhas que se abrem ou se cruzam: o "
        "efeito de um depende do nível do outro.</div>"
    )


def _texto_curvatura(curvatura: TesteCurvatura, alfa: float) -> str:
    if not curvatura.aplicavel:
        motivo = curvatura.motivo_inaplicavel or "sem pontos centrais"
        return f"Teste de curvatura não aplicável ({escape(motivo)})."
    teste = f"p = {_fmt_p(curvatura.valor_p)}"
    if curvatura.significativa:
        return (
            f"<b>Há curvatura</b> ({teste} &lt; {_fmt(alfa, 2)}): o centro difere dos "
            "vértices e o modelo linear não basta. Vale ampliar para um composto "
            "central e ajustar termos quadráticos."
        )
    return f"Sem evidência de curvatura ({teste}): o modelo linear descreve a região."


def _equacao(ajuste: AjusteResposta) -> None:
    eq = ajuste.equacao
    if eq is None:
        return
    legenda = ", ".join(f"{s} = {nome_legivel(n)}" for s, n in eq.variaveis.items())
    titulo_com_ajuda("Equação do modelo", "equacao", "ea-tabela-rotulo")
    ui.html(f'<div class="ea-equacao">{escape(eq.codificada)}</div>')
    ui.html(f'<div class="ea-ler">Variáveis codificadas ({escape(legenda)}).</div>')
    ui.html(f'<div class="ea-equacao">{escape(eq.real.replace("_", " "))}</div>')
    ui.html(
        '<div class="ea-ler">A mesma equação em unidades reais: use direto os '
        "valores do laboratório.</div>"
    )


def _aba_anova(
    ajuste: AjusteResposta, alfa: float, sel: frozenset[str] = frozenset(IDS)
) -> None:
    reg = ajuste.anova_regressao
    if reg is not None and "C2" in sel:
        titulo_com_ajuda("ANOVA da regressão", "anova", "ea-tabela-rotulo")
        _tabela_anova(reg.linhas)
        if reg.razao_f is not None and reg.f_tabelado is not None:
            leitura = (
                "maior que 1: a regressão é significativa"
                if reg.regressao_significativa
                else "menor que 1: a regressão não é significativa"
            )
            ui.html(
                '<div class="ea-ler">F calculado / F tabelado = '
                f"<b>{_fmt(reg.razao_f, 2)}</b> (F tabelado = "
                f"{_fmt(reg.f_tabelado, 2)} a α = {_fmt(alfa, 2)}), {leitura}.</div>"
            )
    if "C2" in sel:
        if ajuste.anova:
            titulo_com_ajuda(
                "Efeito de cada termo (ANOVA Tipo II)",
                "anova_tipo2",
                "ea-tabela-rotulo",
            )
            _tabela_anova(ajuste.anova)
        else:
            ui.html(
                '<div class="ea-ler">ANOVA Tipo II indisponível para este modelo.'
                "</div>"
            )
    if "C4" in sel:
        ui.html(f'<div class="ea-falta">{escape(_texto_falta(ajuste))}</div>')


def _aba_diagnostico(
    ajuste: AjusteResposta, alfa: float, sel: frozenset[str] = frozenset(IDS)
) -> None:
    d = ajuste.diagnostico
    if d is None:
        ui.html(
            '<div class="ea-ler">Este resultado não traz os valores por ensaio.'
            "</div>"
        )
        return

    if "C6" in sel:
        titulo_com_ajuda("Previsto × observado", "previsto_observado")
        _grafico(
            graficos.opcoes_preditos_observados(ajuste),
            300,
            "Previsto contra observado, um ponto por ensaio, com a reta y = x.",
        )
        ui.html(
            '<div class="ea-ler">Ponto sobre a linha <b>y = x</b> é ensaio que o '
            "modelo acerta; quanto mais longe da linha, maior o erro naquele "
            "ensaio.</div>"
        )

    if "D1" in sel:
        titulo_com_ajuda("Resíduos × previsto", "residuos_previsto")
        _grafico(
            graficos.opcoes_residuos_preditos(ajuste),
            280,
            "Resíduos contra o valor previsto, um ponto por ensaio.",
        )
        ui.html(
            '<div class="ea-ler">Os pontos devem se espalhar ao acaso em torno do '
            "zero. Funil, curva ou tendência indicam algo que o modelo deixou de "
            "fora.</div>"
        )

    if d.ordem is not None and "D3" in sel:
        titulo_com_ajuda("Resíduos × ordem de execução", "residuos_ordem")
        _grafico(
            graficos.opcoes_residuos_ordem(ajuste),
            260,
            "Resíduos na ordem de execução dos ensaios.",
        )
        ui.html(
            '<div class="ea-ler">Na ordem em que os ensaios foram feitos, os resíduos '
            "não devem subir ou descer aos poucos: tendência indica deriva do "
            "equipamento, do reagente ou do operador ao longo do tempo.</div>"
        )

    if "D2" in sel:
        titulo_com_ajuda("Normalidade dos resíduos (Q-Q)", "qq")
        _grafico(
            graficos.opcoes_qq(pontos_qq(d.residuos)),
            280,
            "Gráfico Q-Q normal dos resíduos. "
            + _sem_html(_texto_normalidade(ajuste, alfa)),
        )
        ui.html(f'<div class="ea-ler">{_texto_normalidade(ajuste, alfa)}</div>')

    if "D4" in sel:
        ui.html(f'<div class="ea-ler">{_texto_influencia(d)}</div>')
    ui.html('<div class="ea-tabela-rotulo">Valores por ensaio</div>')
    colunas = [
        {"name": "n", "label": "Ensaio", "field": "n", "align": "left"},
        {"name": "obs", "label": "Observado", "field": "obs", "align": "right"},
        {"name": "prev", "label": "Previsto", "field": "prev", "align": "right"},
        {"name": "res", "label": "Resíduo", "field": "res", "align": "right"},
        {"name": "h", "label": "Alavancagem", "field": "h", "align": "right"},
        {"name": "r", "label": "Res. studentizado", "field": "r", "align": "right"},
        {"name": "cook", "label": "Cook", "field": "cook", "align": "right"},
        {"name": "nota", "label": "", "field": "nota", "align": "left"},
    ]

    def coluna(valores: Sequence[float | None], i: int, casas: int = 3) -> str:
        return _fmt(valores[i], casas) if i < len(valores) else "—"

    linhas = [
        {
            "n": i + 1,
            "obs": _fmt(o, 3),
            "prev": _fmt(p, 3),
            "res": _fmt(r, 3),
            "h": coluna(d.alavancagem, i),
            "r": coluna(d.residuos_studentizados, i, 2),
            "cook": coluna(d.distancia_cook, i),
            "nota": ", ".join(
                rotulo
                for rotulo, lista in (
                    ("influente", d.ensaios_influentes),
                    ("possível outlier", d.possiveis_outliers),
                )
                if i + 1 in lista
            ),
        }
        for i, (o, p, r) in enumerate(
            zip(d.observados, d.preditos, d.residuos, strict=True)
        )
    ]
    ui.table(
        columns=colunas, rows=linhas, row_key="n", pagination={"rowsPerPage": 10}
    ).props("flat bordered dense").classes("ensaia-previa w-full")


def _texto_influencia(d: Diagnostico) -> str:
    if not d.alavancagem:
        return ""
    partes = []
    if d.ensaios_influentes:
        lista = ", ".join(str(i) for i in d.ensaios_influentes)
        partes.append(
            f"<b>Ensaio(s) influente(s): {lista}</b> (distância de Cook &gt; 1 e "
            "alavancagem alta): sozinhos, mudam bastante o ajuste; confira se não "
            "houve erro de anotação ou de execução."
        )
    if d.possiveis_outliers:
        lista = ", ".join(str(i) for i in d.possiveis_outliers)
        partes.append(
            f"<b>Possível(is) outlier(s): {lista}</b> (resíduo studentizado "
            "externo acima de 3 em módulo): o valor destoa do que o modelo prevê."
        )
    if not partes:
        return (
            "Nenhum ensaio influente nem possível outlier: nenhum ponto sozinho "
            "está puxando o modelo."
        )
    return " ".join(partes)


def _sem_html(texto: str) -> str:
    """Texto puro a partir de um trecho de HTML curto (para o aria-label)."""
    return unescape(re.sub(r"<[^>]+>", "", texto))


def _texto_normalidade(ajuste: AjusteResposta, alfa: float) -> str:
    d = ajuste.diagnostico
    if d is None or d.shapiro_p is None:
        motivo = (d.motivo_sem_shapiro if d else None) or "dados insuficientes"
        return f"Teste de Shapiro-Wilk não aplicável ({escape(motivo)})."
    teste = (
        f"Shapiro-Wilk: W = {_fmt(d.shapiro_w, 3)}, p = {_fmt_p(d.shapiro_p)}. "
    )
    if d.normalidade_rejeitada:
        return teste + (
            f"<b>Há indício de que os resíduos não são normais</b> (p &lt; "
            f"{_fmt(alfa, 2)}): leia os valores-p do modelo com cautela."
        )
    return teste + (
        "Sem evidência contra a normalidade: pontos perto da reta, como esperado."
    )


class _PainelSuperficie:
    """Contorno e superfície 3D de uma resposta, com eixos e fatores fixos ajustáveis.

    A grade vem sempre de `core.surface.grade_superficie`; aqui só se escolhe o
    par de eixos, o valor dos demais fatores e a forma (contorno ou 3D). O 3D
    carrega a echarts-gl só quando pedido (spec RNF-11: primeira carga leve).
    """

    def __init__(
        self,
        ajuste: AjusteResposta,
        fatores: list[Fator],
        sel: frozenset[str] = frozenset(IDS),
    ) -> None:
        self.ajuste = ajuste
        self.fatores = fatores
        candidatas = (("contorno", "Contorno", "E2"), ("3d", "3D", "E1"))
        formas = {chave: rotulo for chave, rotulo, id_ in candidatas if id_ in sel} or {
            "contorno": "Contorno"
        }
        self.fixos: dict[str, float] = {f.nome: f.centro for f in fatores}
        nomes = [f.nome for f in fatores]
        x, y = par_inicial(ajuste, nomes)
        self._eixos: tuple[str, str] = (x, y)
        self._sincronizando = False
        opcoes = {n: nome_legivel(n) for n in nomes}

        with ui.element("div").classes("ea-controles"):
            self.sel_x = ui.select(opcoes, value=x, label="Eixo horizontal").props(
                "dense outlined"
            )
            self.sel_y = ui.select(opcoes, value=y, label="Eixo vertical").props(
                "dense outlined"
            )
            self.forma = (
                ui.toggle(formas, value=next(iter(formas)))
                .props(
                    "no-caps unelevated dense color=white text-color=primary "
                    "toggle-color=primary toggle-text-color=white"
                )
                .classes("ea-forma")
            )
            ajuda("superficie")
        if len(formas) == 1:
            self.forma.set_visibility(False)  # só uma forma marcada: sem escolha
        self.estacionario = ajuste.ponto_estacionario if "E3" in sel else None
        if self.estacionario is not None:
            self._linha_estacionario()
        self.area_fixos = ui.element("div").classes("ea-controles")
        self.area_grafico = ui.column().classes("w-full")
        self.ler = ui.html("").classes("ea-ler")
        self.grafico: ui.echart | None = None

        self.sel_x.on_value_change(lambda e: self._trocar_eixo("x", e.value))
        self.sel_y.on_value_change(lambda e: self._trocar_eixo("y", e.value))
        self.forma.on_value_change(lambda _: self._redesenhar(recriar=True))
        self._montar_fixos()
        self._redesenhar(recriar=True)

    def _linha_estacionario(self) -> None:
        pe = self.estacionario
        assert pe is not None
        natureza = {"maximo": "máximo", "minimo": "mínimo", "sela": "ponto de sela"}
        onde = (
            "dentro da região estudada"
            if pe.dentro_da_regiao
            else "fora da região estudada (não extrapole o modelo até lá)"
        )
        coords = ", ".join(
            f"{nome_legivel(n)} = {_fmt_curto(v)}" for n, v in pe.real.items()
        )
        with ui.element("div").classes("ea-estacionario"):
            ui.html(
                f'<div class="ea-ler">Ponto estacionário: <b>{natureza[pe.natureza]}'
                f"</b> em {escape(coords)}, {onde}; resposta prevista "
                f"{_fmt(pe.resposta_prevista, 3)}.</div>"
            )
            if pe.dentro_da_regiao:
                ui.button(
                    "Ver este ponto na superfície", on_click=self._ir_ao_estacionario
                ).props("flat dense").classes("ea-botao-sec")

    def _ir_ao_estacionario(self) -> None:
        """Fixa os demais fatores no ponto estacionário e o marca no contorno."""
        pe = self.estacionario
        assert pe is not None
        self.fixos.update(pe.real)
        self._montar_fixos()
        self._redesenhar(recriar=self.forma.value == "3d")

    def _destaque(self) -> tuple[float, float, str] | None:
        """Ponto a marcar no contorno: só quando o corte passa por ele."""
        pe = self.estacionario
        if pe is None or not pe.dentro_da_regiao:
            return None
        x, y = self._eixos
        por_nome = {f.nome: f for f in self.fatores}
        for nome, valor in pe.real.items():
            if nome in (x, y):
                continue
            tolerancia = 1e-6 * (por_nome[nome].amplitude or 1.0)
            if abs(self.fixos.get(nome, float("nan")) - valor) > tolerancia:
                return None
        rotulo = {"maximo": "máximo", "minimo": "mínimo", "sela": "sela"}[pe.natureza]
        return pe.real[x], pe.real[y], rotulo

    # -- interação ---------------------------------------------------------
    def focar(self, envolvidos: list[str]) -> None:
        """Põe nos eixos os fatores de um termo clicado no Pareto."""
        nomes = [f.nome for f in self.fatores]
        par = [n for n in envolvidos if n in nomes][:2]
        if len(par) == 1:  # termo de um fator só: completa com o outro mais forte
            outros = [n for n in ordem_por_forca(self.ajuste, nomes) if n != par[0]]
            par.append(outros[0])
        if len(par) < 2:
            return
        self._definir_eixos(par[0], par[1])

    def _trocar_eixo(self, qual: str, valor: str) -> None:
        if self._sincronizando:  # mudança feita por código, não pelo usuário
            return
        antigo_x, antigo_y = self._eixos
        if qual == "x":
            # Mesmo fator nos dois eixos: o vertical herda o antigo horizontal.
            x, y = valor, (antigo_x if valor == antigo_y else antigo_y)
        else:
            x, y = (antigo_y if valor == antigo_x else antigo_x), valor
        self._definir_eixos(x, y)

    def _definir_eixos(self, x: str, y: str) -> None:
        if (x, y) == self._eixos and (self.sel_x.value, self.sel_y.value) == (x, y):
            return
        self._eixos = (x, y)
        self._sincronizando = True
        try:
            self.sel_x.set_value(x)
            self.sel_y.set_value(y)
        finally:
            self._sincronizando = False
        self._montar_fixos()
        self._redesenhar(recriar=False)

    # -- montagem ----------------------------------------------------------
    def _montar_fixos(self) -> None:
        self.area_fixos.clear()
        with self.area_fixos:
            for fator in self.fatores:
                if fator.nome in self._eixos:
                    continue
                self._controle_fixo(fator)

    def _controle_fixo(self, fator: Fator) -> None:
        with ui.element("div").classes("ea-fixo"):
            rotulo = ui.html("").classes("ea-fixo-rotulo")

            def atualizar_rotulo(valor: float) -> None:
                rotulo.set_content(
                    f"{escape(nome_legivel(fator.nome))} fixo em "
                    f"<b>{_fmt_curto(valor)}</b>"
                )

            atualizar_rotulo(self.fixos[fator.nome])
            passo = (fator.maximo - fator.minimo) / 40 or 1.0
            controle = ui.slider(
                min=fator.minimo, max=fator.maximo, step=passo,
                value=self.fixos[fator.nome],
            ).props("color=primary")
            controle.on_value_change(lambda e: atualizar_rotulo(float(e.value)))

            def soltar(evento: object) -> None:
                valor = getattr(evento, "args", None)
                self.fixos[fator.nome] = float(
                    valor if isinstance(valor, int | float) else controle.value
                )
                self._redesenhar(recriar=False)

            # Redesenha ao soltar (evento "change" do QSlider), não a cada pixel.
            controle.on("change", soltar)

    def _redesenhar(self, *, recriar: bool) -> None:
        x, y = self._eixos
        fixos = {n: v for n, v in self.fixos.items() if n not in (x, y)}
        tres_d = self.forma.value == "3d"
        # Contorno com grade mais fina: em 25 × 25 as faixas saem em degraus
        # visíveis. O 3D fica nos 25 × 25 da spec (§7.3), que já é liso ali.
        grade = grade_superficie(
            self.ajuste,
            self.fatores,
            x,
            y,
            fixos=fixos,
            pontos=PONTOS_PADRAO if tres_d else _PONTOS_CONTORNO,
        )
        opcoes = (
            graficos.opcoes_superficie_3d(grade) if tres_d
            else graficos.opcoes_contorno(grade, destaque=self._destaque())
        )
        descricao = (
            f"{'Superfície 3D' if tres_d else 'Curvas de contorno'} de "
            f"{nome_legivel(self.ajuste.resposta)} prevista em função de "
            f"{nome_legivel(x)} e {nome_legivel(y)}."
        )
        if recriar or self.grafico is None:
            self.area_grafico.clear()
            with self.area_grafico:
                self.grafico = _grafico(opcoes, 400 if tres_d else 380, descricao)
        else:
            self.grafico.options.clear()
            self.grafico.options.update(opcoes)
            self.grafico.props["aria-label"] = descricao
            self.grafico.update()

        fixos_txt = ", ".join(
            f"{escape(nome_legivel(n))} = {_fmt_curto(v)}"
            for n, v in grade.fixos.items()
        )
        sufixo = f" Fixos: {fixos_txt}." if fixos_txt else ""
        if tres_d:
            self.ler.set_content(
                "Arraste para girar e role para aproximar. Mesma escala de cor do "
                f"contorno: mais escuro, maior a resposta prevista.{sufixo}"
            )
        else:
            self.ler.set_content(
                "Cada faixa de cor é uma curva de nível da resposta prevista pelo "
                f"modelo: <b>quanto mais escuro, maior</b>.{sufixo}"
            )


def _fmt_curto(valor: float) -> str:
    """Número pt-BR sem zeros sobrando: 7 → "7"; 0,625 → "0,625"; 37,5 → "37,5"."""
    texto = f"{valor:.4f}".rstrip("0").rstrip(".")
    return "0" if texto in ("-0", "") else texto.replace(".", ",")


def _fmt_p(valor: float | None) -> str:
    """p-valor para texto em HTML (o "<" vai escapado)."""
    return escape(_fmt_p_tabela(valor))


def _fmt_p_tabela(valor: float | None) -> str:
    """p-valor em texto puro (célula de tabela): '< 0,0001' em vez de '0,0000'."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    if valor < 0.0001:
        return "< 0,0001"
    return _fmt(valor, 4)


def _tabela_coeficientes(ajuste: AjusteResposta) -> None:
    colunas = [
        {"name": "termo", "label": "Termo", "field": "termo", "align": "left"},
        {"name": "est", "label": "Estimativa", "field": "est", "align": "right"},
        {"name": "ep", "label": "Erro padrão", "field": "ep", "align": "right"},
        {"name": "t", "label": "t", "field": "t", "align": "right"},
        {"name": "p", "label": "p-valor", "field": "p", "align": "right"},
        {"name": "sig", "label": "Signif.", "field": "sig", "align": "center"},
    ]
    linhas = [
        {
            "termo": nome_legivel(c.termo),
            "est": _fmt(c.estimativa, 4),
            "ep": _fmt(c.erro_padrao, 4),
            "t": _fmt(c.valor_t, 2),
            "p": _fmt_p_tabela(c.valor_p),
            "sig": "sim" if c.significativo else "—",
        }
        for c in ajuste.coeficientes
    ]
    ui.table(columns=colunas, rows=linhas, row_key="termo").props(
        "flat bordered dense"
    ).classes("ensaia-previa w-full")


def _tabela_anova(linhas_anova: list[LinhaAnova]) -> None:
    colunas = [
        {"name": "fonte", "label": "Fonte", "field": "fonte", "align": "left"},
        {"name": "sq", "label": "SQ", "field": "sq", "align": "right"},
        {"name": "gl", "label": "GL", "field": "gl", "align": "right"},
        {"name": "qm", "label": "QM", "field": "qm", "align": "right"},
        {"name": "f", "label": "F", "field": "f", "align": "right"},
        {"name": "p", "label": "p-valor", "field": "p", "align": "right"},
    ]
    linhas = [
        {
            "fonte": nome_legivel(linha.fonte),
            "sq": _fmt(linha.soma_quadrados, 3),
            "gl": str(linha.graus_liberdade),
            "qm": _fmt(linha.quadrado_medio, 3),
            "f": _fmt(linha.valor_f, 2),
            "p": _fmt_p_tabela(linha.valor_p),
        }
        for linha in linhas_anova
    ]
    ui.table(columns=colunas, rows=linhas, row_key="fonte").props(
        "flat bordered dense"
    ).classes("ensaia-previa w-full")


def _texto_falta(ajuste: AjusteResposta) -> str:
    falta = ajuste.falta_de_ajuste
    if not falta.aplicavel:
        motivo = falta.motivo_inaplicavel or "não há réplicas genuínas no delineamento"
        return f"Teste de falta de ajuste: não aplicável ({motivo.rstrip('.')})."
    if falta.significativa:
        return (
            f"Há evidência de falta de ajuste (p = {_fmt(falta.valor_p, 4)}): "
            "o modelo pode não descrever bem os dados."
        )
    return f"Sem evidência de falta de ajuste (p = {_fmt(falta.valor_p, 4)})."


def _fmt(valor: object, casas: int = 4) -> str:
    """Número no padrão brasileiro (vírgula decimal) ou '—' quando ausente."""
    if valor is None:
        return "—"
    try:
        f = float(valor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(valor)
    if math.isnan(f):
        return "—"
    return f"{f:.{casas}f}".replace(".", ",")
