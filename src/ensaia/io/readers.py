"""Lê CSV, TSV, TXT, XLSX, XLS e ODS e devolve uma Table, sem pandas.
Planilhas são abertas só para leitura; fórmulas e macros nunca rodam.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from ensaia.core.table import Table

_EXTENSOES_CSV = {".csv", ".tsv", ".txt"}
_EXTENSOES_PLANILHA = {".xlsx", ".xls", ".ods"}
FORMATOS_ACEITOS = sorted(_EXTENSOES_CSV | _EXTENSOES_PLANILHA)
SEPARADORES = {",": "vírgula", ";": "ponto e vírgula", "\t": "tabulação", "|": "barra"}

# Teto de linhas para evitar abuso de memória.
MAX_LINHAS = 10_000


@dataclass(frozen=True)
class FormatoCsv:
    """Separador, decimal e codificação detectados num arquivo de texto."""

    separador: str
    decimal: str
    codificacao: str


def ler_dados(caminho: Path | str) -> Table:
    """Carrega um arquivo em disco como Table."""
    arquivo = Path(caminho)
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {arquivo}")
    return ler_dados_de_bytes(arquivo.read_bytes(), arquivo.name)


def ler_dados_de_bytes(
    conteudo: bytes,
    nome: str,
    *,
    aba: str | None = None,
    separador: str | None = None,
) -> Table:
    """Carrega um arquivo recebido em memória como Table."""
    extensao = _extensao(nome)
    if extensao == ".xlsx":
        cabecalho, linhas = _ler_xlsx(conteudo, nome, aba)
    elif extensao == ".xls":
        cabecalho, linhas = _ler_xls(conteudo, nome, aba)
    elif extensao == ".ods":
        cabecalho, linhas = _ler_ods(conteudo, nome, aba)
    else:
        texto, _ = _decodificar(conteudo, nome)
        cabecalho, linhas = _ler_csv(texto, nome, separador)

    _validar_cabecalho(nome, cabecalho)
    linhas = [linha for linha in linhas if any(str(c).strip() for c in linha)]
    if not linhas:
        raise ValueError(f"O arquivo {nome!r} não contém ensaios.")
    if len(linhas) > MAX_LINHAS:
        raise ValueError(
            f"O arquivo {nome!r} tem {len(linhas)} linhas; o limite é {MAX_LINHAS}. "
            "Planejamentos de experimentos costumam ter de 8 a 100 ensaios."
        )

    dados: dict[str, list[object]] = {nome_col: [] for nome_col in cabecalho}
    for linha in linhas:
        for j, nome_col in enumerate(cabecalho):
            dados[nome_col].append(linha[j] if j < len(linha) else "")
    return Table.de_colunas(dados)


def listar_abas(conteudo: bytes, nome: str) -> list[str]:
    """Nomes das abas de uma planilha; vazio para arquivos de texto."""
    extensao = _extensao(nome)
    try:
        if extensao == ".xlsx":
            from openpyxl import load_workbook

            planilha = load_workbook(BytesIO(conteudo), read_only=True, data_only=True)
            nomes = list(planilha.sheetnames)
            planilha.close()
            return nomes
        if extensao == ".xls":
            import xlrd

            return list(xlrd.open_workbook(file_contents=conteudo).sheet_names())
        if extensao == ".ods":
            return [t.getAttribute("name") for t in _tabelas_ods(conteudo)]
    except Exception as erro:  # arquivo corrompido: mensagem clara, não traceback
        raise ValueError(f"Não foi possível abrir {nome!r}: {erro}") from erro
    return []


def formato_csv(conteudo: bytes, nome: str) -> FormatoCsv | None:
    """Separador, decimal e codificação de um arquivo de texto."""
    if _extensao(nome) not in _EXTENSOES_CSV:
        return None
    texto, codificacao = _decodificar(conteudo, nome)
    linhas = _linhas_sem_comentario(texto)
    separador = _detectar_separador(linhas)
    corpo = list(csv.reader(linhas[1:21], delimiter=separador))
    usa_virgula = any(
        "," in celula and _parece_numero(celula.replace(",", "."))
        for linha in corpo
        for celula in linha
    )
    return FormatoCsv(
        separador=separador,
        decimal="," if usa_virgula else ".",
        codificacao=codificacao,
    )


# --- texto --------------------------------------------------------------------------


def _extensao(nome: str) -> str:
    """Extensão do arquivo, se for um formato aceito."""
    extensao = Path(nome).suffix.lower()
    if extensao not in _EXTENSOES_CSV | _EXTENSOES_PLANILHA:
        raise ValueError(
            f"Formato {extensao or 'sem extensão'!r} não suportado para dados "
            "experimentais. Use CSV, TSV, TXT, XLSX, XLS ou ODS."
        )
    return extensao


def _decodificar(conteudo: bytes, nome: str) -> tuple[str, str]:
    """Decodifica os bytes tentando as codificações usuais."""
    ultimo_erro: UnicodeDecodeError | None = None
    for codificacao in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            rotulo = "UTF-8" if codificacao.startswith("utf") else "Latin-1"
            return conteudo.decode(codificacao), rotulo
        except UnicodeDecodeError as erro:
            ultimo_erro = erro
    raise ValueError(
        f"Não foi possível ler {nome!r} como UTF-8 ou Latin-1."
    ) from ultimo_erro


def _linhas_sem_comentario(texto: str) -> list[str]:
    """Linhas do texto, sem as que começam com #."""
    return [linha for linha in texto.splitlines() if not linha.lstrip().startswith("#")]


