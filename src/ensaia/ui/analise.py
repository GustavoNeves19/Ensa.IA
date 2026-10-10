"""Passos 3 e 4 do fluxo (spec §4): mapear colunas, analisar e mostrar o laudo.

Depois que `ui/upload.py` lê a planilha numa `Table`, esta tela:

1. **Mapear** — para cada coluna, o usuário diz se é fator (entrada), resposta
   (saída) ou se deve ser ignorada. O padrão é inteligente: colunas numéricas
   viram fatores, a última numérica vira resposta, texto é ignorado.
2. **Analisar** — monta o delineamento a partir dos próprios dados (faixas dos
   fatores pelo mín/máx, tipo inferido por `detectar_tipo`, termos do modelo
   escolhidos conforme o tipo) e roda o núcleo determinístico (`core.pipeline`).
3. **Mostrar** — por resposta, abas Efeitos (Pareto + coeficientes), ANOVA,
   Diagnóstico (preditos × observados, resíduos, Q-Q) e Superfície (contorno e
   3D com os demais fatores ajustáveis). Cada aba só é montada quando aberta
   (spec §7.3: a NiceGUI guarda no servidor a árvore de cada aba aberta).
4. **Relatório** — em texto fiel (modo M0, offline) ou narrado por IA (modo M3,
   com a chave da OpenAI lida do `.env`). A IA roda fora da thread da interface
   (`run.io_bound`) para a tela não congelar enquanto o modelo responde.

Nada é calculado aqui: a conta é toda do núcleo; esta camada só coleta escolhas,
chama o pipeline e desenha o resultado.
"""

from __future__ import annotations

import math
import os
from collections.abc import Callable
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from nicegui import run, ui
from nicegui.events import EChartPointClickEventArguments

from ensaia import __version__
from ensaia.ai.client import ClienteModelo, ConfiguracaoModelo, ErroDeIA
from ensaia.ai.report import RelatorioTextual, gerar_relatorio
from ensaia.core.design import (
    INTERCEPTO,
    Fator,
    Planejamento,
    detectar_tipo,
    interpretar_termo,
    termos_do_modelo,
)
from ensaia.core.diagnostico import pontos_qq
from ensaia.core.pipeline import analisar
from ensaia.core.results import AjusteResposta, AnalysisResult
from ensaia.core.surface import PONTOS_PADRAO, grade_superficie
from ensaia.core.table import Table
from ensaia.ui import graficos
from ensaia.ui.graficos import nome_legivel

_TIPO_LEGIVEL = {
    "fatorial_completo": "fatorial completo",
    "fatorial_fracionado": "fatorial fracionado",
    "composto_central": "composto central",
    "box_behnken": "Box-Behnken",
    "desconhecido": "não identificado",
}


def construir_analise(tabela: Table) -> None:
    """Monta o fluxo mapear → analisar → resultados para a `Table` carregada."""
    numericas = [c for c in tabela.colunas if tabela.e_numerica(c)]
    ultima_resposta = numericas[-1] if numericas else None
    selects: dict[str, ui.select] = {}

    with ui.element("div").classes("ea-mapear"):
        ui.html('<div class="ea-secao-titulo">Mapear colunas</div>')
        ui.html(
            '<div class="ea-secao-sub">Diga o que é <b>fator</b> (o que você '
            "controla) e o que é <b>resposta</b> (o que você mede). O resto é "
            "ignorado.</div>"
        )
        with ui.element("div").classes("ea-mapa-grade"):
            for coluna in tabela.colunas:
                numerica = tabela.e_numerica(coluna)
                if not numerica:
                    padrao = "Ignorar"
                elif coluna == ultima_resposta:
                    padrao = "Resposta"
                else:
                    padrao = "Fator"
                with ui.element("div").classes("ea-mapa-item"):
                    ui.html(f'<div class="ea-col-nome">{escape(coluna)}</div>')
                    sel = (
                        ui.select(["Fator", "Resposta", "Ignorar"], value=padrao)
                        .props("dense outlined")
                        .classes("ea-col-sel")
                    )
                    if not numerica:
                        sel.disable()  # coluna de texto só pode ser ignorada
                    selects[coluna] = sel

    def ao_analisar() -> None:
        fatores = [c for c, s in selects.items() if s.value == "Fator"]
        respostas = [c for c, s in selects.items() if s.value == "Resposta"]
        if not fatores:
            ui.notify("Escolha ao menos uma coluna como Fator.", type="warning")
            return
        if not respostas:
            ui.notify("Escolha ao menos uma coluna como Resposta.", type="warning")
            return
        try:
            analise, planejamento = _rodar_analise(tabela, fatores, respostas)
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
            _mostrar_resultados(analise, planejamento)

    ui.button("Analisar", on_click=ao_analisar).props("unelevated").classes("ea-botao")
    # Os resultados aparecem ABAIXO do botão, na ordem de leitura.
    resultado = ui.column().classes("w-full ea-slot")


