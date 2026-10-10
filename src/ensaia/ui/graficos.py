"""Opções ECharts dos gráficos de resultado (spec §9: B2, C6, D1, D2, E1, E2).

Cada função recebe dados JÁ CALCULADOS pelo núcleo (o `AjusteResposta` congelado,
os pontos do Q-Q, a grade da superfície) e devolve o dicionário de opções que o
`ui.echart` desenha. Nenhuma estatística é feita aqui: só se escolhe forma, cor e
texto. Por serem funções puras (dados → dict), dá para testá-las sem navegador.

Regras visuais (skill de visualização + lei anti-slop): marcas finas, grade em
linha fina e sólida, texto sempre nas cores de texto (nunca na cor da série),
números no padrão brasileiro, legenda só quando há duas séries, e uma tabela
equivalente ao lado de todo gráfico (na própria tela) para quem não lê cor.
"""

from __future__ import annotations

import math
from typing import Any

from ensaia.core.design import INTERCEPTO
from ensaia.core.diagnostico import PontosQQ
from ensaia.core.results import AjusteResposta
from ensaia.core.surface import GradeSuperficie
from ensaia.ui.tema import (
    CINZA,
    GRADE,
    LINHA,
    PAPEL_ALTO,
    RAMPA,
    REFERENCIA,
    SERIE,
    SERIE_APAGADA,
    TINTA,
)

Opcoes = dict[str, Any]

# Formatação pt-BR feita no navegador. As chaves com ":" na frente viram função
# JavaScript na NiceGUI (`convertDynamicProperties`).
_FMT_JS = (
    "(v) => (typeof v === 'number' && isFinite(v))"
    " ? v.toLocaleString('pt-BR', {maximumFractionDigits: 3}) : v"
)
_FONTE = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def nome_legivel(termo: str) -> str:
    """Termo canônico em leitura humana: "a:b" → "a × b", "a^2" → "a²", "_" → " "."""
    texto = termo.replace("^2", "²").replace("^3", "³").replace(":", " × ")
    return texto.replace("_", " ")


def _base() -> Opcoes:
    """Pedaços comuns: fundo transparente, fonte do corpo, tooltip da marca."""
    return {
        "backgroundColor": "transparent",
        "textStyle": {"fontFamily": _FONTE, "color": TINTA},
        # Sem animação de entrada: o gráfico nasce pronto (nada depende de uma
        # animação rodar para aparecer). A transição fica para as mudanças de
        # estado, como mover o fator fixo da superfície.
        "animationDuration": 0,
        "animationDurationUpdate": 350,
        "tooltip": {
            "backgroundColor": PAPEL_ALTO,
            "borderColor": LINHA,
            "borderWidth": 1,
            "padding": [8, 11],
            "textStyle": {"color": TINTA, "fontSize": 12, "fontFamily": _FONTE},
            # Sombra curta e direcional, tingida de verde-mata — nunca um halo.
            "extraCssText": (
                "border-radius:10px;box-shadow:0 8px 18px -12px rgba(14,58,38,.55);"
            ),
        },
    }


def _eixo_valor(
    nome: str, *, escala: bool = True, pontas: bool = True
) -> Opcoes:
    """Eixo numérico recessivo. `pontas=False` esconde os rótulos de mínimo e
    máximo quando a faixa é fixada à mão (senão aparecem números quebrados
    como 44,981 nas bordas)."""
    return {
        "type": "value",
        "name": nome,
        "nameLocation": "middle",
        "nameGap": 34,
        "nameTextStyle": {"color": CINZA, "fontSize": 12},
        "scale": escala,
        "axisLine": {"show": True, "lineStyle": {"color": GRADE}},
        "axisTick": {"show": False},
        "axisLabel": {
            "color": CINZA,
            "fontSize": 11,
            "showMinLabel": pontas,
            "showMaxLabel": pontas,
            ":formatter": _FMT_JS,
        },
        "splitLine": {"lineStyle": {"color": GRADE, "width": 1, "type": "solid"}},
    }


