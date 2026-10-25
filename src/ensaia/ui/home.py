"""Página inicial: abertura, passos, envio da planilha, glossário e privacidade.
A área de análise aparece abaixo quando uma planilha é lida.
"""

from __future__ import annotations

from datetime import date

from nicegui import ui

from ensaia.core.table import Table
from ensaia.ui.ajuda import botao_glossario, seletor_dicas
from ensaia.ui.analise import construir_analise
from ensaia.ui.tema import OLIVA_ESCURO, TINTA, VERDE, VERDE_ESCURO
from ensaia.ui.upload import construir_upload

# Os três passos em destaque: verbo, o que faz e o ícone.
_PASSOS: tuple[tuple[str, str, str], ...] = (
    ("Envie", "sua planilha de ensaios", "upload_file"),
    ("Confira", "a leitura dos dados", "fact_check"),
    ("Baixe", "relatório e dados", "download"),
)


def construir_home() -> None:
    """Monta a página inicial."""
    with ui.element("div").classes("ea-page"), ui.element("div").classes("ea-col"):
        # Abertura em duas colunas: texto à esquerda, passos à direita.
        with ui.element("div").classes("ea-abertura"):
            with ui.element("div").classes("ea-hero"):
                _marca()
                _headline()
                seletor_dicas()
            _trilha()
        _conteudo()


def _conteudo() -> None:
    """Envio da planilha, glossário, área de análise, privacidade e rodapé."""
    with ui.element("div").classes("ea-main"):
        # A área de análise fica abaixo e é preenchida quando a planilha é lida.
        holder: dict[str, ui.column] = {}

        def ao_carregar(tabela: Table | None, nome: str) -> None:
            """Monta a tela de análise para a planilha lida."""
            destino = holder["analise"]
            destino.clear()
            if tabela is not None:
                with destino:
                    construir_analise(tabela, nome)

        with ui.element("div").classes("ea-painel"):
            construir_upload(ao_carregar=ao_carregar)
        botao_glossario()
        holder["analise"] = ui.column().classes("w-full ea-analise")

        _privacidade()
        _rodape()


def _marca() -> None:
    """Logotipo EnsaIA."""
    ui.html(
        f'<div class="ea-marca" role="img" aria-label="EnsaIA">'
        f'<span style="color:{TINTA}">Ensa</span>'
        f'<span style="color:{VERDE}">IA</span></div>'
    )


def _headline() -> None:
    """Título e texto que explicam o sistema."""
    ui.html(
        '<div class="ea-headline">Experimentos químicos, '
        '<span class="ea-ital">analisados e explicados.</span></div>'
    )
    ui.html(
        '<div class="ea-sub">Envie a planilha dos seus ensaios. O EnsaIA faz o '
        "delineamento, a análise estatística e o relatório — offline, sem "
        "instalar nada e sem mandar seus dados para lugar nenhum.</div>"
    )


def _trilha() -> None:
    """Passos Envie, Confira e Baixe com os números."""
    total = len(_PASSOS)
    itens = "".join(
        f'<li class="ea-passo" style="--cor:{_cor_passo(i, total)}">'
        f'<span class="ea-passo-num" aria-hidden="true">{i + 1:02d}</span>'
        f'<span class="ea-passo-circulo">'
        f'<i class="material-icons" aria-hidden="true" translate="no">{icone}</i>'
        f"</span>"
        f'<span class="ea-passo-corpo">'
        f'<span class="t">{titulo}</span> <span class="d">{detalhe}</span>'
        f"</span></li>"
        for i, (titulo, detalhe, icone) in enumerate(_PASSOS)
    )
    ui.html(
        f'<ol class="ea-passos" aria-label="Como funciona, em sequência">{itens}</ol>'
    )


def _cor_passo(indice: int, total: int) -> str:
    """Cor do círculo de um passo, entre as duas cores da marca."""
    inicio, fim = _hex_para_rgb(VERDE_ESCURO), _hex_para_rgb(OLIVA_ESCURO)
    t = indice / (total - 1) if total > 1 else 0.0
    r, g, b = (round(a + (z - a) * t) for a, z in zip(inicio, fim, strict=True))
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_para_rgb(cor: str) -> tuple[int, int, int]:
    """Converte cor hexadecimal em RGB."""
    cor = cor.lstrip("#")
    return int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16)


def _privacidade() -> None:
    # Aviso de privacidade visível já na entrada.
    """Aviso de que os dados não são guardados."""
    ui.html(
        '<div class="ea-privacidade">'
        '<div class="ea-priv-titulo">Seus dados não saem do seu controle</div>'
        '<div class="ea-priv-texto">Nada é gravado em disco nem em banco. Tudo '
        "vive apenas na memória da sessão e é descartado quando você fecha a "
        "página.</div></div>"
    )


def _rodape() -> None:
    """Rodapé com descrição e licença."""
    ui.html(
        '<footer class="ea-rodape">'
        '<div class="ea-rodape-sobre"><b>EnsaIA</b> analisa experimentos químicos '
        "planejados (DOE), encontra a melhor condição e explica o resultado em "
        "linguagem simples.</div>"
        f'<div class="ea-rodape-direitos">© {date.today().year} EnsaIA · '
        "Código aberto sob a licença MIT.</div></footer>"
    )
