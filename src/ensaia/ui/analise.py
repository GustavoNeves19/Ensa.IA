"""Passos 3 e 4 do fluxo (spec §4): mapear colunas, analisar e mostrar o laudo.

Depois que `ui/upload.py` lê a planilha numa `Table`, esta tela:

1. **Mapear** — para cada coluna, o usuário diz se é fator (entrada), resposta
   (saída) ou se deve ser ignorada. O padrão é inteligente: colunas numéricas
   viram fatores, a última numérica vira resposta, texto é ignorado.
2. **Analisar** — monta o delineamento a partir dos próprios dados (faixas dos
   fatores pelo mín/máx, tipo inferido por `detectar_tipo`, termos do modelo
   escolhidos conforme o tipo) e roda o núcleo determinístico (`core.pipeline`).
3. **Mostrar** — R², coeficientes, ANOVA e falta de ajuste por resposta.
4. **Relatório** — em texto fiel (modo M0, offline) ou narrado por IA (modo M3,
   com a chave da OpenAI lida do `.env`). A IA roda fora da thread da interface
   (`run.io_bound`) para a tela não congelar enquanto o modelo responde.

Nada é calculado aqui: a conta é toda do núcleo; esta camada só coleta escolhas,
chama o pipeline e desenha o resultado.
"""

from __future__ import annotations

import math
import os
from html import escape
from pathlib import Path

from nicegui import run, ui

from ensaia import __version__
from ensaia.ai.client import ClienteModelo, ConfiguracaoModelo, ErroDeIA
from ensaia.ai.report import RelatorioTextual, gerar_relatorio
from ensaia.core.design import Fator, Planejamento, detectar_tipo, termos_do_modelo
from ensaia.core.pipeline import analisar
from ensaia.core.results import AnalysisResult
from ensaia.core.table import Table

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
            analise = _rodar_analise(tabela, fatores, respostas)
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
            _mostrar_resultados(analise)

    ui.button("Analisar", on_click=ao_analisar).props("unelevated").classes("ea-botao")
    # Os resultados aparecem ABAIXO do botão, na ordem de leitura.
    resultado = ui.column().classes("w-full ea-slot")


def _rodar_analise(
    tabela: Table, fatores: list[str], respostas: list[str]
) -> AnalysisResult:
    """Monta o delineamento a partir dos dados e roda o núcleo."""
    objetos = [
        Fator(nome, float(tabela.coluna(nome).min()), float(tabela.coluna(nome).max()))
        for nome in fatores
    ]
    niveis = {nome: list(tabela.coluna(nome)) for nome in fatores}
    tipo = detectar_tipo(niveis, len(tabela))
    planejamento = Planejamento(tipo=tipo, fatores=objetos)
    termos = _escolher_termos(fatores, tipo, len(tabela))
    return analisar(tabela, planejamento, termos, respostas, versao_ensaia=__version__)


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


def _mostrar_resultados(analise: AnalysisResult) -> None:
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
            ui.html('<div class="ea-tabela-rotulo">Coeficientes</div>')
            _tabela_coeficientes(ajuste)
            if ajuste.anova:
                ui.html('<div class="ea-tabela-rotulo">ANOVA (Tipo II)</div>')
                _tabela_anova(ajuste)
            ui.html(f'<div class="ea-falta">{escape(_texto_falta(ajuste))}</div>')

    for aviso in analise.avisos:
        ui.html(f'<div class="ea-aviso">{escape(aviso)}</div>')

    relatorio = ui.column().classes("w-full ea-slot")
    with ui.element("div").classes("ea-acoes"):
        ui.button(
            "Narrar com IA", on_click=lambda: _gerar_ia(analise, relatorio)
        ).props("unelevated").classes("ea-botao")
        ui.button(
            "ou ver o texto fiel (sem IA)",
            on_click=lambda: _gerar_m0(analise, relatorio),
        ).props("flat").classes("ea-botao-sec")


def _tabela_coeficientes(ajuste) -> None:
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
            "termo": c.termo,
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


def _tabela_anova(ajuste) -> None:
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
            "fonte": linha.fonte,
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


def _texto_falta(ajuste) -> str:
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


def _gerar_m0(analise: AnalysisResult, destino: ui.column) -> None:
    destino.clear()
    with destino:
        _mostrar_relatorio(gerar_relatorio(analise, modo="m0"))


async def _gerar_ia(analise: AnalysisResult, destino: ui.column) -> None:
    cfg = _config_openai()
    if cfg is None:
        ui.notify(
            "Configure OPENAI_API_KEY no arquivo .env para narrar com IA. "
            "Mostrando o texto fiel (sem IA).",
            type="warning",
            position="top",
            timeout=9000,
        )
        _gerar_m0(analise, destino)
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
        _gerar_m0(analise, destino)
        return

    destino.clear()
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