# Margem esquerda que cabe o nome do eixo vertical (ele fica fora dos rótulos).
_GRADE_XY = {"left": 40, "right": 24, "top": 18, "bottom": 44, "containLabel": True}


def _limites(valores: list[float], folga: float = 0.06) -> tuple[float, float]:
    """Faixa com uma folga proporcional, para nenhum ponto encostar na borda."""
    baixo, alto = min(valores), max(valores)
    margem = (alto - baixo) * folga or max(abs(alto), 1.0) * folga
    return baixo - margem, alto + margem


def _pontos(cor: str = SERIE) -> Opcoes:
    """Marcador ≥ 8 px com anel de 2 px na cor da superfície (separa sobreposições)."""
    return {
        "symbolSize": 10,
        "itemStyle": {"color": cor, "borderColor": PAPEL_ALTO, "borderWidth": 2},
        "emphasis": {"scale": 1.35},
    }


# --- B2: Pareto dos efeitos padronizados --------------------------------------


def opcoes_pareto(ajuste: AjusteResposta, *, alfa: float) -> Opcoes:
    """Barras de |t| por termo, maior no topo, com a linha do t crítico.

    Duas séries empilhadas na mesma categoria (significativo / não) só para
    ganhar legenda nativa; cada termo tem valor em exatamente uma delas. A
    posição em relação à linha já diz a significância — a cor reforça.
    """
    termos = sorted(
        (c for c in ajuste.coeficientes if c.termo != INTERCEPTO),
        key=lambda c: abs(c.valor_t),
        reverse=True,
    )
    categorias = [nome_legivel(c.termo) for c in termos]

    def item(c: Any) -> Opcoes:
        return {"value": abs(c.valor_t), "p": c.valor_p, "termo": c.termo}

    sig = [item(c) if c.significativo else "-" for c in termos]
    nao = ["-" if c.significativo else item(c) for c in termos]
    # Ponta de dado arredondada (4 px), base reta no eixo; barra ≤ 22 px.
    canto = [0, 4, 4, 0]
    barra: Opcoes = {
        "type": "bar",
        "stack": "pareto",
        "barMaxWidth": 22,
        "emphasis": {"focus": "none"},
    }
    serie_sig: Opcoes = {
        **barra,
        "name": "Significativo",
        "data": sig,
        "itemStyle": {"borderRadius": canto, "color": SERIE},
    }
    if ajuste.t_critico is not None:
        serie_sig["markLine"] = {
            "silent": True,
            "symbol": "none",
            "lineStyle": {"color": TINTA, "width": 1, "type": "dashed"},
            # O valor vai no texto de leitura logo abaixo do gráfico: um rótulo
            # aqui disputaria espaço com os números do eixo.
            "label": {"show": False},
            "data": [{"xAxis": ajuste.t_critico}],
        }
    serie_nao = {
        **barra,
        "name": "Não significativo",
        "data": nao,
        "itemStyle": {"borderRadius": canto, "color": SERIE_APAGADA},
    }

    maior = max([abs(c.valor_t) for c in termos] + [ajuste.t_critico or 0.0, 1.0])
    opcoes = _base()
    opcoes["tooltip"].update(
        {
            "trigger": "item",
            ":formatter": (
                "(p) => { const f = " + _FMT_JS + "; "
                "const pv = p.data.p < 0.0001 ? '< 0,0001' : p.data.p.toLocaleString("
                "'pt-BR', {minimumFractionDigits: 4, maximumFractionDigits: 4}); "
                "return '<b>' + p.name + '</b><br/>|t| = ' + f(p.value) + "
                f"' · p = ' + pv + '<br/>' + (p.data.p < {alfa} ? "
                "'significativo' : 'não significativo'); }"
            ),
        }
    )
    opcoes.update(
        {
            "legend": {
                "top": 0,
                "left": 0,
                "icon": "roundRect",
                "itemWidth": 12,
                "itemHeight": 8,
                "textStyle": {"color": CINZA, "fontSize": 12},
                "data": ["Significativo", "Não significativo"],
            },
            "grid": {"left": 4, "right": 28, "top": 34, "bottom": 40,
                     "containLabel": True},
            "xAxis": {
                **_eixo_valor(
                    "|t|  (efeito padronizado)", escala=False, pontas=False
                ),
                "max": round(maior * 1.12, 2),
            },
            "yAxis": {
                "type": "category",
                "inverse": True,  # maior efeito no topo
                "data": categorias,
                "axisLine": {"show": True, "lineStyle": {"color": GRADE}},
                "axisTick": {"show": False},
                # Nome longo quebra em duas linhas em vez de roubar a largura
                # das barras (no celular chegava a metade do gráfico).
                "axisLabel": {"color": TINTA, "fontSize": 12, "width": 128,
                              "overflow": "break", "lineHeight": 14},
            },
            "series": [serie_sig, serie_nao],
        }
    )
    # O zero é um rótulo limpo e ancora as barras; só o máximo (quebrado, como
    # 13,27) fica escondido.
    opcoes["xAxis"]["axisLabel"]["showMinLabel"] = True
    return opcoes


