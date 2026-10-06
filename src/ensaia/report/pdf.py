"""A folha do relatório: uma subclasse de FPDF com a cara do EnsaIA.

Concentra o que se repete em toda página (cabeçalho discreto e o rodapé exigido
pela spec §13) e oferece os tijolos que o `builder` usa para montar as seções:
título de seção, parágrafo, tabela e imagem. Registra a fonte Unicode DejaVu
para os acentos do português e os símbolos dos fatos (≥, ², −).

Números saem no padrão brasileiro (vírgula decimal), com as casas definidas no
tema por grandeza.
"""

from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO

from fpdf import FPDF
from fpdf.fonts import FontFace

from ensaia.report.theme import TEMA, Tema


def numero_ptbr(valor: float, casas: int) -> str:
    """Número com casas fixas e vírgula decimal."""
    return f"{valor:.{casas}f}".replace(".", ",")


class RelatorioPDF(FPDF):
    """Documento do relatório. Instancie, use as seções do builder e `output()`."""

    def __init__(self, *, versao: str, tema: Tema = TEMA) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.versao = versao
        self.tema = tema
        self.mostrar_cabecalho = False  # ligado após a capa
        self.set_margins(tema.margem, tema.margem, tema.margem)
        self.set_auto_page_break(auto=True, margin=tema.margem)
        self.add_font(tema.familia, "", str(tema.arquivo_regular))
        self.add_font(tema.familia, "B", str(tema.arquivo_negrito))
        self.add_font(tema.familia, "I", str(tema.arquivo_italico))
        self.set_text_color(*tema.tinta)

    # -- repetições de página ----------------------------------------------

    def header(self) -> None:
        if not self.mostrar_cabecalho:
            return
        self.set_font(self.tema.familia, "", 8)
        self.set_text_color(*self.tema.cinza)
        self.cell(0, 6, "EnsaIA — relatório de análise", align="R")
        self.ln(8)
        self.set_draw_color(*self.tema.cinza_claro)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)
        self.set_text_color(*self.tema.tinta)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_draw_color(*self.tema.cinza_claro)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1)
        self.set_font(self.tema.familia, "I", 7)
        self.set_text_color(*self.tema.cinza)
        self.cell(
            0,
            6,
            f"Gerado por EnsaIA v{self.versao} — nenhum dado foi armazenado.",
            align="L",
        )
        self.cell(0, 6, f"{self.page_no()}", align="R")
        self.set_text_color(*self.tema.tinta)

    # -- tijolos de conteúdo -----------------------------------------------

    def titulo_secao(self, texto: str) -> None:
        self.ln(2)
        self.set_font(self.tema.familia, "B", 13)
        self.set_text_color(*self.tema.acento)
        self.multi_cell(0, 7, texto, new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_text_color(*self.tema.tinta)
        self.ln(1)

    def paragrafo(self, texto: str, *, tamanho: int = 10) -> None:
        # Alinhamento à esquerda (bandeira): justificar abriria vãos largos entre
        # as palavras — um defeito visível em parágrafos curtos.
        self.set_font(self.tema.familia, "", tamanho)
        self.multi_cell(0, 5.2, texto, new_x="LMARGIN", new_y="NEXT", align="L")
        self.ln(1.5)

    def rotulo_valor(self, rotulo: str, valor: str) -> None:
        """Uma linha 'Rótulo: valor', com o rótulo em negrito."""
        self.set_font(self.tema.familia, "B", 10)
        largura = self.get_string_width(rotulo + ": ") + 1
        self.cell(largura, 5.6, f"{rotulo}:")
        self.set_font(self.tema.familia, "", 10)
        self.multi_cell(0, 5.6, f" {valor}", new_x="LMARGIN", new_y="NEXT", align="L")

    def tabela(
        self,
        cabecalhos: Sequence[str],
        linhas: Sequence[Sequence[str]],
        larguras: Sequence[float],
    ) -> None:
        """Tabela com cabeçalho em acento e zebra leve; quebra texto longo.

        Usa a API `table()` do fpdf2, que embrulha o conteúdo de cada célula em
        várias linhas quando preciso — essencial para nomes de termo longos como
        `dose_catalisador:concentracao_levofloxacino`. A primeira coluna fica à
        esquerda (texto); as demais, centralizadas (números).
        """
        estilo_cabecalho = FontFace(
            emphasis="BOLD", color=self.tema.branco, fill_color=self.tema.acento
        )
        alinhamentos = ["LEFT"] + ["CENTER"] * (len(cabecalhos) - 1)
        self.set_font(self.tema.familia, "", 9)
        with self.table(
            col_widths=tuple(larguras),
            text_align=tuple(alinhamentos),
            line_height=6,
            headings_style=estilo_cabecalho,
            cell_fill_color=self.tema.cinza_claro,
            cell_fill_mode="ROWS",
        ) as tabela:
            cabecalho = tabela.row()
            for titulo in cabecalhos:
                cabecalho.cell(titulo)
            for linha in linhas:
                registro = tabela.row()
                for valor in linha:
                    registro.cell(valor)
        self.ln(2)

    def imagem_png(self, png: bytes, *, largura: float | None = None) -> None:
        if largura is None:
            largura = self.w - self.l_margin - self.r_margin
        self.image(BytesIO(png), w=largura)
        self.ln(2)
