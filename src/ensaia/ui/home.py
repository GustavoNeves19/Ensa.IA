"""Página inicial da interface web.

Abertura do fluxo da seção 4 (enviar → conferir → mapear → analisar →
resultados → explicar → baixar). Por ora, só a entrada: a marca, uma frase do
que o sistema faz, a trilha dos passos, o envio do arquivo e o aviso de
privacidade (RF-17). Cada passo do fluxo entra depois, um a um, como sua própria
tela.

A assinatura visual da página é a **superfície de resposta** desenhada à mão em
SVG (`_superficie_svg`): curvas de nível concêntricas nos dois verdes da Ufra,
com o ponto ótimo marcado. É o objeto que o DOE calcula para otimizar — e, de
quebra, evoca a topografia amazônica. Fica atrás do conteúdo, sangrando pelo
canto, e se dissolve no papel por uma máscara (ver `tema.aplicar_tema`).
"""

from __future__ import annotations

from nicegui import ui

from ensaia.core.table import Table
from ensaia.ui.ajuda import botao_glossario
from ensaia.ui.analise import construir_analise
from ensaia.ui.tema import TINTA, VERDE
from ensaia.ui.upload import construir_upload

# Os sete passos do fluxo (spec §4). Mostrados como uma trilha discreta — dão ao
# visitante o mapa do caminho sem prometer nada que ainda não existe.
_PASSOS: tuple[tuple[str, str], ...] = (
    ("Enviar", "sua planilha de ensaios"),
    ("Conferir", "a leitura dos dados"),
    ("Mapear", "fatores e respostas"),
    ("Analisar", "o que você escolher"),
    ("Ver", "tabelas e gráficos"),
    ("Explicar", "em texto, se quiser"),
    ("Baixar", "relatório e dados"),
)


def construir_home() -> None:
    """Monta os elementos da página inicial."""
    with ui.element("div").classes("ea-page"):
        ui.html(_superficie_svg()).classes("ea-atmosfera")
        with (
            ui.element("div").classes("ea-col"),
            ui.element("div").classes("ea-main"),
        ):
            _marca()
            _headline()
            _trilha()
            botao_glossario()

            # O container da análise vive abaixo do painel; o upload o preenche
            # (mapear → analisar → resultados) quando uma planilha é lida.
            holder: dict[str, ui.column] = {}

            def ao_carregar(tabela: Table | None, nome: str) -> None:
                destino = holder["analise"]
                destino.clear()
                if tabela is not None:
                    with destino:
                        construir_analise(tabela, nome)

            with ui.element("div").classes("ea-painel"):
                construir_upload(ao_carregar=ao_carregar)
            holder["analise"] = ui.column().classes("w-full ea-analise")

            _privacidade()
            _rodape()


def _marca() -> None:
    with ui.column().classes("gap-0"):
        ui.html(
            f'<div class="ea-marca">'
            f'<span style="color:{TINTA}">Ensa</span>'
            f'<span style="color:{VERDE}">IA</span></div>'
        )
        ui.html(
            '<div class="ea-colofao">Universidade Federal Rural da Amazônia '
            "· Trabalho de Conclusão de Curso</div>"
        )


def _headline() -> None:
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
    itens = "".join(
        f'<div class="ea-passo"><span class="n">{i}</span>'
        f'<span><span class="t">{titulo}</span> '
        f'<span class="d">{detalhe}</span></span></div>'
        for i, (titulo, detalhe) in enumerate(_PASSOS, start=1)
    )
    ui.html(f'<div class="ea-passos">{itens}</div>')


def _privacidade() -> None:
    # Aviso de privacidade (RF-17 / princípio P1): visível já na entrada, como uma
    # ilha recuada e bem tipografada — nada de card com ícone em tile.
    ui.html(
        '<div class="ea-privacidade">'
        '<div class="ea-priv-titulo">Seus dados não saem do seu controle</div>'
        '<div class="ea-priv-texto">Nada é gravado em disco nem em banco. Tudo '
        "vive apenas na memória da sessão e é descartado quando você fecha a "
        "página.</div></div>"
    )