def altura_pareto(ajuste: AjusteResposta) -> int:
    """Altura em px que cabe todas as barras sem espremer (mais o eixo)."""
    n = sum(1 for c in ajuste.coeficientes if c.termo != INTERCEPTO)
    return max(180, 34 * n + 96)


# --- C6 / D1: preditos × observados e resíduos × preditos ---------------------


_TOOLTIP_ENSAIO = (
    "(p) => { const f = " + _FMT_JS + "; const d = p.data; "
    "return '<b>Ensaio ' + d[2] + '</b><br/>observado ' + f(d[3]) + "
    "'<br/>previsto ' + f(d[4]) + '<br/>resíduo ' + f(d[5]); }"
)


def _linhas_por_ensaio(ajuste: AjusteResposta) -> list[tuple[int, float, float, float]]:
    d = ajuste.diagnostico
    if d is None:
        return []
    return [
        (i + 1, o, p, r)
        for i, (o, p, r) in enumerate(
            zip(d.observados, d.preditos, d.residuos, strict=True)
        )
    ]


def opcoes_preditos_observados(ajuste: AjusteResposta) -> Opcoes:
    """Previsto (y) contra observado (x), com a reta y = x de referência."""
    linhas = _linhas_por_ensaio(ajuste)
    baixo, alto = _limites([v for _, o, p, _ in linhas for v in (o, p)])
    opcoes = _base()
    opcoes["tooltip"].update({"trigger": "item", ":formatter": _TOOLTIP_ENSAIO})
    opcoes.update(
        {
            "grid": _GRADE_XY,
            "xAxis": {**_eixo_valor("Observado", pontas=False), "min": baixo,
                      "max": alto},
            "yAxis": {**_eixo_valor("Previsto pelo modelo", pontas=False),
                      "min": baixo, "max": alto, "nameGap": 40},
            "series": [
                {
                    "type": "scatter",
                    "name": "Ensaios",
                    **_pontos(),
                    "data": [[o, p, n, o, p, r] for n, o, p, r in linhas],
                    "markLine": {
                        "silent": True,
                        "symbol": "none",
                        "lineStyle": {"color": REFERENCIA, "width": 1, "type": "solid"},
                        "label": {"position": "insideEndTop", "color": CINZA,
                                  "fontSize": 11, "formatter": "y = x"},
                        "data": [[{"coord": [baixo, baixo]}, {"coord": [alto, alto]}]],
                    },
                }
            ],
        }
    )
    return opcoes


