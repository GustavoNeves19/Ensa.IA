"""Gráficos do relatório PDF em PNG, desenhados com matplotlib na memória.
Os mesmos da tela, com a mesma paleta; nenhuma conta é feita aqui.
"""

from __future__ import annotations

import math
import textwrap
from collections.abc import Sequence
from io import BytesIO
from typing import Literal

import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from ensaia.core.design import INTERCEPTO, nome_legivel
from ensaia.core.diagnostico import pontos_qq
from ensaia.core.results import AjusteResposta
from ensaia.core.surface import GradeSuperficie
from ensaia.report.theme import TEMA, Tema, cor_mpl

# Gráficos de diagnóstico que o PDF sabe desenhar, na ordem da tela.
DIAGNOSTICOS = ("C6", "D1", "D2", "D3")


def numero_curto(valor: float) -> str:
    """Número curto com vírgula, para rótulos de eixo."""
    if valor == 0 or not math.isfinite(valor):
        return "0"
    texto = f"{valor:.4g}"
    if "e" in texto:
        mantissa, expoente = texto.split("e")
        return f"{mantissa.replace('.', ',')}×10^{int(expoente)}"
    return texto.replace(".", ",")


def grafico_pareto(ajuste: AjusteResposta, *, tema: Tema = TEMA) -> bytes:
    """Pareto dos efeitos padronizados, com o t crítico."""
    efeitos = sorted(
        (c for c in ajuste.coeficientes if c.termo != INTERCEPTO),
        key=lambda c: abs(c.valor_t),
        reverse=True,
    )
    fig = Figure(figsize=(7.0, _altura_termos(efeitos)))
    ax = fig.subplots()
    if not efeitos:
        _vazio(ax, "Sem termos além do intercepto.", tema)
        return _png(fig)

    posicoes = list(range(len(efeitos)))
    cores = [
        cor_mpl(tema.serie if c.significativo else tema.serie_apagada) for c in efeitos
    ]
    ax.barh(posicoes, [abs(c.valor_t) for c in efeitos], color=cores, height=0.62)
    ax.set_yticks(posicoes)
    ax.set_yticklabels([_rotulo_termo(c.termo) for c in efeitos])
    ax.invert_yaxis()  # o maior efeito no topo
    if ajuste.t_critico is not None:  # o valor vai na legenda do PDF
        ax.axvline(
            ajuste.t_critico, color=cor_mpl(tema.tinta), linewidth=1, linestyle="--"
        )
    ax.set_xlabel("|t|: efeito padronizado")
    _titulo(ax, "Pareto dos efeitos", tema)
    _limpar(ax, tema, categorias_y=True)
    return _png(fig)


def grafico_coeficientes(ajuste: AjusteResposta, *, tema: Tema = TEMA) -> bytes:
    """Coeficientes com seus intervalos de confiança."""
    efeitos = [c for c in ajuste.coeficientes if c.termo != INTERCEPTO]
    fig = Figure(figsize=(7.0, _altura_termos(efeitos)))
    ax = fig.subplots()
    if not efeitos:
        _vazio(ax, "Sem termos além do intercepto.", tema)
        return _png(fig)

    posicoes = list(range(len(efeitos)))
    erro_abaixo = [
        c.estimativa - c.ic_inferior if c.ic_inferior is not None else 0.0
        for c in efeitos
    ]
    erro_acima = [
        c.ic_superior - c.estimativa if c.ic_superior is not None else 0.0
        for c in efeitos
    ]
    ax.axvline(0.0, color=cor_mpl(tema.cinza), linewidth=0.8)
    for i, c in enumerate(efeitos):
        cor = cor_mpl(tema.serie if c.significativo else tema.serie_apagada)
        ax.errorbar(
            [c.estimativa],
            [i],
            xerr=[[erro_abaixo[i]], [erro_acima[i]]],
            fmt="o",
            color=cor,
            ecolor=cor,
            elinewidth=1.4,
            capsize=3,
            markersize=6,
        )
    ax.set_yticks(posicoes)
    ax.set_yticklabels([_rotulo_termo(c.termo) for c in efeitos])
    ax.invert_yaxis()
    ax.set_xlabel("Coeficiente (escala codificada)")
    _titulo(ax, "Coeficientes e intervalos de confiança", tema)
    _limpar(ax, tema, categorias_y=True)
    return _png(fig)


def grafico_diagnostico(
    ajuste: AjusteResposta, quais: Sequence[str], *, tema: Tema = TEMA
) -> bytes | None:
    """Painel de diagnóstico com os gráficos marcados."""
    d = ajuste.diagnostico
    if d is None:
        return None
    pedidos = [q for q in DIAGNOSTICOS if q in quais and (q != "D3" or d.ordem)]
    if not pedidos:
        return None
    colunas = 1 if len(pedidos) == 1 else 2
    linhas = math.ceil(len(pedidos) / colunas)
    fig = Figure(figsize=(7.0 if colunas == 2 else 5.0, 3.1 * linhas))
    eixos = fig.subplots(linhas, colunas, squeeze=False).ravel()
    for ax, qual in zip(eixos, pedidos, strict=False):
        _DESENHOS[qual](ax, ajuste, tema)
        _limpar(ax, tema, grade_y=True)
    for ax in eixos[len(pedidos) :]:
        ax.axis("off")
    fig.tight_layout(h_pad=1.6, w_pad=2.0)
    return _png(fig)


