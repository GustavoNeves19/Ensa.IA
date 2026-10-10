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
from html import escape
from typing import Any, cast

from nicegui import run, ui
from nicegui.events import EChartPointClickEventArguments

from ensaia import __version__
from ensaia.ai.report import gerar_relatorio
from ensaia.core.catalogo import CATALOGO, GRUPOS, IDS, disponibilidade
from ensaia.core.descritiva import matriz_codificada
from ensaia.core.design import (
    INTERCEPTO,
    Fator,
    Planejamento,
    interpretar_termo,
)
from ensaia.core.desirability import metas_padrao, otimizar
from ensaia.core.diagnostico import pontos_qq
from ensaia.core.fatorial import pontos_meio_normal
from ensaia.core.identificacao import identificar_planejamento
from ensaia.core.pipeline import analisar, limite_da_regiao
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
from ensaia.core.surface import PONTOS_PADRAO, grade_superficie, prever_condicao
from ensaia.core.table import Table
from ensaia.core.termos import NOME_MODELO, escolher_termos, termos_do_tipo
from ensaia.ui import graficos
from ensaia.ui.graficos import nome_legivel
from ensaia.ui.narrar import construir_narracao
from ensaia.ui.sessao import Sessao

# Nomes usuais da coluna de ordem/número do ensaio (spec §8.3).
_NOME_ORDEM = re.compile(
    r"^(ensaio|ensaios|exp|experimento|run|ordem|corrida|n|n[º°o.]?)\b", re.IGNORECASE
)

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


def construir_analise(tabela: Table) -> None:
    """Monta o fluxo mapear → analisar → resultados para a `Table` carregada."""
    numericas = [c for c in tabela.colunas if tabela.e_numerica(c)]
    ultima_resposta = numericas[-1] if numericas else None
    selects: dict[str, ui.select] = {}

    with ui.element("div").classes("ea-mapear"):
        ui.html('<div class="ea-secao-titulo">Mapear colunas</div>')
        ui.html(
            '<div class="ea-secao-sub">Diga o que é <b>fator</b> (o que você '
            "controla) e o que é <b>resposta</b> (o que você mede). Se a planilha "
            "tem a ordem em que os ensaios foram feitos, marque como <b>ordem</b>. "
            "O resto é ignorado.</div>"
        )
        with ui.element("div").classes("ea-mapa-grade"):
            for coluna in tabela.colunas:
                numerica = tabela.e_numerica(coluna)
                if not numerica:
                    padrao = "Ignorar"
                elif _parece_ordem(coluna, tabela):
                    padrao = "Ordem"
                elif coluna == ultima_resposta:
                    padrao = "Resposta"
                else:
                    padrao = "Fator"
                with ui.element("div").classes("ea-mapa-item"):
                    ui.html(f'<div class="ea-col-nome">{escape(coluna)}</div>')
                    sel = (
                        ui.select(
                            ["Fator", "Resposta", "Ordem", "Ignorar"], value=padrao
                        )
                        .props("dense outlined")
                        .classes("ea-col-sel")
                    )
                    if not numerica:
                        sel.disable()  # coluna de texto só pode ser ignorada
                    selects[coluna] = sel

    painel_analises = _PainelAnalises(tabela, selects)
    opcoes = _Opcoes()
    _painel_opcoes(opcoes)

    def analisar_e_mostrar() -> None:
        fatores = [c for c, s in selects.items() if s.value == "Fator"]
        respostas = [c for c, s in selects.items() if s.value == "Resposta"]
        ordens = [c for c, s in selects.items() if s.value == "Ordem"]
        if len(ordens) > 1:
            ui.notify(
                f"Só uma coluna pode ser a ordem; usando {ordens[0]!r}.",
                type="warning",
            )
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
                analise, planejamento, candidatos, opcoes, analisar_e_mostrar, tabela
            )

    def ao_analisar() -> None:
        opcoes.excluidos.clear()  # nova análise parte do modelo completo
        analisar_e_mostrar()

    ui.button("Analisar", on_click=ao_analisar).props("unelevated").classes("ea-botao")
    # Os resultados aparecem ABAIXO do botão, na ordem de leitura.
    resultado = ui.column().classes("w-full ea-slot")


