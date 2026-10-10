from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from ensaia.io.readers import ler_dados, ler_dados_de_bytes


def test_ler_dados_aceita_csv_brasileiro_com_comentario(tmp_path: Path) -> None:
    arquivo = tmp_path / "experimento.csv"
    arquivo.write_text(
        "# Exportado da planilha\nconcentracao;resposta\n1,5;82,3\n",
        encoding="utf-8",
    )

    dados = ler_dados(arquivo)

    assert dados.colunas == ("concentracao", "resposta")
    assert dados.coluna("concentracao")[0] == 1.5
    assert dados.coluna("resposta")[0] == 82.3


# --- leitura a partir de bytes em memória (interface web, princípio P1) --------


def test_de_bytes_csv_brasileiro() -> None:
    conteudo = b"concentracao;resposta\n1,5;82,3\n"
    dados = ler_dados_de_bytes(conteudo, "experimento.csv")
    assert dados.colunas == ("concentracao", "resposta")
    assert dados.coluna("concentracao")[0] == 1.5


def test_de_bytes_tsv_detecta_tabulacao() -> None:
    conteudo = b"x\ty\n1\t2\n3\t4\n"
    dados = ler_dados_de_bytes(conteudo, "dados.tsv")
    assert dados.colunas == ("x", "y")
    assert list(dados.coluna("y")) == [2.0, 4.0]


def test_de_bytes_decodifica_latin1() -> None:
    conteudo = "fração;y\n0,5;1\n".encode("latin-1")
    dados = ler_dados_de_bytes(conteudo, "acento.csv")
    assert dados.colunas == ("fração", "y")


def test_de_bytes_xlsx_em_memoria() -> None:
    from openpyxl import Workbook

    livro = Workbook()
    aba = livro.active
    assert aba is not None
    aba.append(["temperatura", "rendimento"])
    aba.append([80, 92.5])
    buffer = BytesIO()
    livro.save(buffer)

    dados = ler_dados_de_bytes(buffer.getvalue(), "ensaios.xlsx")
    assert dados.colunas == ("temperatura", "rendimento")
    assert dados.coluna("rendimento")[0] == 92.5


def test_de_bytes_formato_nao_suportado() -> None:
    with pytest.raises(ValueError, match="não suportado"):
        ler_dados_de_bytes(b"qualquer coisa", "relatorio.pdf")


def test_de_bytes_colunas_repetidas_ganham_sufixo() -> None:
    dados = ler_dados_de_bytes(b"x;x\n1;2\n", "dup.csv")
    assert dados.colunas == ("x", "x (2)")


def test_linha_de_titulo_acima_do_cabecalho_e_pulada() -> None:
    conteudo = (
        b";Variaveis independentes;;Variaveis dependentes\n"
        b"Ensaio;Tempo;pH;Rendimento\n1;30;5;61,2\n2;60;7;70,4\n"
    )
    dados = ler_dados_de_bytes(conteudo, "titulo.csv")
    assert dados.colunas == ("Ensaio", "Tempo", "pH", "Rendimento")
    assert len(dados) == 2


def test_tabela_embaixo_da_matriz_nao_vira_ensaio() -> None:
    conteudo = (
        b"ensaio,tempo,rend\n1,30,61.2\n2,60,70.4\n,,\n,,\n"
        b"Composicao do caroco,,\numidade,9.8,\n"
    )
    dados = ler_dados_de_bytes(conteudo, "duas_tabelas.csv")
    assert len(dados) == 2 and dados.e_numerica("tempo")


def test_coluna_sem_nome_com_dados_ganha_nome_e_sem_dados_some() -> None:
    dados = ler_dados_de_bytes(b";x;;\n1;2;;\n2;3;;\n", "sem_nome.csv")
    assert dados.colunas == ("Coluna 1", "x")


def test_de_bytes_sem_ensaios() -> None:
    with pytest.raises(ValueError, match="não contém ensaios"):
        ler_dados_de_bytes(b"x;y\n", "vazio.csv")