def _rodape() -> None:
    ui.html(
        '<div class="ea-rodape">'
        "<b>EnsaIA</b> · núcleo estatístico offline e reprodutível, "
        "com uma camada de linguagem que narra o resultado sem recalcular nada."
        "<br>Gabriel Henrique Lemos de Athayde · Gustavo Neves da Paz Rafael "
        "· Orientadora: Profa. Dra. Luiza Helena da Silva Martins</div>"
    )


def _superficie_svg() -> str:
    """Curvas de nível de uma superfície de resposta, nos dois verdes da Ufra.

    Elipses concêntricas levemente deslocadas (uma crista até o ótimo), com o
    traço indo do verde oliva (fora) ao verde (dentro) e a opacidade crescendo
    para o centro. No centro, o ponto ótimo: um anel que respira e uma mira.
    Eixos técnicos quase invisíveis dão o tom de "instrumento", sem gritar.
    """
    oliva = (155, 146, 28)
    verde = (64, 165, 81)
    n = 8
    aneis: list[str] = []
    cx = cy = 0.0
    for i in range(n):
        t = i / (n - 1)
        rx = 300 - t * (300 - 26)
        ry = 214 - t * (214 - 18)
        cx = 426 + i * 4
        cy = 208 + i * 3
        r = round(oliva[0] + (verde[0] - oliva[0]) * t)
        g = round(oliva[1] + (verde[1] - oliva[1]) * t)
        b = round(oliva[2] + (verde[2] - oliva[2]) * t)
        op = 0.16 + t * 0.34
        aneis.append(
            f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" '
            f'transform="rotate(-20 {cx:.0f} {cy:.0f})" fill="none" '
            f'stroke="rgb({r},{g},{b})" stroke-opacity="{op:.2f}" stroke-width="1.5"/>'
        )
    # Eixos técnicos discretos (canto inferior esquerdo da leitura).
    ticks_x = "".join(
        f'<path d="M{x} 436 v6" fill="none"/>' for x in (214, 278, 342, 406)
    )
    ticks_y = "".join(
        f'<path d="M150 {y} h-6" fill="none"/>' for y in (372, 308, 244)
    )
    eixos = (
        '<g stroke="rgb(155,146,28)" stroke-opacity="0.14" stroke-width="1.4" '
        'stroke-linecap="round">'
        '<path d="M150 436 H470" fill="none"/>'
        '<path d="M150 436 V168" fill="none"/>'
        + ticks_x
        + ticks_y
        + "</g>"
    )
    # Ponto ótimo: anel que respira + miolo + mira curta.
    otimo = (
        f'<g>'
        f'<circle class="ea-otimo-halo" cx="{cx:.0f}" cy="{cy:.0f}" r="13" '
        f'fill="none" stroke="rgb(64,165,81)" stroke-width="2"/>'
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="3.4" fill="rgb(64,165,81)"/>'
        f'<g stroke="rgb(64,165,81)" stroke-width="1.5" stroke-linecap="round">'
        f'<path d="M{cx - 22:.0f} {cy:.0f} h10"/>'
        f'<path d="M{cx + 12:.0f} {cy:.0f} h10"/>'
        f'<path d="M{cx:.0f} {cy - 22:.0f} v10"/>'
        f'<path d="M{cx:.0f} {cy + 12:.0f} v10"/>'
        f"</g></g>"
    )
    return (
        '<svg viewBox="0 0 640 520" xmlns="http://www.w3.org/2000/svg" '
        'role="img" aria-label="Superfície de resposta com ponto ótimo">'
        f'<g class="ea-superficie">{eixos}{"".join(aneis)}{otimo}</g></svg>'
    )