class _PainelAnalises:
    """As caixas de seleção das análises, agrupadas como na spec (§9).

    A disponibilidade depende do mapeamento (quantos fatores, se há ordem, se há
    réplicas…), então é recalculada a cada mudança nele. Compatíveis vêm
    marcadas; incompatíveis ficam desabilitadas com o motivo no tooltip.
    """

    def __init__(self, tabela: Table, selects: dict[str, ui.select]) -> None:
        self.tabela = tabela
        self.selects = selects
        self.caixas: dict[str, ui.checkbox] = {}
        self.dicas: dict[str, ui.tooltip] = {}
        self.expansao = (
            ui.expansion("Análises").classes("ea-opcoes w-full").props(
                "dense switch-toggle-side"
            )
        )
        with self.expansao:
            ui.html(
                '<div class="ea-ler">As compatíveis com os seus dados já vêm '
                "marcadas; as cinzas não se aplicam (passe o mouse para ver o "
                "motivo). O que ficar desmarcado sai da tela e do PDF.</div>"
            )
            with ui.element("div").classes("ea-grupos"):
                for grupo, titulo in GRUPOS.items():
                    with ui.element("div").classes("ea-grupo"):
                        ui.html(f'<div class="ea-grupo-titulo">{escape(titulo)}</div>')
                        for analise in (a for a in CATALOGO if a.grupo == grupo):
                            caixa = ui.checkbox(f"{analise.id} · {analise.nome}").props(
                                "dense"
                            )
                            with caixa:
                                self.dicas[analise.id] = ui.tooltip("")
                            caixa.on_value_change(lambda _: self._rotular())
                            self.caixas[analise.id] = caixa
        for sel in selects.values():
            sel.on_value_change(lambda _: self.atualizar())
        self.atualizar()

    def _colunas(self, papel: str) -> list[str]:
        return [c for c, s in self.selects.items() if s.value == papel]

    def atualizar(self) -> None:
        fatores = {
            c: [float(v) for v in self.tabela.coluna(c)] for c in self._colunas("Fator")
        }
        disponivel = disponibilidade(
            fatores,
            n_respostas=len(self._colunas("Resposta")),
            tem_ordem=bool(self._colunas("Ordem")),
        )
        for id_, motivo in disponivel.items():
            caixa = self.caixas[id_]
            caixa.set_value(motivo is None)
            if motivo is None:
                caixa.enable()
                self.dicas[id_].set_text("Compatível com os seus dados.")
            else:
                caixa.disable()
                self.dicas[id_].set_text(f"Não se aplica: {motivo}.")
        self._rotular()

    def _rotular(self) -> None:
        marcadas = len(self.marcadas())
        habilitadas = sum(1 for c in self.caixas.values() if c.enabled)
        self.expansao.props(f'label="Análises ({marcadas} de {habilitadas} marcadas)"')

    def marcadas(self) -> list[str]:
        return [id_ for id_, c in self.caixas.items() if c.value and c.enabled]


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


def _parece_ordem(coluna: str, tabela: Table) -> bool:
    """Coluna 1..n com nome de ensaio/ordem vira Ordem por padrão (spec §8.3)."""
    if not _NOME_ORDEM.match(coluna.strip()):
        return False
    valores = sorted(float(v) for v in tabela.coluna(coluna))
    return valores == [float(i) for i in range(1, len(valores) + 1)]


