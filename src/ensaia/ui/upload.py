"""Passo 1 do fluxo (spec §4): enviar o arquivo e conferir a prévia dos dados.

A planilha chega como bytes em memória (`ui.upload`) e é lida por
`io.readers.ler_dados_de_bytes` — nunca gravada em disco (princípio P1). Erros de
leitura viram avisos em português claro, não telas de exceção. A prévia mostra
até 50 linhas, com os números no padrão brasileiro (vírgula decimal).

O mapeamento de colunas e a escolha de análises (passos 3 e 4) entram depois;
aqui a `Table` carregada é entregue ao chamador por um callback.
"""

from __future__ import annotations

from collections.abc import Callable

from nicegui import events, ui

from ensaia.core.table import Table
from ensaia.io.readers import ler_dados_de_bytes
from ensaia.ui.tema import CINZA, TINTA, VERDE_ESCURO

# RF-01: aceita até 5 MB; acima disso o upload é recusado no próprio navegador.
MAX_BYTES = 5 * 1024 * 1024
_ACEITA = ".csv,.tsv,.txt,.xlsx,.xls"
_LIMITE_PREVIA = 50


def construir_upload(ao_carregar: Callable[[Table, str], None] | None = None) -> None:
    """Monta a dropzone e a área de prévia.

    `ao_carregar` recebe a `Table` e o nome do arquivo quando a leitura dá certo —
    o gancho para o próximo passo (mapear colunas), ainda não implementado.
    """
    async def tratar_upload(evento: events.UploadEventArguments) -> None:
        # Na NiceGUI 3.x o arquivo vem em `evento.file`, e `read()` é assíncrono.
        area_previa.clear()
        conteudo = await evento.file.read()
        nome = evento.file.name
        try:
            tabela = ler_dados_de_bytes(conteudo, nome)
        except (ValueError, FileNotFoundError) as erro:
            ui.notify(str(erro), type="negative", position="top", timeout=8000)
            return
        if ao_carregar is not None:
            ao_carregar(tabela, nome)
        with area_previa:
            _mostrar_previa(tabela, nome)

    def tratar_recusa(_: events.UiEventArguments) -> None:
        ui.notify(
            "Arquivo recusado. Envie um CSV, TSV, TXT, XLSX ou XLS de até 5 MB.",
            type="warning",
            position="top",
            timeout=8000,
        )

    ui.upload(
        on_upload=tratar_upload,
        on_rejected=tratar_recusa,
        max_file_size=MAX_BYTES,
        max_files=1,
        auto_upload=True,
        label="Arraste sua planilha aqui ou clique para escolher",
    ).props(f'accept="{_ACEITA}" flat').classes("ensaia-upload")

    ui.label("Formatos aceitos: CSV, TSV, TXT, XLSX, XLS · até 5 MB").style(
        f"color:{CINZA};font-size:0.8rem"
    )

    # A prévia fica ABAIXO da dropzone, preenchida quando um arquivo é lido.
    area_previa = ui.column().classes("w-full gap-2")


def _mostrar_previa(tabela: Table, nome: str) -> None:
    total = len(tabela)
    ui.label(nome).style(f"color:{TINTA};font-weight:600;font-size:1rem;margin-top:0.5rem")
    ui.label(
        f"{total} {'ensaio' if total == 1 else 'ensaios'} · "
        f"{len(tabela.colunas)} {'coluna' if len(tabela.colunas) == 1 else 'colunas'}"
    ).style(f"color:{VERDE_ESCURO};font-size:0.85rem;font-weight:600")

    colunas = [
        {"name": c, "label": c, "field": c, "align": "left"} for c in tabela.colunas
    ]
    linhas = [
        {c: _celula(tabela, c, i) for c in tabela.colunas}
        for i in range(min(total, _LIMITE_PREVIA))
    ]
    ui.table(columns=colunas, rows=linhas, row_key=tabela.colunas[0]).props(
        "flat bordered dense"
    ).classes("ensaia-previa w-full")

    if total > _LIMITE_PREVIA:
        ui.label(
            f"Mostrando as primeiras {_LIMITE_PREVIA} de {total} linhas."
        ).style(f"color:{CINZA};font-size:0.8rem")


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
