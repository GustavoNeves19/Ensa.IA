"""Passos 1 e 2 do fluxo (spec §4): enviar o arquivo e conferir os dados.

A planilha chega como bytes em memória (`ui.upload`) e é lida por
`io.readers.ler_dados_de_bytes` — nunca gravada em disco (princípio P1). Erros de
leitura viram avisos em português claro, não telas de exceção.

Conferir (passo 2): a prévia mostra os dados 5 linhas por vez, com os números
no padrão brasileiro, e embaixo dela o nome do arquivo e o tamanho; em planilha
com várias abas, o usuário escolhe a aba (RF-03); em arquivo de texto, uma linha
discreta diz o separador, o decimal e a codificação detectados, e o separador
pode ser trocado. Quem não tem uma planilha à mão pode abrir um dos exemplos
públicos (RF-18) ou baixar a planilha-modelo com o guia (US-02); essas opções
saem da tela assim que uma planilha é lida.
"""

from __future__ import annotations

from collections.abc import Callable
from html import escape

from nicegui import events, ui

from ensaia.core.table import Table
from ensaia.exemplos import EXEMPLOS, conteudo_exemplo
from ensaia.io.modelo import planilha_modelo_xlsx
from ensaia.io.readers import (
    SEPARADORES,
    FormatoCsv,
    formato_csv,
    ler_dados_de_bytes,
    listar_abas,
)
from ensaia.ui.tema import CINZA

# RF-01: aceita até 5 MB; acima disso o upload é recusado no próprio navegador.
MAX_BYTES = 5 * 1024 * 1024
_ACEITA = ".csv,.tsv,.txt,.xlsx,.xls,.ods"
_LIMITE_PREVIA = 50
_LINHAS_POR_PAGINA = 5
_MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def construir_upload(
    ao_carregar: Callable[[Table | None, str], None] | None = None,
) -> None:
    """Monta a dropzone, os exemplos, a planilha-modelo e a área de conferência.

    `ao_carregar` recebe a `Table` e o nome do arquivo quando a leitura dá certo
    — é o gancho para o passo seguinte (mapear colunas). Recebe `None` quando a
    aba escolhida não tem dados, para o passo seguinte não ficar com a anterior.
    """

    def carregar(
        conteudo: bytes,
        nome: str,
        *,
        aba: str | None = None,
        separador: str | None = None,
    ) -> None:
        area_previa.clear()
        try:
            abas = listar_abas(conteudo, nome)
            formato = formato_csv(conteudo, nome)
        except (ValueError, FileNotFoundError) as erro:
            ui.notify(str(erro), type="negative", position="top", timeout=8000)
            return
        tabela, aba, problema = _ler(conteudo, nome, abas, aba, separador)
        if tabela is None and len(abas) <= 1:
            ui.notify(problema, type="negative", position="top", timeout=8000)
            return
        if ao_carregar is not None:
            ao_carregar(tabela, nome)
        # Com uma planilha na tela, exemplos e modelo só atrapalham a leitura.
        alternativas.set_visibility(False)
        with area_previa:
            _escolher_aba(
                abas, aba, lambda nova_aba: carregar(conteudo, nome, aba=nova_aba)
            )
            if tabela is None:
                # Com várias abas, o seletor continua na tela para trocar de aba.
                ui.html(f'<div class="ea-aviso">{escape(problema)}</div>')
            else:
                _mostrar_previa(tabela, nome)
                if formato is not None:
                    _linha_formato(
                        formato,
                        formato.separador if separador is None else separador,
                        lambda novo_sep: carregar(conteudo, nome, separador=novo_sep),
                    )

    async def tratar_upload(evento: events.UploadEventArguments) -> None:
        # Na NiceGUI 3.x o arquivo vem em `evento.file`, e `read()` é assíncrono.
        carregar(await evento.file.read(), evento.file.name)
        # Com max_files=1 a fila cheia esconde o seletor: esvazia para aceitar
        # outra planilha (o arquivo já foi lido para a memória).
        envio.reset()

    def tratar_recusa(_: events.UiEventArguments) -> None:
        ui.notify(
            "Arquivo recusado. Envie um CSV, TSV, TXT, XLSX, XLS ou ODS de até 5 MB.",
            type="warning",
            position="top",
            timeout=8000,
        )

    envio = ui.upload(
        on_upload=tratar_upload,
        on_rejected=tratar_recusa,
        max_file_size=MAX_BYTES,
        max_files=1,
        auto_upload=True,
        label="Arraste sua planilha aqui ou clique para escolher",
    ).props(f'accept="{_ACEITA}" flat').classes("ensaia-upload")

    ui.label("Formatos aceitos: CSV, TSV, TXT, XLSX, XLS, ODS · até 5 MB").style(
        f"color:{CINZA};font-size:0.8rem"
    )

    # Sem planilha à mão: um rótulo por linha e as ações ao lado, alinhadas.
    with ui.element("div").classes("ea-alternativas") as alternativas:
        ui.label("Exemplos publicados").classes("ea-ler")
        with ui.element("div").classes("ea-acoes"):
            for exemplo in EXEMPLOS.values():
                ui.button(
                    exemplo.titulo,
                    on_click=lambda e=exemplo: carregar(
                        conteudo_exemplo(e.id), e.arquivo
                    ),
                ).props("flat dense no-caps").classes("ea-botao-sec").tooltip(
                    f"{exemplo.descricao} Fonte: {exemplo.citacao}"
                )
        ui.label("Planilha-modelo").classes("ea-ler")
        with ui.element("div").classes("ea-acoes"):
            ui.button(
                "Baixar .xlsx com guia de preenchimento",
                on_click=lambda: ui.download.content(
                    planilha_modelo_xlsx(), "ensaia-planilha-modelo.xlsx", _MIME_XLSX
                ),
            ).props("flat dense no-caps").classes("ea-botao-sec")

    # A prévia fica ABAIXO da dropzone, preenchida quando um arquivo é lido.
    area_previa = ui.column().classes("w-full gap-2")


