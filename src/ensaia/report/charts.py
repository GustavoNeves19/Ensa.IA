"""Gráficos do relatório, renderizados em PNG na memória.

Usa o matplotlib pelo objeto `Figure` direto (sem pyplot), que é a forma
recomendada em servidor: não mexe no estado global e libera a figura ao fim de
cada gráfico. É importado só aqui, na camada de apresentação — o núcleo e a
camada de IA nunca o veem.

Os gráficos saem do próprio `AjusteResposta` (o contrato congelado): o Pareto
usa a magnitude |t| de cada termo; o de coeficientes, as estimativas e seus
intervalos de confiança. Nenhum recálculo estatístico acontece aqui.
"""

from __future__ import annotations

from io import BytesIO

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ensaia.core.design import INTERCEPTO
from ensaia.core.results import AjusteResposta
from ensaia.report.theme import TEMA, Tema, cor_mpl


def grafico_pareto(ajuste: AjusteResposta, *, tema: Tema = TEMA) -> bytes:
    """Pareto dos efeitos: |t| por termo, do maior para o menor.

    Barras em acento para os termos significativos e em cinza para os demais,
    deixando a leitura "o que importa no modelo" imediata.
    """
    efeitos = sorted(
        (c for c in ajuste.coeficientes if c.termo != INTERCEPTO),
        key=lambda c: abs(c.valor_t),
        reverse=True,
    )
    fig = Figure(figsize=(7.0, max(1.6, 0.42 * len(efeitos) + 0.9)))
    ax = fig.subplots()
    if not efeitos:
        _vazio(ax, "Sem termos além do intercepto.", tema)
        return _png(fig)

    posicoes = range(len(efeitos))
    cores = [
        cor_mpl(tema.acento if c.significativo else tema.cinza_claro) for c in efeitos
    ]
    ax.barh(list(posicoes), [abs(c.valor_t) for c in efeitos], color=cores)
    ax.set_yticks(list(posicoes))
    ax.set_yticklabels([c.termo for c in efeitos])
    ax.invert_yaxis()  # o maior efeito no topo
    ax.set_xlabel("|t| — magnitude do efeito padronizado")
    ax.set_title("Pareto dos efeitos", loc="left", fontweight="bold")
    _limpar(ax, tema)
    return _png(fig)


def grafico_coeficientes(ajuste: AjusteResposta, *, tema: Tema = TEMA) -> bytes:
    """Coeficientes e seus intervalos de confiança, em escala codificada.

    Cada termo vira um ponto (estimativa) com barra de erro (IC); a linha
    vertical no zero separa efeito positivo de negativo. Termos sem IC no
    contrato aparecem só como ponto.
    """
    efeitos = [c for c in ajuste.coeficientes if c.termo != INTERCEPTO]
    fig = Figure(figsize=(7.0, max(1.6, 0.42 * len(efeitos) + 0.9)))
    ax = fig.subplots()
    if not efeitos:
        _vazio(ax, "Sem termos além do intercepto.", tema)
        return _png(fig)

    posicoes = list(range(len(efeitos)))
    estimativas = [c.estimativa for c in efeitos]
    erro_abaixo = [
        c.estimativa - c.ic_inferior if c.ic_inferior is not None else 0.0
        for c in efeitos
    ]
    erro_acima = [
        c.ic_superior - c.estimativa if c.ic_superior is not None else 0.0
        for c in efeitos
    ]
    ax.axvline(0.0, color=cor_mpl(tema.cinza), linewidth=0.8)
    ax.errorbar(
        estimativas,
        posicoes,
        xerr=[erro_abaixo, erro_acima],
        fmt="o",
        color=cor_mpl(tema.acento),
        ecolor=cor_mpl(tema.cinza),
        capsize=3,
        linestyle="none",
    )
    ax.set_yticks(posicoes)
    ax.set_yticklabels([c.termo for c in efeitos])
    ax.invert_yaxis()
    ax.set_xlabel("Coeficiente (escala codificada)")
    ax.set_title(
        "Coeficientes e intervalos de confiança", loc="left", fontweight="bold"
    )
    _limpar(ax, tema)
    return _png(fig)


def _limpar(ax: Axes, tema: Tema) -> None:
    """Aplica o visual sóbrio do tema: sem molduras supérfluas, cinzas calmos."""
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(cor_mpl(tema.cinza))
    ax.tick_params(colors=cor_mpl(tema.tinta), labelsize=9)
    ax.xaxis.label.set_color(cor_mpl(tema.tinta))
    ax.title.set_color(cor_mpl(tema.tinta))
    ax.grid(axis="x", color=cor_mpl(tema.cinza_claro), linewidth=0.6)
    ax.set_axisbelow(True)


def _vazio(ax: Axes, mensagem: str, tema: Tema) -> None:
    ax.text(0.5, 0.5, mensagem, ha="center", va="center", color=cor_mpl(tema.cinza))
    ax.axis("off")


def _png(fig: Figure) -> bytes:
    """Serializa a figura em PNG e libera os recursos."""
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    fig.clear()
    return buffer.getvalue()