def _rodar_analise(
    tabela: Table,
    fatores: list[str],
    respostas: list[str],
    opcoes: _Opcoes,
    coluna_ordem: str | None = None,
    analises: list[str] | None = None,
) -> tuple[AnalysisResult, Planejamento, list[str]]:
    """Reconhece o planejamento, escolhe os termos e roda o núcleo.

    Devolve também o `Planejamento` (a superfície precisa das faixas dos fatores)
    e os termos candidatos do modelo, para o usuário escolher o que excluir.
    """
    identificacao = identificar_planejamento(
        {nome: [float(v) for v in tabela.coluna(nome)] for nome in fatores}
    )
    planejamento = identificacao.planejamento
    pedido = None if opcoes.tipo_modelo == "auto" else opcoes.tipo_modelo
    selecao = escolher_termos(
        tabela,
        planejamento,
        tipo_modelo=cast(TipoModelo | None, pedido),
        excluidos=opcoes.excluidos,
    )
    niveis = {f.fator.nome: len(f.niveis) for f in identificacao.fatores}
    candidatos = [
        t for t in termos_do_tipo(niveis, selecao.tipo_modelo) if t != INTERCEPTO
    ]
    analise = analisar(
        tabela,
        planejamento,
        selecao.termos,
        respostas,
        versao_ensaia=__version__,
        alfa=opcoes.alfa,
        termo_erro=cast(TermoErro, opcoes.termo_erro),
        reduzir=opcoes.reduzir,
        tipo_modelo=selecao.tipo_modelo,
        avisos_planejamento=[*identificacao.avisos, *selecao.avisos],
        coluna_ordem=coluna_ordem,
        analises=analises,
    )
    return analise, planejamento, candidatos