def _previsto_observado(ax: Axes, ajuste: AjusteResposta, tema: Tema) -> None:
    """Gráfico previsto × observado."""
    assert ajuste.diagnostico is not None
    obs, prev = ajuste.diagnostico.observados, ajuste.diagnostico.preditos
    baixo, alto = min(obs + prev), max(obs + prev)
    folga = (alto - baixo) * 0.06 or 1.0
    ax.plot(
        [baixo - folga, alto + folga],
        [baixo - folga, alto + folga],
        color=cor_mpl(tema.cinza),
        linewidth=0.9,
        linestyle="--",
    )
    _pontos(ax, obs, prev, tema)
    ax.set_xlabel("Observado")
    ax.set_ylabel("Previsto")
    _titulo(ax, "Previsto × observado", tema, tamanho=10)


def _residuos_previsto(ax: Axes, ajuste: AjusteResposta, tema: Tema) -> None:
    """Gráfico resíduos × previsto."""
    assert ajuste.diagnostico is not None
    ax.axhline(0.0, color=cor_mpl(tema.cinza), linewidth=0.9, linestyle="--")
    _pontos(ax, ajuste.diagnostico.preditos, ajuste.diagnostico.residuos, tema)
    ax.set_xlabel("Previsto")
    ax.set_ylabel("Resíduo")
    _titulo(ax, "Resíduos × previsto", tema, tamanho=10)


def _normalidade(ax: Axes, ajuste: AjusteResposta, tema: Tema) -> None:
    """Gráfico Q-Q normal dos resíduos."""
    d = ajuste.diagnostico
    assert d is not None
    qq = pontos_qq(d.residuos)
    if qq.teoricos:
        extremos = [min(qq.teoricos), max(qq.teoricos)]
        ax.plot(
            extremos,
            [qq.reta_intercepto + qq.reta_inclinacao * x for x in extremos],
            color=cor_mpl(tema.cinza),
            linewidth=0.9,
            linestyle="--",
        )
        _pontos(ax, qq.teoricos, qq.amostrais, tema)
    ax.set_xlabel("Quantil normal teórico")
    ax.set_ylabel("Resíduo")
    _titulo(ax, "Normalidade (Q-Q)", tema, tamanho=10)


def _residuos_ordem(ax: Axes, ajuste: AjusteResposta, tema: Tema) -> None:
    """Gráfico dos resíduos na ordem de execução."""
    d = ajuste.diagnostico
    assert d is not None and d.ordem is not None
    pares = sorted(zip(d.ordem, d.residuos, strict=True))
    ax.axhline(0.0, color=cor_mpl(tema.cinza), linewidth=0.9, linestyle="--")
    ax.plot(
        [o for o, _ in pares],
        [r for _, r in pares],
        color=cor_mpl(tema.serie),
        linewidth=1.2,
        marker="o",
        markersize=5,
        markeredgecolor=cor_mpl(tema.branco),
    )
    ax.set_xlabel("Ordem de execução")
    ax.set_ylabel("Resíduo")
    _titulo(ax, "Resíduos × ordem", tema, tamanho=10)


_DESENHOS = {
    "C6": _previsto_observado,
    "D1": _residuos_previsto,
    "D2": _normalidade,
    "D3": _residuos_ordem,
}


def grafico_contorno(
    grade: GradeSuperficie,
    *,
    rotulo_x: str,
    rotulo_y: str,
    destaque: tuple[float, float] | None = None,
    tema: Tema = TEMA,
) -> bytes:
    """Curvas de contorno da resposta prevista."""
    x = np.asarray(grade.valores_x)
    y = np.asarray(grade.valores_y)
    z = np.asarray(grade.z)
    niveis = np.linspace(float(z.min()), float(z.max()), len(tema.rampa) + 1)
    if niveis[0] == niveis[-1]:
        niveis = np.linspace(niveis[0] - 1, niveis[0] + 1, len(tema.rampa) + 1)
    fig = Figure(figsize=(6.2, 4.4))
    ax = fig.subplots()
    preenchido = ax.contourf(x, y, z, levels=niveis, colors=list(tema.rampa))
    linhas = ax.contour(
        x, y, z, levels=niveis[1:-1], colors=[cor_mpl(tema.branco)], linewidths=0.6
    )
    ax.clabel(linhas, fmt=numero_curto, fontsize=7, colors=[cor_mpl(tema.branco)])
    if destaque is not None:
        ax.scatter(
            [destaque[0]],
            [destaque[1]],
            s=70,
            marker="o",
            facecolors=cor_mpl(tema.branco),
            edgecolors=cor_mpl(tema.tinta),
            linewidths=1.4,
            zorder=4,
            clip_on=False,  # o ótimo cai muito na borda da região
        )
        # O rótulo vai para o lado de dentro: no canto, ele sairia do gráfico.
        dx = -8 if destaque[0] > (x.min() + x.max()) / 2 else 8
        dy = -10 if destaque[1] > (y.min() + y.max()) / 2 else 8
        ax.annotate(
            "ótimo",
            destaque,
            xytext=(dx, dy),
            textcoords="offset points",
            ha="right" if dx < 0 else "left",
            va="top" if dy < 0 else "bottom",
            fontsize=8,
            color=cor_mpl(tema.branco),
            fontweight="bold",
        )
    barra = fig.colorbar(preenchido, ax=ax, shrink=0.9)
    barra.set_label(f"{nome_legivel(grade.resposta)} prevista", fontsize=9)
    barra.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: numero_curto(v)))
    barra.ax.tick_params(labelsize=8, colors=cor_mpl(tema.tinta))
    barra.outline.set_visible(False)
    ax.set_xlabel(rotulo_x)
    ax.set_ylabel(rotulo_y)
    _titulo(ax, "Curvas de contorno", tema)
    _limpar(ax, tema, grade_x=False)
    return _png(fig)