def _rodar_analise(
    tabela: Table, fatores: list[str], respostas: list[str]
) -> tuple[AnalysisResult, Planejamento]:
    """Monta o delineamento a partir dos dados e roda o núcleo.

    Devolve também o `Planejamento`: a superfície precisa das faixas dos fatores
    para converter a grade codificada em unidades reais.
    """
    objetos = [
        Fator(nome, float(tabela.coluna(nome).min()), float(tabela.coluna(nome).max()))
        for nome in fatores
    ]
    niveis = {nome: list(tabela.coluna(nome)) for nome in fatores}
    tipo = detectar_tipo(niveis, len(tabela))
    planejamento = Planejamento(tipo=tipo, fatores=objetos)
    termos = _escolher_termos(fatores, tipo, len(tabela))
    analise = analisar(
        tabela, planejamento, termos, respostas, versao_ensaia=__version__
    )
    return analise, planejamento


def _escolher_termos(fatores: list[str], tipo: str, n_obs: int) -> list[str]:
    """Escolhe os termos do modelo, degradando para caber nos graus de liberdade.

    Fatorial de 2 níveis não tem como estimar curvatura (quadráticos), então
    entram só lineares + interações. Para os demais, tenta o modelo quadrático
    completo; se não houver observações suficientes (precisa sobrar grau de
    liberdade para o resíduo), cai para sem-quadráticos e, no limite, só lineares.
    """
    quadraticos = tipo != "fatorial_completo"
    candidatos = [
        termos_do_modelo(fatores, incluir_quadraticos=quadraticos, grau_interacao=2),
        termos_do_modelo(fatores, incluir_quadraticos=False, grau_interacao=2),
        termos_do_modelo(fatores, incluir_quadraticos=False, grau_interacao=1),
    ]
    for termos in candidatos:
        if len(termos) < n_obs:
            return termos
    return candidatos[-1]  # ainda que aperte, deixa o núcleo decidir e avisar


def _mostrar_resultados(analise: AnalysisResult, planejamento: Planejamento) -> None:
    tipo = _TIPO_LEGIVEL.get(analise.tipo_planejamento, analise.tipo_planejamento)
    primeiro = analise.ajustes[0]
    ui.html('<div class="ea-secao-titulo">Resultados</div>')
    ui.html(
        f'<div class="ea-secao-sub">Delineamento {escape(tipo)} · '
        f"{primeiro.n_observacoes} ensaios · modelo com "
        f"{len(primeiro.termos_incluidos)} termos</div>"
    )

    for ajuste in analise.ajustes:
        with ui.element("div").classes("ea-resultado"):
            ui.html(f'<div class="ea-resp-nome">{escape(ajuste.resposta)}</div>')
            ui.html(
                f'<div class="ea-r2">R² = <b>{_fmt(ajuste.r2, 3)}</b> · '
                f"R² ajustado = <b>{_fmt(ajuste.r2_ajustado, 3)}</b></div>"
            )
            _abas_resposta(ajuste, planejamento.fatores, alfa=analise.metadados.alfa)

    for aviso in analise.avisos:
        ui.html(f'<div class="ea-aviso">{escape(aviso)}</div>')

    # O último texto mostrado (IA ou fiel) é o que vai para o PDF.
    estado: dict[str, RelatorioTextual] = {}
    relatorio = ui.column().classes("w-full ea-slot")
    with ui.element("div").classes("ea-acoes"):
        ui.button(
            "Narrar com IA", on_click=lambda: _gerar_ia(analise, relatorio, estado)
        ).props("unelevated").classes("ea-botao")
        ui.button(
            "ou ver o texto fiel (sem IA)",
            on_click=lambda: _gerar_m0(analise, relatorio, estado),
        ).props("flat").classes("ea-botao-sec")

    _bloco_baixar(analise, estado)