def _mostrar_resultados(
    analise: AnalysisResult,
    planejamento: Planejamento,
    candidatos: list[str],
    opcoes: _Opcoes,
    reanalisar: Callable[[], None],
    tabela: Table,
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
            if "C3" in sel:
                r2 = (
                    f"R² = <b>{_fmt(ajuste.r2, 3)}</b> · "
                    f"R² ajustado = <b>{_fmt(ajuste.r2_ajustado, 3)}</b>"
                )
                if ajuste.r2_predicao is not None:
                    r2 += f" · R² de predição = <b>{_fmt(ajuste.r2_predicao, 3)}</b>"
                ui.html(f'<div class="ea-r2">{r2}</div>')
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

    sessao = Sessao(analise)
    if sel & {"E4", "E5"}:
        _bloco_otimizacao(sessao, planejamento)
    if "C1" in sel:
        _bloco_prever(analise, planejamento)

    construir_narracao(sessao)
    _bloco_baixar(sessao)


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
            ui.html('<div class="ea-tabela-rotulo">Estatística descritiva</div>')
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
        ui.html(
            '<div class="ea-tabela-rotulo">Matriz do planejamento '
            "(real e, entre parênteses, codificado)</div>"
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
        ui.html('<div class="ea-secao-titulo">Melhor condição</div>')
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
            gerar_pdf, analise, texto, gerado_em=agora.strftime("%d/%m/%Y %H:%M")
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
    on_point_click: Callable[[EChartPointClickEventArguments], None] | None = None,
) -> ui.echart:
    return (
        ui.echart(opcoes, on_point_click=on_point_click)
        .classes("ea-grafico")
        .style(f"height:{altura}px")
    )


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
        ui.html('<div class="ea-tabela-rotulo">Coeficientes (escala codificada)</div>')
        _tabela_coeficientes(ajuste)
    if "C5" in sel:
        _equacao(ajuste)


def _pareto(
    ajuste: AjusteResposta, alfa: float, ao_clicar: Callable[[str], None] | None
) -> None:
    ui.html('<div class="ea-grafico-titulo">Pareto dos efeitos padronizados</div>')

    def clique(evento: EChartPointClickEventArguments) -> None:
        if ao_clicar and isinstance(evento.data, dict) and evento.data.get("termo"):
            ao_clicar(str(evento.data["termo"]))

    _grafico(
        graficos.opcoes_pareto(ajuste, alfa=alfa),
        graficos.altura_pareto(ajuste),
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
    ui.html('<div class="ea-tabela-rotulo">Efeitos (de −1 a +1)</div>')
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
    ui.html('<div class="ea-grafico-titulo">Gráfico meio-normal dos efeitos</div>')
    _grafico(
        graficos.opcoes_meio_normal(
            pontos_meio_normal(ef.efeitos), ef.lenth.me, ativos
        ),
        300,
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
    ui.html('<div class="ea-grafico-titulo">Efeitos principais</div>')
    with ui.element("div").classes("ea-multiplos"):
        for m in ef.medias_principais:
            _grafico(graficos.opcoes_medias(m, baixo - folga, alto + folga), 200)
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
    ui.html(
        '<div class="ea-grafico-titulo">Interação '
        f"{escape(nome_legivel(mais_forte.fator_a))} × "
        f"{escape(nome_legivel(mais_forte.fator_b))}</div>"
    )
    _grafico(graficos.opcoes_interacao(mais_forte), 280)
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
    ui.html('<div class="ea-tabela-rotulo">Equação do modelo</div>')
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
        ui.html('<div class="ea-tabela-rotulo">ANOVA da regressão</div>')
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
            ui.html(
                '<div class="ea-tabela-rotulo">Efeito de cada termo '
                "(ANOVA Tipo II)</div>"
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
        ui.html('<div class="ea-grafico-titulo">Previsto × observado</div>')
        _grafico(graficos.opcoes_preditos_observados(ajuste), 300)
        ui.html(
            '<div class="ea-ler">Ponto sobre a linha <b>y = x</b> é ensaio que o '
            "modelo acerta; quanto mais longe da linha, maior o erro naquele "
            "ensaio.</div>"
        )

    if "D1" in sel:
        ui.html('<div class="ea-grafico-titulo">Resíduos × previsto</div>')
        _grafico(graficos.opcoes_residuos_preditos(ajuste), 280)
        ui.html(
            '<div class="ea-ler">Os pontos devem se espalhar ao acaso em torno do '
            "zero. Funil, curva ou tendência indicam algo que o modelo deixou de "
            "fora.</div>"
        )

    if d.ordem is not None and "D3" in sel:
        ui.html('<div class="ea-grafico-titulo">Resíduos × ordem de execução</div>')
        _grafico(graficos.opcoes_residuos_ordem(ajuste), 260)
        ui.html(
            '<div class="ea-ler">Na ordem em que os ensaios foram feitos, os resíduos '
            "não devem subir ou descer aos poucos: tendência indica deriva do "
            "equipamento, do reagente ou do operador ao longo do tempo.</div>"
        )

    if "D2" in sel:
        ui.html('<div class="ea-grafico-titulo">Normalidade dos resíduos (Q-Q)</div>')
        _grafico(graficos.opcoes_qq(pontos_qq(d.residuos)), 280)
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
        x, y = _par_inicial(ajuste, nomes)
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
            outros = [n for n in _ordem_por_forca(self.ajuste, nomes) if n != par[0]]
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
        if recriar or self.grafico is None:
            self.area_grafico.clear()
            with self.area_grafico:
                self.grafico = _grafico(opcoes, 400 if tres_d else 380)
        else:
            self.grafico.options.clear()
            self.grafico.options.update(opcoes)
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


def _ordem_por_forca(ajuste: AjusteResposta, nomes: list[str]) -> list[str]:
    """Fatores do mais ao menos influente, pelo maior |t| entre os termos de cada um."""
    forca = dict.fromkeys(nomes, 0.0)
    for c in ajuste.coeficientes:
        if c.termo == INTERCEPTO:
            continue
        for nome, _ in interpretar_termo(c.termo):
            if nome in forca:
                forca[nome] = max(forca[nome], abs(c.valor_t))
    return sorted(nomes, key=lambda n: forca[n], reverse=True)


def _par_inicial(ajuste: AjusteResposta, nomes: list[str]) -> tuple[str, str]:
    """Par de eixos de abertura: a interação mais forte ou os 2 fatores mais fortes."""
    interacoes = [
        c for c in ajuste.coeficientes
        if len({n for n, _ in interpretar_termo(c.termo)}) == 2
    ]
    if interacoes:
        melhor = max(interacoes, key=lambda c: abs(c.valor_t))
        a, b = list(dict.fromkeys(n for n, _ in interpretar_termo(melhor.termo)))
        return a, b
    ordem = _ordem_por_forca(ajuste, nomes)
    return ordem[0], ordem[1]


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
