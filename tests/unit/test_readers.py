from __future__ import annotations

from pathlib import Path

from ensaia.io.readers import ler_dados


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
