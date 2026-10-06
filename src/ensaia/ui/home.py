"""Página inicial da interface web.

Abertura do fluxo da seção 4 (enviar → conferir → mapear → analisar →
resultados → explicar → baixar). Por ora, só a entrada: a marca, uma frase do
que o sistema faz, a trilha dos passos e o aviso de privacidade (RF-17). Cada
passo do fluxo entra depois, um a um, como sua própria tela.
"""

from __future__ import annotations

from nicegui import ui

from ensaia.ui.tema import ACENTO, CINZA, TINTA

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
    with ui.column().classes("w-full max-w-3xl mx-auto px-6 py-20 gap-10"):
        _marca()
        _trilha()
        _privacidade()


def _marca() -> None:
    with ui.row().classes("items-baseline gap-0"):
        ui.label("Ensa").style(
            f"color:{TINTA};font-size:3.25rem;font-weight:700;letter-spacing:-0.02em"
        )
        ui.label("IA").style(
            f"color:{ACENTO};font-size:3.25rem;font-weight:700;letter-spacing:-0.02em"
        )
    ui.label(
        "Delineamento de experimentos e análise de dados químicos — "
        "do arquivo ao relatório, sem instalar nada."
    ).style(f"color:{CINZA};font-size:1.05rem;max-width:34rem;line-height:1.5")


def _trilha() -> None:
    # A ordem dos passos é dada pela numeração (não por setas, que ficariam
    # órfãs ao quebrar de linha, nem por um trilho vertical — um tell gasto).
    with ui.row().classes("flex-wrap gap-x-10 gap-y-5"):
        for i, (titulo, detalhe) in enumerate(_PASSOS, start=1):
            with ui.row().classes("items-baseline gap-2"):
                ui.label(f"{i}").style(
                    f"color:{ACENTO};font-weight:700;font-size:0.8rem;"
                    "font-variant-numeric:tabular-nums;min-width:0.9rem"
                )
                with ui.column().classes("gap-0"):
                    ui.label(titulo).style(
                        f"color:{TINTA};font-weight:600;font-size:0.95rem"
                    )
                    ui.label(detalhe).style(f"color:{CINZA};font-size:0.78rem")


def _privacidade() -> None:
    # Aviso de privacidade (RF-17 / princípio P1): visível já na entrada. Nada de
    # card com ícone em tile — uma barra de acento à esquerda e texto claro.
    with ui.column().classes("gap-1 mt-2").style(
        f"border-left:3px solid {ACENTO};padding:0.75rem 1rem;"
        "background-color:rgba(26,95,111,0.05);border-radius:0 6px 6px 0"
    ):
        ui.label("Seus dados não saem do seu controle").style(
            f"color:{TINTA};font-weight:600;font-size:0.95rem"
        )
        ui.label(
            "Nada é gravado em disco nem em banco. Tudo vive apenas na "
            "memória da sessão e é descartado quando você fecha a página."
        ).style(f"color:{CINZA};font-size:0.85rem;line-height:1.45")