def opcoes_residuos_preditos(ajuste: AjusteResposta) -> Opcoes:
    """Resíduo (y) contra previsto (x), com a linha do zero."""
    linhas = _linhas_por_ensaio(ajuste)
    maior = max([abs(r) for *_, r in linhas] + [1e-9])
    xb, xa = _limites([p for _, _, p, _ in linhas])
    opcoes = _base()
    opcoes["tooltip"].update({"trigger": "item", ":formatter": _TOOLTIP_ENSAIO})
    opcoes.update(
        {
            "grid": _GRADE_XY,
            "xAxis": {**_eixo_valor("Previsto pelo modelo", pontas=False), "min": xb,
                      "max": xa},
            "yAxis": {**_eixo_valor("Resíduo", escala=False, pontas=False),
                      "min": -maior * 1.25, "max": maior * 1.25, "nameGap": 40},
            "series": [
                {
                    "type": "scatter",
                    "name": "Ensaios",
                    **_pontos(),
                    "data": [[p, r, n, o, p, r] for n, o, p, r in linhas],
                    "markLine": {
                        "silent": True,
                        "symbol": "none",
                        "lineStyle": {"color": REFERENCIA, "width": 1, "type": "solid"},
                        "label": {"show": False},
                        "data": [{"yAxis": 0}],
                    },
                }
            ],
        }
    )
    return opcoes


# --- D2: Q-Q normal dos resíduos ----------------------------------------------


def opcoes_qq(qq: PontosQQ) -> Opcoes:
    """Resíduos ordenados contra os quantis da normal, com a reta pelos quartis."""
    xb, xa = _limites(qq.teoricos or [0.0])
    a, b = qq.reta_intercepto, qq.reta_inclinacao
    # A faixa vertical tem de conter as pontas da reta: se uma ponta cai fora
    # do eixo, o ECharts simplesmente não desenha a linha.
    yb, ya = _limites([*qq.amostrais, a + b * xb, a + b * xa])
    opcoes = _base()
    opcoes["tooltip"].update(
        {
            "trigger": "item",
            ":formatter": (
                "(p) => { const f = " + _FMT_JS + "; "
                "return '<b>Ensaio ' + p.data[2] + '</b><br/>resíduo ' + f(p.data[1])"
                " + '<br/>quantil normal ' + f(p.data[0]); }"
            ),
        }
    )
    opcoes.update(
        {
            "grid": _GRADE_XY,
            "xAxis": {**_eixo_valor("Quantil teórico da normal", pontas=False),
                      "min": xb, "max": xa},
            "yAxis": {**_eixo_valor("Resíduo", pontas=False), "min": yb, "max": ya,
                      "nameGap": 40},
            "series": [
                {
                    "type": "scatter",
                    "name": "Resíduos",
                    **_pontos(),
                    "data": [
                        [t, r, e]
                        for t, r, e in zip(
                            qq.teoricos, qq.amostrais, qq.ensaios, strict=True
                        )
                    ],
                    "markLine": {
                        "silent": True,
                        "symbol": "none",
                        "lineStyle": {"color": REFERENCIA, "width": 1, "type": "solid"},
                        "label": {"show": False},
                        "data": [
                            [{"coord": [xb, a + b * xb]}, {"coord": [xa, a + b * xa]}]
                        ],
                    },
                }
            ],
        }
    )
    return opcoes


# --- E1 / E2: contorno e superfície 3D ----------------------------------------


def _faixa_z(grade: GradeSuperficie) -> tuple[float, float]:
    baixo, alto = grade.z_minimo, grade.z_maximo
    if math.isclose(baixo, alto, rel_tol=1e-12, abs_tol=1e-12):
        baixo, alto = baixo - 1.0, alto + 1.0  # superfície plana: evita escala nula
    return baixo, alto


def _rotulo_eixo(valor: float) -> str:
    texto = f"{valor:.3g}" if abs(valor) >= 1000 else f"{valor:.4g}"
    return texto.replace(".", ",")


