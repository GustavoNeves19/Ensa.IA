from __future__ import annotations

from pathlib import Path

from lyra.io.readers import ler_dados


def test_ler_dados_aceita_csv_brasileiro_com_comentario(tmp_path: Path) -> None:
    arquivo = tmp_path / "experimento.csv"
    arquivo.write_text(
        "# Exportado da planilha\nconcentracao;resposta\n1,5;82,3\n",
        encoding="utf-8",
    )

    dados = ler_dados(arquivo)

    assert list(dados.columns) == ["concentracao", "resposta"]
    assert dados.loc[0, "concentracao"] == 1.5
    assert dados.loc[0, "resposta"] == 82.3