def _detectar_separador(linhas: list[str]) -> str:
    """Detecta o separador de colunas do CSV."""
    amostra = "\n".join(linhas[:20])
    try:
        return csv.Sniffer().sniff(amostra, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _parece_numero(texto: str) -> bool:
    """Diz se o texto pode ser lido como número."""
    try:
        float(texto.strip())
    except ValueError:
        return False
    return True


def _validar_cabecalho(nome: str, cabecalho: list[str]) -> None:
    """Confere se há cabeçalho e se toda coluna tem nome."""
    if not cabecalho:
        raise ValueError(f"O arquivo {nome!r} não tem cabeçalho.")
    if any(not str(coluna).strip() for coluna in cabecalho):
        raise ValueError(
            "O arquivo tem uma coluna sem nome. Dê um nome a todas as colunas."
        )
    repetidas = [coluna for coluna in cabecalho if cabecalho.count(coluna) > 1]
    if repetidas:
        raise ValueError(f"O arquivo tem colunas repetidas: {sorted(set(repetidas))}.")


def _ler_csv(
    conteudo: str, nome: str, separador: str | None = None
) -> tuple[list[str], list[Sequence[object]]]:
    """Lê um CSV já decodificado como Table."""
    linhas_texto = _linhas_sem_comentario(conteudo)
    if not "\n".join(linhas_texto[:20]).strip():
        raise ValueError(f"O CSV {nome!r} não contém dados além de comentários.")
    if separador is not None and separador not in SEPARADORES:
        raise ValueError(f"Separador {separador!r} não suportado.")
    sep = separador or _detectar_separador(linhas_texto)
    linhas = list(csv.reader(linhas_texto, delimiter=sep))
    cabecalho = [c.strip() for c in linhas[0]]
    corpo: list[Sequence[object]] = list(linhas[1:])
    return cabecalho, corpo


# --- planilhas ------------------------------------------------------------------------


def _separar(
    linhas: list[list[object]], nome: str
) -> tuple[list[str], list[Sequence[object]]]:
    """Separa cabeçalho e linhas, com células vazias como texto vazio."""
    if not linhas:
        raise ValueError(f"O arquivo {nome!r} não contém ensaios.")
    cabecalho = [str(c).strip() if c is not None else "" for c in linhas[0]]
    while cabecalho and not cabecalho[-1]:
        cabecalho.pop()  # colunas vazias à direita não são colunas
    corpo: list[Sequence[object]] = [
        ["" if c is None else c for c in linha] for linha in linhas[1:]
    ]
    return cabecalho, corpo


def _aba_inexistente(nome: str, aba: str, abas: list[str]) -> ValueError:
    """Erro para uma aba que não existe na planilha."""
    return ValueError(f"A aba {aba!r} não existe em {nome!r}. Abas: {abas}.")


def _ler_xlsx(
    conteudo: bytes, nome: str, aba: str | None
) -> tuple[list[str], list[Sequence[object]]]:
    """Lê uma aba de .xlsx com os valores em cache."""
    from openpyxl import load_workbook

    planilha = load_workbook(BytesIO(conteudo), read_only=True, data_only=True)
    try:
        if aba is None:
            folha = planilha.active
        elif aba in planilha.sheetnames:
            folha = planilha[aba]
        else:
            raise _aba_inexistente(nome, aba, list(planilha.sheetnames))
        if folha is None:
            raise ValueError(f"O arquivo {nome!r} não tem nenhuma aba.")
        linhas: list[list[object]] = []
        for linha in folha.iter_rows(values_only=True):
            linhas.append(list(linha))
            if len(linhas) > MAX_LINHAS + 1:
                break
    finally:
        planilha.close()
    return _separar(linhas, nome)


def _ler_xls(
    conteudo: bytes, nome: str, aba: str | None
) -> tuple[list[str], list[Sequence[object]]]:
    """Lê uma aba de .xls (Excel 97–2003)."""
    import xlrd

    try:
        livro = xlrd.open_workbook(file_contents=conteudo)
    except xlrd.XLRDError as erro:
        raise ValueError(f"Não foi possível abrir {nome!r}: {erro}") from erro
    if aba is not None and aba not in livro.sheet_names():
        raise _aba_inexistente(nome, aba, list(livro.sheet_names()))
    folha = livro.sheet_by_name(aba) if aba else livro.sheet_by_index(0)
    linhas = [
        folha.row_values(i) for i in range(min(folha.nrows, MAX_LINHAS + 2))
    ]
    return _separar(linhas, nome)


def _tabelas_ods(conteudo: bytes) -> list:  # type: ignore[type-arg]
    """Abas de um arquivo .ods."""
    from odf.opendocument import load
    from odf.table import Table as TabelaOds

    documento = load(BytesIO(conteudo))
    return list(documento.spreadsheet.getElementsByType(TabelaOds))


def _ler_ods(
    conteudo: bytes, nome: str, aba: str | None
) -> tuple[list[str], list[Sequence[object]]]:
    """Lê uma aba de .ods, expandindo células repetidas com teto."""
    from odf import teletype
    from odf.table import TableRow

    tabelas = _tabelas_ods(conteudo)
    if not tabelas:
        raise ValueError(f"O arquivo {nome!r} não tem nenhuma aba.")
    nomes = [t.getAttribute("name") for t in tabelas]
    if aba is not None and aba not in nomes:
        raise _aba_inexistente(nome, aba, nomes)
    folha = tabelas[nomes.index(aba)] if aba else tabelas[0]

    linhas: list[list[object]] = []
    for linha in folha.getElementsByType(TableRow):
        celulas: list[object] = []
        for celula in linha.childNodes:
            if celula.qname[1] not in ("table-cell", "covered-table-cell"):
                continue
            repetir = int(celula.getAttribute("numbercolumnsrepeated") or 1)
            tipo = celula.getAttribute("valuetype")
            valor: object = (
                float(celula.getAttribute("value"))
                if tipo in ("float", "percentage", "currency")
                else teletype.extractText(celula)
            )
            celulas.extend([valor] * min(repetir, 1024))
        while celulas and celulas[-1] in ("", None):
            celulas.pop()
        repetir_linha = int(linha.getAttribute("numberrowsrepeated") or 1)
        linhas.extend([celulas] * min(repetir_linha, MAX_LINHAS + 2))
        if len(linhas) > MAX_LINHAS + 1:
            break
    while linhas and not linhas[-1]:
        linhas.pop()
    return _separar(linhas, nome)