def opcoes_contorno(
    grade: GradeSuperficie, *, destaque: tuple[float, float, str] | None = None
) -> Opcoes:
    """Mapa de contorno preenchido: a resposta prevista em faixas de cor.

    Faixas discretas (7, da rampa) leem como curvas de nível: cada mudança de
    tom é uma isolinha. Quanto mais escuro, maior a resposta.
    """
    baixo, alto = _faixa_z(grade)
    categorias_x = [_rotulo_eixo(v) for v in grade.valores_x]
    categorias_y = [_rotulo_eixo(v) for v in grade.valores_y]
    dados = [
        [j, i, grade.z[i][j]]
        for i in range(len(grade.valores_y))
        for j in range(len(grade.valores_x))
    ]
    passo = max(1, (len(categorias_x) - 1) // 4)
    eixo_cat = {
        "type": "category",
        "axisLine": {"show": False},
        "axisTick": {"show": False},
        "splitArea": {"show": False},
        "axisLabel": {"color": CINZA, "fontSize": 11, "interval": passo - 1},
        "nameLocation": "middle",
        "nameTextStyle": {"color": CINZA, "fontSize": 12},
    }
    opcoes = _base()
    opcoes["tooltip"].update(
        {
            "trigger": "item",
            ":formatter": (
                "(p) => { const f = " + _FMT_JS + "; "
                f"const xs = {categorias_x}; const ys = {categorias_y}; "
                f"return '{_js(nome_legivel(grade.eixo_x))} = ' + xs[p.data[0]] + "
                f"'<br/>{_js(nome_legivel(grade.eixo_y))} = ' + ys[p.data[1]] + "
                f"'<br/><b>{_js(nome_legivel(grade.resposta))} prevista ' + "
                "f(p.data[2]) + '</b>'; }"
            ),
        }
    )
    opcoes.update(
        {
            "grid": {"left": 40, "right": 112, "top": 12, "bottom": 40,
                     "containLabel": True},
            "xAxis": {**eixo_cat, "data": categorias_x,
                      "name": nome_legivel(grade.eixo_x), "nameGap": 28},
            "yAxis": {**eixo_cat, "data": categorias_y,
                      "name": nome_legivel(grade.eixo_y), "nameGap": 44},
            "visualMap": {
                "type": "piecewise",
                "min": baixo,
                "max": alto,
                "splitNumber": len(RAMPA),
                "inRange": {"color": RAMPA},
                "orient": "vertical",
                "right": 0,
                "top": "middle",
                "itemWidth": 14,
                "itemHeight": 12,
                "itemGap": 7,
                "textStyle": {"color": CINZA, "fontSize": 11},
                ":formatter": (
                    "(a, b) => { const f = (v) => v.toLocaleString('pt-BR', "
                    "{maximumFractionDigits: 1}); return f(a) + ' a ' + f(b); }"
                ),
            },
            "series": [
                {
                    # Série "custom" em vez de "heatmap": cada célula é desenhada
                    # um pouco maior que a faixa, sobrepondo a vizinha. No
                    # heatmap, as bordas fracionárias deixam frestas claras de
                    # serrilhado entre células — linhas finas que não são dado.
                    "type": "custom",
                    "name": nome_legivel(grade.resposta),
                    "data": dados,
                    "encode": {"x": 0, "y": 1, "tooltip": [2]},
                    "progressive": 0,
                    ":renderItem": _CELULA_JS,
                }
            ],
        }
    )
    opcoes["visualMap"]["dimension"] = 2
    opcoes["visualMap"]["seriesIndex"] = 0  # a escala de cor é só do mapa
    if destaque is not None:
        opcoes["series"].append(_marcador(grade, destaque))
    # Tela estreita (celular): a legenda sai da direita e vira uma fileira de
    # amostras com "menor"/"maior" nas pontas, devolvendo a largura ao mapa.
    opcoes["media"] = [
        {
            "query": {"maxWidth": 480},
            "option": {
                "grid": {"left": 40, "right": 12, "top": 12, "bottom": 84},
                "visualMap": {
                    "orient": "horizontal",
                    "left": "center",
                    "right": None,
                    "top": None,
                    "bottom": 0,
                    "showLabel": False,
                    "text": ["maior", "menor"],
                    "itemGap": 2,
                    "itemWidth": 16,
                    "itemHeight": 10,
                },
            },
        }
    ]
    return opcoes


def _marcador(
    grade: GradeSuperficie, destaque: tuple[float, float, str]
) -> Opcoes:
    """Anel com rótulo sobre o contorno (ex.: o ponto estacionário).

    Os eixos do contorno são categorias (uma por ponto da grade); a posição do
    ponto vira um índice fracionário, interpolado entre as categorias vizinhas.
    """
    x, y, rotulo = destaque

    def indice(valor: float, eixo: list[float]) -> float:
        return (valor - eixo[0]) / (eixo[-1] - eixo[0]) * (len(eixo) - 1)

    ix = indice(x, grade.valores_x)
    # Perto da borda direita, o rótulo vai para a esquerda do anel.
    lado = "left" if ix > 0.7 * (len(grade.valores_x) - 1) else "right"
    return {
        "type": "scatter",
        "name": rotulo,
        "silent": True,
        "z": 5,
        "symbol": "circle",
        "symbolSize": 16,
        "itemStyle": {"color": "transparent", "borderColor": PAPEL_ALTO,
                      "borderWidth": 3},
        "label": {
            "show": True,
            "position": lado,
            "formatter": rotulo,
            "color": PAPEL_ALTO,
            "fontWeight": 600,
            "fontSize": 12,
            "textBorderColor": TINTA,
            "textBorderWidth": 2,
        },
        "tooltip": {"show": False},
        "data": [[ix, indice(y, grade.valores_y)]],
    }


_CELULA_JS = (
    "(params, api) => { const c = api.coord([api.value(0), api.value(1)]); "
    "const s = api.size([1, 1]); return {type: 'rect', "
    "shape: {x: c[0] - s[0] / 2 - 0.5, y: c[1] - s[1] / 2 - 0.5, "
    "width: s[0] + 1, height: s[1] + 1}, "
    "style: {fill: api.visual('color')}}; }"
)


def opcoes_superficie_3d(grade: GradeSuperficie) -> Opcoes:
    """Superfície 3D (echarts-gl), na mesma rampa do contorno, para girar e explorar."""
    baixo, alto = _faixa_z(grade)
    dados = [
        [grade.valores_x[j], grade.valores_y[i], grade.z[i][j]]
        for i in range(len(grade.valores_y))
        for j in range(len(grade.valores_x))
    ]

    def eixo(nome: str) -> Opcoes:
        return {
            "type": "value",
            "name": nome,
            "nameTextStyle": {"color": CINZA, "fontSize": 12},
            "axisLabel": {"color": CINZA, "fontSize": 10, ":formatter": _FMT_JS},
            "axisLine": {"lineStyle": {"color": CINZA}},
            "splitLine": {"lineStyle": {"color": GRADE}},
        }

    return {
        "backgroundColor": "transparent",
        "tooltip": {
            "backgroundColor": PAPEL_ALTO,
            "borderColor": LINHA,
            "textStyle": {"color": TINTA, "fontSize": 12},
        },
        "visualMap": {
            "show": False,
            "min": baixo,
            "max": alto,
            "inRange": {"color": RAMPA},
        },
        "xAxis3D": eixo(nome_legivel(grade.eixo_x)),
        "yAxis3D": eixo(nome_legivel(grade.eixo_y)),
        # Eixo z na faixa da resposta (não a partir de zero), senão a superfície
        # vira uma lâmina achatada no topo da caixa.
        "zAxis3D": {**eixo(nome_legivel(grade.resposta)), "scale": True},
        "grid3D": {
            "top": -48,
            "left": 64,  # folga para o nome do eixo z, que fica à esquerda da caixa
            "boxWidth": 100,
            "boxDepth": 100,
            "boxHeight": 66,
            "axisPointer": {"lineStyle": {"color": CINZA}},
            "viewControl": {"alpha": 24, "beta": 38, "distance": 190,
                            "rotateSensitivity": 1.2, "zoomSensitivity": 0.8},
            "light": {
                "main": {"intensity": 1.05, "alpha": 42, "beta": 28, "shadow": False},
                "ambient": {"intensity": 0.38},
            },
        },
        "series": [
            {
                "type": "surface",
                "name": nome_legivel(grade.resposta),
                "shading": "lambert",
                "wireframe": {"show": True,
                              "lineStyle": {"color": "rgba(14,58,38,0.28)",
                                            "width": 0.6}},
                "data": dados,
            }
        ],
    }


def _js(texto: str) -> str:
    """Escapa texto para dentro de uma string JS entre aspas simples."""
    return texto.replace("\\", "\\\\").replace("'", "\\'")