def grafico_superficie_3d(
    grade: GradeSuperficie,
    *,
    rotulo_x: str,
    rotulo_y: str,
    tema: Tema = TEMA,
) -> bytes:
    """Superfície de resposta em 3D."""
    xx, yy = np.meshgrid(np.asarray(grade.valores_x), np.asarray(grade.valores_y))
    z = np.asarray(grade.z)
    fig = Figure(figsize=(6.2, 4.6))
    ax = fig.add_subplot(projection="3d")
    mapa = LinearSegmentedColormap.from_list("ensaia", list(tema.rampa))
    ax.plot_surface(xx, yy, z, cmap=mapa, linewidth=0, antialiased=True)
    ax.view_init(elev=24, azim=-58)
    formato = FuncFormatter(lambda v, _: numero_curto(v))
    for eixo, rotulo in (
        (ax.xaxis, rotulo_x),
        (ax.yaxis, rotulo_y),
        (ax.zaxis, f"{nome_legivel(grade.resposta)} prevista"),
    ):
        eixo.set_major_formatter(formato)
        eixo.set_label_text(rotulo, fontsize=8, color=cor_mpl(tema.tinta))
        eixo.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.tick_params(labelsize=7, colors=cor_mpl(tema.tinta))
    _titulo(ax, "Superfície de resposta", tema)
    return _png(fig)


# --- Acabamento comum ---------------------------------------------------------


def _rotulo_termo(termo: str) -> str:
    """Nome do termo quebrado em linhas curtas."""
    return textwrap.fill(nome_legivel(termo), width=24, break_long_words=False)


def _altura_termos(efeitos: Sequence[object]) -> float:
    """Altura do gráfico conforme o número de termos."""
    return max(1.8, 0.40 * len(efeitos) + 1.0)


def _pontos(ax: Axes, x: Sequence[float], y: Sequence[float], tema: Tema) -> None:
    """Desenha os pontos dos ensaios."""
    ax.scatter(
        x,
        y,
        s=30,
        color=cor_mpl(tema.serie),
        edgecolors=cor_mpl(tema.branco),
        linewidths=0.8,
        zorder=3,
    )


def _titulo(ax: Axes, texto: str, tema: Tema, *, tamanho: int = 11) -> None:
    """Título do gráfico no estilo do tema."""
    ax.set_title(
        texto,
        loc="left",
        fontweight="bold",
        fontsize=tamanho,
        color=cor_mpl(tema.tinta),
    )


def _limpar(
    ax: Axes,
    tema: Tema,
    *,
    grade_x: bool = True,
    grade_y: bool = False,
    categorias_y: bool = False,
) -> None:
    """Aplica o visual sóbrio do tema aos eixos."""
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(cor_mpl(tema.cinza))
    ax.tick_params(colors=cor_mpl(tema.tinta), labelsize=8)
    ax.xaxis.label.set_color(cor_mpl(tema.tinta))
    ax.yaxis.label.set_color(cor_mpl(tema.tinta))
    # Eixos numéricos com vírgula decimal.
    formato = FuncFormatter(lambda v, _: numero_curto(v))
    ax.xaxis.set_major_formatter(formato)
    if not categorias_y:
        ax.yaxis.set_major_formatter(formato)
    linhas_de_grade: dict[tuple[bool, bool], Literal["both", "x", "y"]] = {
        (True, True): "both",
        (True, False): "x",
        (False, True): "y",
    }
    if grade_x or grade_y:
        ax.grid(
            axis=linhas_de_grade[(grade_x, grade_y)],
            color=cor_mpl(tema.grade),
            linewidth=0.6,
        )
    ax.set_axisbelow(True)


def _vazio(ax: Axes, mensagem: str, tema: Tema) -> None:
    """Mostra uma mensagem no lugar de um gráfico sem dados."""
    ax.text(0.5, 0.5, mensagem, ha="center", va="center", color=cor_mpl(tema.cinza))
    ax.axis("off")


def _png(fig: Figure) -> bytes:
    """Salva a figura em PNG e libera a memória."""
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    fig.clear()
    return buffer.getvalue()