def _bloco_baixar(analise: AnalysisResult, estado: dict[str, RelatorioTextual]) -> None:
    """Passo 7 do fluxo (spec §4): baixar o relatório em PDF e os resultados em JSON."""
    with ui.element("div").classes("ea-baixar"):
        with ui.element("div").classes("ea-acoes"):
            botao_pdf = (
                ui.button("Baixar relatório (PDF)")
                .props("unelevated")
                .classes("ea-botao")
            )
            ui.button(
                "ou baixar os resultados (JSON)", on_click=lambda: _baixar_json(analise)
            ).props("flat").classes("ea-botao-sec")
        ui.html(
            '<div class="ea-ler">O PDF leva o texto que estiver na tela; sem texto '
            "gerado, vai o texto fiel (sem IA). Nada fica guardado: o arquivo é "
            "montado na memória e entregue direto ao seu navegador.</div>"
        )
    botao_pdf.on_click(lambda: _baixar_pdf(analise, estado, botao_pdf))


async def _baixar_pdf(
    analise: AnalysisResult, estado: dict[str, RelatorioTextual], botao: ui.button
) -> None:
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

    texto = estado.get("texto") or gerar_relatorio(analise, modo="m0")
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


_ABA_EFEITOS = "Efeitos"
_PONTOS_CONTORNO = 61
_ABA_ANOVA = "ANOVA"
_ABA_DIAGNOSTICO = "Diagnóstico"
_ABA_SUPERFICIE = "Superfície"


