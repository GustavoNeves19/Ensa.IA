"""Envio e conferência da planilha: dropzone, exemplos, modelo e prévia.
O arquivo é lido na memória e nunca gravado em disco.
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
    """Monta o envio, os exemplos, a planilha-modelo e a prévia."""

    def carregar(
        conteudo: bytes,
        nome: str,
        *,
        aba: str | None = None,
        separador: str | None = None,
    ) -> None:
        """Lê o arquivo e mostra a prévia, ou o erro."""
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
        """Recebe o arquivo enviado e libera um novo envio."""
        carregar(await evento.file.read(), evento.file.name)
        # Esvazia a fila para aceitar outra planilha.
        envio.reset()

    def tratar_recusa(_: events.UiEventArguments) -> None:
        """Avisa quando o arquivo é recusado."""
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

    # Sem planilha: um rótulo por linha e as ações ao lado.
    with ui.element("div").classes("ea-alternativas") as alternativas:
        ui.label("Carregar um exemplo publicado").classes("ea-ler")
        with ui.element("div").classes("ea-acoes"):
            for exemplo in EXEMPLOS.values():
                ui.button(
                    f"Usar: {exemplo.titulo}",
                    icon="science",
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
                icon="file_download",
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
    """Lê a aba pedida ou a primeira que tiver dados."""
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
    """Seletor de aba para planilhas com várias abas."""
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
    """Linha com separador, decimal e codificação, e o trocar separador."""
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
    """Prévia da planilha, 5 linhas por página."""
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
    """Valor de uma célula para a prévia."""
    if tabela.e_numerica(coluna):
        return _numero_ptbr(float(tabela.coluna(coluna)[i]))
    return tabela.texto(coluna)[i]


def _numero_ptbr(valor: float) -> str:
    """Número com vírgula, sem zeros sobrando."""
    if valor == int(valor):
        return str(int(valor))
    return f"{valor:g}".replace(".", ",")