def _ler(
    conteudo: bytes,
    nome: str,
    abas: list[str],
    aba: str | None,
    separador: str | None,
) -> tuple[Table | None, str | None, str]:
    """Lê a aba pedida; sem pedido, a primeira aba que tiver dados.

    Planilhas costumam abrir com uma aba de instruções ou capa antes dos dados;
    pular as abas vazias poupa o usuário de um erro logo no primeiro passo.
    Devolve a tabela (ou `None`), a aba usada e a mensagem do primeiro erro.
    """
    candidatas: list[str | None] = [aba] if aba else (list(abas) or [None])
    primeiro_erro = ""
    for candidata in candidatas:
        try:
            tabela = ler_dados_de_bytes(
                conteudo, nome, aba=candidata, separador=separador
            )
        except (ValueError, FileNotFoundError) as erro:
            if not primeiro_erro:
                primeiro_erro = (
                    f"A aba '{candidata}' não tem dados de ensaios."
                    if candidata is not None and len(abas) > 1
                    else str(erro)
                )
            continue
        return tabela, candidata, ""
    return None, candidatas[0], primeiro_erro


def _escolher_aba(
    abas: list[str], aba: str | None, trocar_aba: Callable[[str], None]
) -> None:
    """Passo 2 em planilha com várias abas: qual aba tem os dados (RF-03)."""
    if len(abas) <= 1:
        return
    with ui.element("div").classes("ea-controles"):
        ui.select(
            abas,
            value=aba,
            label="Aba da planilha",
            on_change=lambda e: trocar_aba(str(e.value)),
        ).props("dense outlined")
        ui.html(
            f'<div class="ea-ler">A planilha tem {len(abas)} abas; os dados '
            "devem estar numa só, com os nomes das colunas na primeira linha."
            "</div>"
        )


def _linha_formato(
    formato: FormatoCsv, separador: str, trocar_separador: Callable[[str], None]
) -> None:
    """Como o arquivo de texto foi lido, numa linha discreta, e o "trocar"."""
    decimal = "vírgula" if formato.decimal == "," else "ponto"
    with ui.element("div").classes("ea-formato"):
        with (
            ui.button("Trocar separador", icon="swap_horiz")
            .props("outline dense no-caps")
            .classes("ea-formato-trocar")
            .tooltip("Se as colunas saírem grudadas na tabela, troque o separador."),
            ui.menu(),
        ):
            for sep, nome in SEPARADORES.items():
                ui.menu_item(nome, lambda s=sep: trocar_separador(s)).classes(
                    "ea-formato-atual" if sep == separador else ""
                )
        ui.html(
            f"Separador <b>{escape(SEPARADORES.get(separador, separador))}</b> · "
            f"decimal <b>{decimal}</b> · {escape(formato.codificacao)}"
        ).classes("ea-formato-texto")


def _mostrar_previa(tabela: Table, nome: str) -> None:
    """A tabela, 5 linhas por página, e embaixo o arquivo e o tamanho."""
    total = len(tabela)
    colunas = [
        {"name": c, "label": c, "field": c, "align": "left"} for c in tabela.colunas
    ]
    linhas = [
        {"_n": i, **{c: _celula(tabela, c, i) for c in tabela.colunas}}
        for i in range(min(total, _LIMITE_PREVIA))
    ]
    ui.table(
        columns=colunas,
        rows=linhas,
        row_key="_n",
        pagination={"rowsPerPage": _LINHAS_POR_PAGINA},
    ).props(
        f":rows-per-page-options=[{_LINHAS_POR_PAGINA}] flat bordered dense"
    ).classes("ensaia-previa ea-previa-dados w-full")

    with ui.element("div").classes("ea-previa-info"):
        ui.label(nome).classes("ea-previa-nome")
        ui.label(
            f"{total} {'ensaio' if total == 1 else 'ensaios'} · "
            f"{len(tabela.colunas)} "
            f"{'coluna' if len(tabela.colunas) == 1 else 'colunas'}"
        ).classes("ea-previa-tamanho")
    if total > _LIMITE_PREVIA:
        ui.label(
            f"A prévia mostra as primeiras {_LIMITE_PREVIA} de {total} linhas."
        ).classes("ea-formato-dica")


def _celula(tabela: Table, coluna: str, i: int) -> str:
    """Valor de uma célula para a prévia, numérico em padrão brasileiro."""
    if tabela.e_numerica(coluna):
        return _numero_ptbr(float(tabela.coluna(coluna)[i]))
    return tabela.texto(coluna)[i]


def _numero_ptbr(valor: float) -> str:
    """Número enxuto com vírgula decimal: inteiro sem casas, resto sem zeros à toa."""
    if valor == int(valor):
        return str(int(valor))
    return f"{valor:g}".replace(".", ",")
