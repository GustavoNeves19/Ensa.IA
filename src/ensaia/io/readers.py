"""Leitura de dados experimentais (CSV, TSV, TXT, XLSX, XLS, ODS), sem pandas.

Devolve uma `Table` (colunas em numpy) — ver ADR 0008 e a seção 8.1 da
especificação. CSV é lido com a biblioteca padrão; planilhas com o leitor de
cada formato, sempre em modo somente leitura (fórmulas e macros nunca são
executadas; vale o valor em cache):

    .xlsx  openpyxl     .xls  xlrd (formato antigo)     .ods  odfpy (LibreOffice)

Os leitores de planilha só são importados quando um arquivo daquele tipo chega
(spec §16.2: memória ociosa baixa).

A leitura funciona por dois caminhos que compartilham o mesmo parse:

- `ler_dados(caminho)` — a partir de um arquivo em disco, usada pelo pipeline de
  validação (`validation/runner`).
- `ler_dados_de_bytes(conteudo, nome)` — a partir de bytes em memória, usada pela
  interface web, que recebe o upload e **nunca o grava em disco** (princípio P1).
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

# Spec §8.1: planejamentos reais têm de 8 a 100 ensaios; o teto evita abuso de
# memória (e trava planilhas com milhões de linhas vazias "repetidas").
MAX_LINHAS = 10_000


@dataclass(frozen=True)
class FormatoCsv:
    """O que foi detectado num arquivo de texto, para mostrar (e corrigir) na tela."""

    separador: str
    decimal: str
    codificacao: str


def ler_dados(caminho: Path | str) -> Table:
    """Carrega dados experimentais de um arquivo em disco como `Table`."""
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
    """Carrega dados experimentais a partir de bytes em memória como `Table`.

    `nome` é o nome do arquivo (ex.: ``"ensaios.csv"``); sua extensão decide o
    leitor. Em planilhas, `aba` escolhe a aba (padrão: a primeira, ou a ativa no
    .xlsx). Em texto, o separador é detectado (vírgula, ponto e vírgula,
    tabulação ou barra) e pode ser forçado por `separador`. CSVs brasileiros com
    `;` e vírgula decimal são aceitos sem pré-processamento. Linhas iniciadas
    por `#` são comentários; os nomes das colunas são preservados.
    """
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

    cabecalho, linhas = _normalizar(nome, cabecalho, linhas)
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
    """Nomes das abas de uma planilha (RF-03); lista vazia para arquivos de texto."""
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
    """Separador, decimal e codificação detectados; None para planilhas."""
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
    extensao = Path(nome).suffix.lower()
    if extensao not in _EXTENSOES_CSV | _EXTENSOES_PLANILHA:
        raise ValueError(
            f"Formato {extensao or 'sem extensão'!r} não suportado para dados "
            "experimentais. Use CSV, TSV, TXT, XLSX, XLS ou ODS."
        )
    return extensao


def _decodificar(conteudo: bytes, nome: str) -> tuple[str, str]:
    """Decodifica os bytes tentando as codificações usuais, em ordem."""
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
    return [linha for linha in texto.splitlines() if not linha.lstrip().startswith("#")]


def _detectar_separador(linhas: list[str]) -> str:
    amostra = "\n".join(linhas[:20])
    try:
        return csv.Sniffer().sniff(amostra, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _parece_numero(texto: str) -> bool:
    try:
        float(texto.strip())
    except ValueError:
        return False
    return True


# Até onde procurar o cabeçalho de verdade, abaixo de linhas de título.
_LINHAS_DE_TITULO = 10


def _normalizar(
    nome: str, cabecalho: list[str], linhas: list[Sequence[object]]
) -> tuple[list[str], list[Sequence[object]]]:
    """Ajusta o que planilhas de laboratório costumam trazer, sem perder dado.

    - Uma linha de título acima do cabeçalho ("Variáveis independentes |
      Variáveis dependentes") é pulada: o cabeçalho é a primeira linha cheia,
      com a largura dos dados, feita de texto.
    - Coluna sem nome e sem dados some; sem nome mas com dados ganha um nome
      ("Coluna 3") que o usuário vê e corrige no passo de mapear. Células além
      da largura do cabeçalho são ignoradas (costumam ser sobra de um separador
      errado).
    - Nomes repetidos ganham um sufixo ("massa", "massa (2)") em vez de recusar
      o arquivo inteiro.
    - A matriz termina na primeira linha em branco depois dos ensaios: anotações
      ou uma segunda tabela embaixo (composição, médias) não viram ensaios.
    """
    todas: list[list[object]] = [
        list[object](cabecalho),
        *(list[object](linha) for linha in linhas),
    ]
    inicio = _linha_do_cabecalho(todas)
    titulos = [_texto(c) for c in todas[inicio]]
    corpo = _primeiro_bloco(todas[inicio + 1 :])
    manter = [
        j
        for j, titulo in enumerate(titulos)
        if titulo or any(j < len(linha) and _texto(linha[j]) for linha in corpo)
    ]
    if not manter:
        raise ValueError(f"O arquivo {nome!r} não tem cabeçalho.")
    nomes = _sem_repetidos([titulos[j] or f"Coluna {j + 1}" for j in manter])
    dados: list[Sequence[object]] = [
        [linha[j] if j < len(linha) else "" for j in manter] for linha in corpo
    ]
    return nomes, dados


def _primeiro_bloco(linhas: list[list[object]]) -> list[list[object]]:
    """Linhas até a primeira linha em branco que vem depois de algum ensaio."""
    bloco: list[list[object]] = []
    for linha in linhas:
        vazia = not any(_texto(c) for c in linha)
        if vazia and bloco:
            break
        if not vazia:
            bloco.append(linha)
    return bloco


def _linha_do_cabecalho(linhas: list[list[object]]) -> int:
    """Índice do cabeçalho: a primeira linha cheia e de texto (0 se não houver)."""
    cheias = [[c for c in linha if _texto(c)] for linha in linhas[:30]]
    largura = max((len(c) for c in cheias), default=0)
    for i, celulas in enumerate(cheias[:_LINHAS_DE_TITULO]):
        textos = sum(not _parece_numero(_texto(c)) for c in celulas)
        if len(celulas) == largura and textos * 2 > len(celulas):
            return i
    return 0


def _sem_repetidos(nomes: list[str]) -> list[str]:
    vistos: dict[str, int] = {}
    saida: list[str] = []
    for nome_col in nomes:
        vistos[nome_col] = vistos.get(nome_col, 0) + 1
        saida.append(
            nome_col if vistos[nome_col] == 1 else f"{nome_col} ({vistos[nome_col]})"
        )
    return saida


def _texto(celula: object) -> str:
    return "" if celula is None else str(celula).strip()


def _ler_csv(
    conteudo: str, nome: str, separador: str | None = None
) -> tuple[list[str], list[Sequence[object]]]:
    """Faz o parse de um CSV já decodificado, detectando o separador."""
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
    """Cabeçalho = primeira linha; células vazias viram ""."""
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
    return ValueError(f"A aba {aba!r} não existe em {nome!r}. Abas: {abas}.")


def _ler_xlsx(
    conteudo: bytes, nome: str, aba: str | None
) -> tuple[list[str], list[Sequence[object]]]:
    """.xlsx em modo somente leitura, com valores em cache (sem fórmulas)."""
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
    """.xls (Excel 97–2003) pelo xlrd."""
    import xlrd

    try:
        livro = xlrd.open_workbook(file_contents=conteudo)
    except xlrd.XLRDError as erro:
        raise ValueError(f"Não foi possível abrir {nome!r}: {erro}") from erro
    if aba is not None and aba not in livro.sheet_names():
        raise _aba_inexistente(nome, aba, list(livro.sheet_names()))
    folha = livro.sheet_by_name(aba) if aba else livro.sheet_by_index(0)
    linhas = [folha.row_values(i) for i in range(min(folha.nrows, MAX_LINHAS + 2))]
    return _separar(linhas, nome)


def _tabelas_ods(conteudo: bytes) -> list:  # type: ignore[type-arg]
    from odf.opendocument import load
    from odf.table import Table as TabelaOds

    documento = load(BytesIO(conteudo))
    return list(documento.spreadsheet.getElementsByType(TabelaOds))


def _ler_ods(
    conteudo: bytes, nome: str, aba: str | None
) -> tuple[list[str], list[Sequence[object]]]:
    """.ods (LibreOffice) pelo odfpy.

    O ODS comprime células e linhas iguais em "repetidas N vezes" — inclusive
    milhares de linhas vazias no fim da aba. A repetição é expandida com teto,
    e linhas vazias no fim são descartadas.
    """
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