def _abas_resposta(
    ajuste: AjusteResposta, fatores: list[Fator], *, alfa: float
) -> None:
    """Abas de uma resposta, cada uma montada só na primeira vez que é aberta.

    O clique numa barra do Pareto leva à superfície daquele termo (o "zoom" do
    efeito para a forma da resposta): uma interação a × b abre a superfície com
    a e b nos eixos.
    """
    nomes = [_ABA_EFEITOS, _ABA_ANOVA, _ABA_DIAGNOSTICO]
    tem_superficie = len(fatores) >= 2
    if tem_superficie:
        nomes.append(_ABA_SUPERFICIE)

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
    with ui.tab_panels(abas, value=_ABA_EFEITOS, animated=False).classes(
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
                _aba_efeitos(ajuste, alfa, ao_clicar_termo if tem_superficie else None)
            elif nome == _ABA_ANOVA:
                _aba_anova(ajuste)
            elif nome == _ABA_DIAGNOSTICO:
                _aba_diagnostico(ajuste, alfa)
            else:
                painel["superficie"] = _PainelSuperficie(ajuste, fatores)

    def ao_clicar_termo(termo: str) -> None:
        envolvidos = list(dict.fromkeys(n for n, _ in interpretar_termo(termo)))
        abas.set_value(_ABA_SUPERFICIE)
        abrir(_ABA_SUPERFICIE)
        painel["superficie"].focar(envolvidos)

    abas.on_value_change(lambda e: abrir(e.value))
    abrir(_ABA_EFEITOS)


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
    ui.html('<div class="ea-tabela-rotulo">Coeficientes (escala codificada)</div>')
    _tabela_coeficientes(ajuste)


def _aba_anova(ajuste: AjusteResposta) -> None:
    if ajuste.anova:
        ui.html('<div class="ea-tabela-rotulo">ANOVA (Tipo II)</div>')
        _tabela_anova(ajuste)
    else:
        ui.html(
            '<div class="ea-ler">ANOVA Tipo II indisponível para este modelo.</div>'
        )
    ui.html(f'<div class="ea-falta">{escape(_texto_falta(ajuste))}</div>')


def _aba_diagnostico(ajuste: AjusteResposta, alfa: float) -> None:
    d = ajuste.diagnostico
    if d is None:
        ui.html(
            '<div class="ea-ler">Este resultado não traz os valores por ensaio.'
            "</div>"
        )
        return

    ui.html('<div class="ea-grafico-titulo">Previsto × observado</div>')
    _grafico(graficos.opcoes_preditos_observados(ajuste), 300)
    ui.html(
        '<div class="ea-ler">Ponto sobre a linha <b>y = x</b> é ensaio que o modelo '
        "acerta; quanto mais longe da linha, maior o erro naquele ensaio.</div>"
    )

    ui.html('<div class="ea-grafico-titulo">Resíduos × previsto</div>')
    _grafico(graficos.opcoes_residuos_preditos(ajuste), 280)
    ui.html(
        '<div class="ea-ler">Os pontos devem se espalhar ao acaso em torno do zero. '
        "Funil, curva ou tendência indicam algo que o modelo deixou de fora.</div>"
    )

    ui.html('<div class="ea-grafico-titulo">Normalidade dos resíduos (Q-Q)</div>')
    _grafico(graficos.opcoes_qq(pontos_qq(d.residuos)), 280)
    ui.html(f'<div class="ea-ler">{_texto_normalidade(ajuste, alfa)}</div>')

    ui.html('<div class="ea-tabela-rotulo">Valores por ensaio</div>')
    colunas = [
        {"name": "n", "label": "Ensaio", "field": "n", "align": "left"},
        {"name": "obs", "label": "Observado", "field": "obs", "align": "right"},
        {"name": "prev", "label": "Previsto", "field": "prev", "align": "right"},
        {"name": "res", "label": "Resíduo", "field": "res", "align": "right"},
    ]
    linhas = [
        {"n": i + 1, "obs": _fmt(o, 3), "prev": _fmt(p, 3), "res": _fmt(r, 3)}
        for i, (o, p, r) in enumerate(
            zip(d.observados, d.preditos, d.residuos, strict=True)
        )
    ]
    ui.table(
        columns=colunas, rows=linhas, row_key="n", pagination={"rowsPerPage": 10}
    ).props("flat bordered dense").classes("ensaia-previa w-full")


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

    def __init__(self, ajuste: AjusteResposta, fatores: list[Fator]) -> None:
        self.ajuste = ajuste
        self.fatores = fatores
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
                ui.toggle({"contorno": "Contorno", "3d": "3D"}, value="contorno")
                .props(
                    "no-caps unelevated dense color=white text-color=primary "
                    "toggle-color=primary toggle-text-color=white"
                )
                .classes("ea-forma")
            )
        self.area_fixos = ui.element("div").classes("ea-controles")
        self.area_grafico = ui.column().classes("w-full")
        self.ler = ui.html("").classes("ea-ler")
        self.grafico: ui.echart | None = None

        self.sel_x.on_value_change(lambda e: self._trocar_eixo("x", e.value))
        self.sel_y.on_value_change(lambda e: self._trocar_eixo("y", e.value))
        self.forma.on_value_change(lambda _: self._redesenhar(recriar=True))
        self._montar_fixos()
        self._redesenhar(recriar=True)

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
            else graficos.opcoes_contorno(grade)
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
    if valor is None:
        return "—"
    if valor < 0.0001:
        return "&lt; 0,0001"
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
            "p": _fmt(c.valor_p, 4),
            "sig": "sim" if c.significativo else "—",
        }
        for c in ajuste.coeficientes
    ]
    ui.table(columns=colunas, rows=linhas, row_key="termo").props(
        "flat bordered dense"
    ).classes("ensaia-previa w-full")


def _tabela_anova(ajuste: AjusteResposta) -> None:
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
            "p": _fmt(linha.valor_p, 4),
        }
        for linha in ajuste.anova
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


def _gerar_m0(
    analise: AnalysisResult, destino: ui.column, estado: dict[str, RelatorioTextual]
) -> None:
    texto = gerar_relatorio(analise, modo="m0")
    estado["texto"] = texto
    destino.clear()
    with destino:
        _mostrar_relatorio(texto)


async def _gerar_ia(
    analise: AnalysisResult, destino: ui.column, estado: dict[str, RelatorioTextual]
) -> None:
    cfg = _config_openai()
    if cfg is None:
        ui.notify(
            "Configure OPENAI_API_KEY no arquivo .env para narrar com IA. "
            "Mostrando o texto fiel (sem IA).",
            type="warning",
            position="top",
            timeout=9000,
        )
        _gerar_m0(analise, destino, estado)
        return

    destino.clear()
    with destino:
        ui.spinner(size="lg").classes("ea-spinner")
        ui.html('<div class="ea-secao-sub">Narrando com IA…</div>')

    def trabalho() -> RelatorioTextual:
        with ClienteModelo(cfg) as cliente:
            return gerar_relatorio(analise, modo="m3", cliente=cliente)

    try:
        relatorio = await run.io_bound(trabalho)
    except ErroDeIA as erro:
        destino.clear()
        ui.notify(
            f"Falha ao falar com o modelo: {erro}. Mostrando o texto fiel (sem IA).",
            type="negative",
            position="top",
            timeout=9000,
        )
        _gerar_m0(analise, destino, estado)
        return

    destino.clear()
    if relatorio is None:  # o servidor encerrou no meio da chamada
        return
    estado["texto"] = relatorio
    with destino:
        _mostrar_relatorio(relatorio)


def _mostrar_relatorio(relatorio: RelatorioTextual) -> None:
    origem = (
        f"narrado por IA ({relatorio.modelo_usado})"
        if relatorio.modo == "m3"
        else "texto fiel, gerado pelo núcleo (sem IA)"
    )
    with ui.element("div").classes("ea-relatorio"):
        ui.html('<div class="ea-secao-titulo">Relatório</div>')
        ui.html(f'<div class="ea-secao-sub">{escape(origem)}</div>')
        for secao in relatorio.secoes:
            tag_classe = "ea-tag-ia" if secao.com_ia else "ea-tag-m0"
            tag_texto = "IA" if secao.com_ia else "texto fiel"
            ui.html(
                '<div class="ea-rel-secao">'
                f'<div class="ea-rel-titulo">{escape(secao.titulo)} '
                f'<span class="{tag_classe}">· {tag_texto}</span></div>'
                f'<div class="ea-rel-texto">{escape(secao.texto)}</div></div>'
            )
        for aviso in relatorio.avisos:
            ui.html(f'<div class="ea-aviso">{escape(aviso)}</div>')


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


def _carregar_env(caminho: Path) -> None:
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def _config_openai() -> ConfiguracaoModelo | None:
    """Config da OpenAI a partir do `.env` do projeto, ou None se não houver chave."""
    raiz = Path(__file__).resolve().parents[3]  # src/ensaia/ui/ → raiz do projeto
    _carregar_env(raiz / ".env")
    chave = os.environ.get("OPENAI_API_KEY")
    if not chave:
        return None
    return ConfiguracaoModelo(
        url_base="https://api.openai.com/v1",
        modelo=os.environ.get("ENSAIA_MODELO_OPENAI", "gpt-4o-mini"),
        chave_api=chave,
        temperatura=0.0,
    )
