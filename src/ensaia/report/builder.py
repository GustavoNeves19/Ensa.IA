"""Montagem do relatório PDF a partir do resultado e do texto (spec §13).

Recebe o `AnalysisResult` congelado (os números), o `RelatorioTextual` (a prosa
do modo escolhido) e, quando a tela tem a planilha, a `MatrizEnsaios`. Monta a
estrutura fixa da spec — capa, resumo, dados, descritiva, efeitos, modelo,
ANOVA, diagnóstico, superfícies, otimização, texto e apêndice — e **só entram
as seções das análises marcadas** (RF-11), lidas de `metadados.analises`.

Nada se calcula aqui: tabelas e gráficos leem o que o núcleo já produziu (a
grade da superfície e os pontos do Q-Q também vêm de funções do núcleo).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

from ensaia.ai.report import RelatorioTextual
from ensaia.core.catalogo import CATALOGO, IDS
from ensaia.core.descritiva import MatrizEnsaios
from ensaia.core.design import INTERCEPTO, nome_legivel
from ensaia.core.pipeline import fatores_do_contrato
from ensaia.core.results import (
    NOME_PLANEJAMENTO,
    AjusteResposta,
    AnalysisResult,
    Diagnostico,
    EfeitosFatorial,
    LinhaAnova,
)
from ensaia.core.surface import grade_superficie, par_inicial
from ensaia.core.termos import NOME_MODELO
from ensaia.report import charts
from ensaia.report.pdf import RelatorioPDF, numero_ptbr, numero_sig
from ensaia.report.theme import TEMA, Tema

# Pontos por eixo da grade do contorno: fino o bastante para as faixas não
# saírem em degraus, leve o bastante para o PDF sair em segundos.
_PONTOS_CONTORNO = 41
# Contorno e 3D cabem juntos numa página nesta largura (mm).
_LARGURA_SUPERFICIE = 118
# Matriz com mais ensaios que isto vai resumida (o resto está no JSON).
_MAX_LINHAS_MATRIZ = 60
_NATUREZA = {"maximo": "um máximo", "minimo": "um mínimo", "sela": "um ponto de sela"}
_SENTIDO = {"maximizar": "maximizar", "minimizar": "minimizar", "alvo": "alvo"}


def gerar_pdf(
    resultado: AnalysisResult,
    relatorio: RelatorioTextual,
    *,
    gerado_em: str | None = None,
    destino: str | Path | None = None,
    tema: Tema = TEMA,
    dados: MatrizEnsaios | None = None,
) -> bytes:
    """Monta o relatório PDF e devolve os bytes (e grava, se `destino` for dado).

    `gerado_em` é a data/hora da capa, recebida de fora para o PDF continuar
    reproduzível em teste (sem relógio interno). `dados` traz a matriz dos
    ensaios (A3); sem ela, a seção mostra só a codificação dos fatores.
    """
    sel = frozenset(resultado.metadados.analises or IDS)
    pdf = RelatorioPDF(versao=resultado.metadados.versao_ensaia, tema=tema)

    _capa(pdf, resultado, gerado_em, dados)
    pdf.mostrar_cabecalho = True
    _resumo(pdf, resultado)
    if sel & {"A2", "A3"}:
        _secao_dados(pdf, resultado, dados, sel)
    if "A1" in sel and resultado.descritiva:
        _secao_descritiva(pdf, resultado)
    for ajuste in resultado.ajustes:
        if sel & {"B1", "B2", "B3", "B4", "B5"}:
            _secao_efeitos(pdf, ajuste, sel)
    for ajuste in resultado.ajustes:
        if sel & {"C1", "C5"}:
            _secao_modelo(pdf, ajuste, sel)
    for ajuste in resultado.ajustes:
        if sel & {"C2", "C3", "C4"}:
            _secao_anova(pdf, ajuste, sel, resultado.metadados.alfa)
    for ajuste in resultado.ajustes:
        if sel & {"C6", "D1", "D2", "D3", "D4"}:
            _secao_diagnostico(pdf, ajuste, sel)
    if len(resultado.fatores) >= 2 and resultado.planejamento is not None:
        for ajuste in resultado.ajustes:
            if sel & {"E1", "E2", "E3"}:
                _secao_superficie(pdf, resultado, ajuste, sel)
    if resultado.ponto_otimo is not None and sel & {"E4", "E5"}:
        _secao_otimizacao(pdf, resultado)
    _secao_interpretacao(pdf, relatorio)
    _apendice(pdf, resultado, relatorio, sel)

    saida = bytes(pdf.output())
    if destino is not None:
        Path(destino).write_bytes(saida)
    return saida


# --- 1–2. Capa e resumo -------------------------------------------------------


def _nome_tipo(resultado: AnalysisResult) -> str:
    """Nome do planejamento com inicial maiúscula (título e resumo do PDF)."""
    nome = NOME_PLANEJAMENTO.get(
        resultado.tipo_planejamento, resultado.tipo_planejamento
    )
    return nome[:1].upper() + nome[1:]


def _capa(
    pdf: RelatorioPDF,
    resultado: AnalysisResult,
    gerado_em: str | None,
    dados: MatrizEnsaios | None,
) -> None:
    pdf.add_page()
    tema = pdf.tema
    pdf.ln(28)
    pdf.set_font(tema.familia, "B", 26)
    pdf.multi_cell(0, 12, "Relatório de Análise", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(tema.familia, "", 13)
    pdf.set_text_color(*tema.cinza)
    pdf.multi_cell(0, 7, _nome_tipo(resultado), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*tema.tinta)
    pdf.ln(14)

    hash_curto = hashlib.sha256(resultado.to_json().encode("utf-8")).hexdigest()[:12]
    if dados is not None and dados.nome_arquivo:
        pdf.rotulo_valor("Arquivo", dados.nome_arquivo)
    pdf.rotulo_valor("Fatores", ", ".join(map(nome_legivel, resultado.fatores)))
    pdf.rotulo_valor("Respostas", ", ".join(map(nome_legivel, resultado.respostas)))
    if gerado_em:
        pdf.rotulo_valor("Gerado em", gerado_em)
    pdf.rotulo_valor(
        "Versão do sistema", f"EnsaIA v{resultado.metadados.versao_ensaia}"
    )
    pdf.rotulo_valor("Nível de significância (α)", _num_alfa(resultado.metadados.alfa))
    pdf.rotulo_valor("Identificador da análise (SHA-256)", hash_curto)


def _resumo(pdf: RelatorioPDF, resultado: AnalysisResult) -> None:
    pdf.titulo_secao("Resumo")
    tema = pdf.tema
    n_ensaios = resultado.ajustes[0].n_observacoes if resultado.ajustes else 0
    pdf.paragrafo(
        f"{_nome_tipo(resultado)} com {len(resultado.fatores)} fator(es), "
        f"{len(resultado.respostas)} resposta(s) e {n_ensaios} ensaios."
    )
    for ajuste in resultado.ajustes:
        significativos = [
            nome_legivel(c.termo)
            for c in ajuste.coeficientes
            if c.termo != INTERCEPTO and c.significativo
        ]
        termos = ", ".join(significativos) if significativos else "nenhum termo"
        pdf.rotulo_valor(
            nome_legivel(ajuste.resposta),
            f"R² = {numero_ptbr(ajuste.r2, tema.casas_r2)}; "
            f"termos significativos: {termos}.",
        )
    otimo = resultado.ponto_otimo
    if otimo is not None:
        condicao = "; ".join(
            f"{nome_legivel(f)} = {numero_sig(v)}" for f, v in otimo.coordenadas.items()
        )
        previstas = "; ".join(
            f"{nome_legivel(r)} = {numero_sig(v)}"
            for r, v in otimo.resposta_prevista.items()
        )
        pdf.rotulo_valor("Melhor condição", f"{condicao} (prevê {previstas}).")


# --- 3–4. Dados e estatística descritiva ---------------------------------------


def _secao_dados(
    pdf: RelatorioPDF,
    resultado: AnalysisResult,
    dados: MatrizEnsaios | None,
    sel: frozenset[str],
) -> None:
    pdf.titulo_secao("Dados e planejamento")
    info = resultado.planejamento
    if "A2" in sel and info is not None:
        pdf.rotulo_valor("Planejamento", _nome_tipo(resultado))
        pdf.rotulo_valor(
            "Ensaios",
            f"{info.n_ensaios}, dos quais {info.n_pontos_centrais} no ponto central",
        )
        if info.alfa_axial:
            pdf.rotulo_valor("Distância axial (α)", numero_sig(info.alfa_axial))
        pdf.subtitulo("Codificação dos fatores")
        pdf.tabela(
            ["Fator", "Unidade", "−1", "0", "+1"],
            [
                [
                    nome_legivel(f.nome),
                    f.unidade or "—",
                    numero_sig(f.centro - f.passo),
                    numero_sig(f.centro),
                    numero_sig(f.centro + f.passo),
                ]
                for f in info.fatores
            ],
            larguras=[54, 30, 30, 30, 30],
        )
        for aviso in info.avisos:
            pdf.nota(f"Aviso: {aviso}")
    if "A3" in sel and dados is not None and dados.n_ensaios:
        _matriz(pdf, dados)


def _matriz(pdf: RelatorioPDF, dados: MatrizEnsaios) -> None:
    pdf.subtitulo("Matriz dos ensaios: valor real (codificado) e respostas")
    fatores = list(dados.real)
    respostas = list(dados.respostas)
    n = min(dados.n_ensaios, _MAX_LINHAS_MATRIZ)
    linhas = [
        [
            str(i + 1),
            *(_real_codificado(dados, f, i) for f in fatores),
            *(numero_sig(dados.respostas[r][i]) for r in respostas),
        ]
        for i in range(n)
    ]
    util = pdf.w - pdf.l_margin - pdf.r_margin - 14
    colunas = len(fatores) + len(respostas)
    pdf.tabela(
        ["Ensaio", *map(nome_legivel, fatores), *map(nome_legivel, respostas)],
        linhas,
        larguras=[14, *([util / colunas] * colunas)],
    )
    if dados.n_ensaios > n:
        pdf.nota(
            f"Mostrando os {n} primeiros de {dados.n_ensaios} ensaios; a matriz "
            "completa está no JSON dos resultados."
        )


def _real_codificado(dados: MatrizEnsaios, fator: str, i: int) -> str:
    real = numero_sig(dados.real[fator][i])
    return f"{real} ({numero_ptbr(dados.codificada[fator][i], 2)})"


def _secao_descritiva(pdf: RelatorioPDF, resultado: AnalysisResult) -> None:
    pdf.titulo_secao("Estatística descritiva")
    pdf.tabela(
        ["Resposta", "n", "Média", "Desvio-padrão", "Mín.", "Máx.", "CV (%)"],
        [
            [
                nome_legivel(d.resposta),
                str(d.n),
                numero_sig(d.media),
                numero_sig(d.desvio_padrao),
                numero_sig(d.minimo),
                numero_sig(d.maximo),
                numero_ptbr(d.cv_percentual, 1) if d.cv_percentual is not None else "—",
            ]
            for d in resultado.descritiva
        ],
        larguras=[44, 12, 24, 28, 22, 22, 22],
    )
    pdf.nota(
        "O coeficiente de variação (CV) mostra quanto a resposta mudou entre os "
        "ensaios: muito baixo indica que os fatores mexeram pouco nela."
    )


# --- 5. Efeitos ---------------------------------------------------------------


def _secao_efeitos(
    pdf: RelatorioPDF, ajuste: AjusteResposta, sel: frozenset[str]
) -> None:
    ef = ajuste.efeitos_fatorial
    fatorial = ef is not None and bool(sel & {"B1", "B3", "B4", "B5"})
    if not fatorial and "B2" not in sel:
        return
    pareto = charts.grafico_pareto(ajuste, tema=pdf.tema) if "B2" in sel else None
    if ef is not None and "B1" in sel:
        primeiro = 60.0
    else:
        primeiro = pdf.altura_png(pareto, 150) if pareto else 30.0
    pdf.titulo_secao(f"Efeitos — {nome_legivel(ajuste.resposta)}", reservar=primeiro)
    if ef is not None and "B1" in sel:
        _tabela_efeitos(pdf, ef)
    if pareto is not None:
        pdf.imagem_png(pareto, largura=150)
        t = ajuste.t_critico
        limite = f" (t crítico = {numero_ptbr(t, 3)})" if t is not None else ""
        pdf.nota(f"Barra que passa da linha tracejada{limite} é efeito significativo.")
    if ef is None:
        return
    if "B3" in sel:
        png = charts.grafico_meio_normal(ef, tema=pdf.tema)
        if png is not None and ef.lenth is not None:
            pdf.imagem_png(png, largura=130)
            pdf.nota(
                f"Lenth: PSE = {numero_sig(ef.lenth.pse)}; ME = "
                f"{numero_sig(ef.lenth.me)}; SME = {numero_sig(ef.lenth.sme)}. "
                "Efeitos à direita da linha tracejada são ativos."
            )
    if "B4" in sel:
        for png_b4 in (
            charts.grafico_efeitos_principais(ef, ajuste.resposta, tema=pdf.tema),
            charts.grafico_interacoes(ef, tema=pdf.tema),
        ):
            if png_b4 is not None:
                pdf.imagem_png(png_b4, largura=160)
    if "B5" in sel:
        _curvatura(pdf, ef)


def _tabela_efeitos(pdf: RelatorioPDF, ef: EfeitosFatorial) -> None:
    pdf.subtitulo("Efeitos estimados")
    pdf.tabela(
        ["Termo", "Efeito", "Erro padrão", "t", "p", "Signif."],
        [
            [
                nome_legivel(e.termo),
                numero_sig(e.efeito),
                numero_sig(e.erro_padrao),
                numero_ptbr(e.valor_t, 2),
                _fmt_p(e.valor_p, pdf.tema.casas_p),
                "sim" if e.significativo else "não",
            ]
            for e in ef.efeitos
        ],
        larguras=[54, 24, 28, 20, 24, 24],
    )


def _curvatura(pdf: RelatorioPDF, ef: EfeitosFatorial) -> None:
    c = ef.curvatura
    if not c.aplicavel or c.valor_p is None:
        motivo = (c.motivo_inaplicavel or "sem pontos centrais").rstrip(".")
        pdf.paragrafo(f"Teste de curvatura: não aplicável ({motivo}).")
        return
    p = _fmt_p(c.valor_p, pdf.tema.casas_p)
    if c.significativa:
        pdf.paragrafo(
            f"Há curvatura (p = {p}): a média dos pontos centrais difere da média "
            "dos pontos fatoriais, e um modelo de segunda ordem pode ser necessário."
        )
    else:
        pdf.paragrafo(f"Sem evidência de curvatura (p = {p}).")


# --- 6. Modelo ----------------------------------------------------------------


def _secao_modelo(
    pdf: RelatorioPDF, ajuste: AjusteResposta, sel: frozenset[str]
) -> None:
    tema = pdf.tema
    pdf.titulo_secao(f"Modelo ajustado — {nome_legivel(ajuste.resposta)}")
    if "C1" in sel:
        pdf.tabela(
            ["Termo", "Coef.", "Erro padrão", "t", "p", "Signif."],
            [
                [
                    nome_legivel(c.termo),
                    numero_sig(c.estimativa),
                    numero_sig(c.erro_padrao),
                    numero_ptbr(c.valor_t, 2),
                    _fmt_p(c.valor_p, tema.casas_p),
                    "sim" if c.significativo else "não",
                ]
                for c in ajuste.coeficientes
            ],
            larguras=[54, 24, 28, 20, 24, 24],
        )
        if ajuste.termos_descartados:
            removidos = ", ".join(map(nome_legivel, ajuste.termos_descartados))
            pdf.nota(f"Removidos pela redução do modelo: {removidos}.")
        pdf.imagem_png(charts.grafico_coeficientes(ajuste, tema=tema), largura=150)
    eq = ajuste.equacao
    if "C5" in sel and eq is not None:
        pdf.subtitulo("Equação do modelo (codificada)")
        pdf.paragrafo(eq.codificada.replace("_", " "))
        if eq.variaveis:
            legenda = "; ".join(
                f"{x} = {nome_legivel(nome)}" for x, nome in eq.variaveis.items()
            )
            pdf.nota(legenda)
        pdf.subtitulo("Equação em unidades reais")
        pdf.paragrafo(eq.real.replace("_", " "))
        pdf.nota("Use direto os valores do laboratório nesta forma.")


# --- 7. ANOVA e R² -------------------------------------------------------------


def _secao_anova(
    pdf: RelatorioPDF, ajuste: AjusteResposta, sel: frozenset[str], alfa: float
) -> None:
    tema = pdf.tema
    pdf.titulo_secao(f"ANOVA e qualidade do ajuste — {nome_legivel(ajuste.resposta)}")
    if "C3" in sel:
        r2 = (
            f"{numero_ptbr(ajuste.r2, tema.casas_r2)} (ajustado "
            f"{numero_ptbr(ajuste.r2_ajustado, tema.casas_r2)}"
        )
        if ajuste.r2_predicao is not None:
            r2 += f"; de predição {numero_ptbr(ajuste.r2_predicao, tema.casas_r2)}"
        pdf.rotulo_valor("R²", r2 + ")")
    reg = ajuste.anova_regressao
    if "C2" in sel and reg is not None:
        pdf.subtitulo("ANOVA da regressão")
        _tabela_anova(pdf, reg.linhas)
        if reg.razao_f is not None and reg.f_tabelado is not None:
            leitura = (
                "maior que 1: a regressão é significativa"
                if reg.regressao_significativa
                else "menor que 1: a regressão não é significativa"
            )
            pdf.nota(
                f"F calculado / F tabelado = {numero_ptbr(reg.razao_f, 2)} "
                f"(F tabelado = {numero_ptbr(reg.f_tabelado, 2)} a α = "
                f"{_num_alfa(alfa)}), {leitura}."
            )
    if "C2" in sel and ajuste.anova:
        pdf.subtitulo("Efeito de cada termo (ANOVA Tipo II)")
        _tabela_anova(pdf, ajuste.anova)
        if ajuste.termo_erro == "erro_puro":
            pdf.nota("Testes feitos com o erro puro das réplicas.")
    if "C4" in sel:
        pdf.paragrafo(_texto_falta(ajuste, tema.casas_p))


def _tabela_anova(pdf: RelatorioPDF, linhas: Sequence[LinhaAnova]) -> None:
    casas_p = pdf.tema.casas_p
    pdf.tabela(
        ["Fonte", "SQ", "gl", "QM", "F", "p"],
        [
            [
                nome_legivel(linha.fonte),
                numero_sig(linha.soma_quadrados),
                str(linha.graus_liberdade),
                numero_sig(linha.quadrado_medio),
                numero_ptbr(linha.valor_f, 2) if linha.valor_f is not None else "—",
                _fmt_p(linha.valor_p, casas_p) if linha.valor_p is not None else "—",
            ]
            for linha in linhas
        ],
        larguras=[54, 30, 16, 30, 22, 22],
    )


def _texto_falta(ajuste: AjusteResposta, casas_p: int) -> str:
    falta = ajuste.falta_de_ajuste
    if not falta.aplicavel or falta.valor_p is None:
        motivo = falta.motivo_inaplicavel or "não há réplicas genuínas no delineamento"
        return f"Teste de falta de ajuste: não aplicável ({motivo.rstrip('.')})."
    p = _fmt_p(falta.valor_p, casas_p)
    if falta.significativa:
        return (
            f"Há evidência de falta de ajuste (p = {p}): o modelo pode não "
            "descrever bem os dados."
        )
    return f"Não há evidência de falta de ajuste (p = {p})."


# --- 8. Diagnóstico -----------------------------------------------------------


def _secao_diagnostico(
    pdf: RelatorioPDF, ajuste: AjusteResposta, sel: frozenset[str]
) -> None:
    d = ajuste.diagnostico
    png = charts.grafico_diagnostico(ajuste, sorted(sel), tema=pdf.tema)
    pdf.titulo_secao(
        f"Diagnóstico — {nome_legivel(ajuste.resposta)}",
        reservar=pdf.altura_png(png, 170) if png else 30.0,
    )
    if d is None:
        pdf.paragrafo("Este resultado não traz os valores por ensaio.")
        return
    if png is not None:
        pdf.imagem_png(png, largura=170)
        pdf.nota(
            "Pontos perto da linha y = x acertam; resíduos devem se espalhar ao "
            "acaso em torno do zero; no Q-Q, pontos longe da reta indicam desvio "
            "da normalidade."
        )
    if "D2" in sel:
        pdf.paragrafo(_texto_normalidade(d, pdf.tema.casas_p))
    if "D4" in sel:
        pdf.paragrafo(_texto_influencia(d))


def _texto_normalidade(d: Diagnostico, casas_p: int) -> str:
    if d.shapiro_w is None or d.shapiro_p is None:
        motivo = (d.motivo_sem_shapiro or "poucos ensaios").rstrip(".")
        return f"Teste de Shapiro-Wilk não aplicável ({motivo})."
    estatistica = (
        f"W = {numero_ptbr(d.shapiro_w, 3)}; p = {_fmt_p(d.shapiro_p, casas_p)}"
    )
    if d.normalidade_rejeitada:
        return (
            f"Shapiro-Wilk ({estatistica}): os resíduos não parecem normais; "
            "os p-valores do modelo pedem cautela."
        )
    return f"Shapiro-Wilk ({estatistica}): sem evidência contra a normalidade."


def _texto_influencia(d: Diagnostico) -> str:
    partes = []
    if d.ensaios_influentes:
        lista = ", ".join(map(str, d.ensaios_influentes))
        partes.append(
            f"Ensaio(s) influente(s): {lista} (distância de Cook > 1 e alavancagem "
            "alta); confira se foram executados como planejado."
        )
    if d.possiveis_outliers:
        lista = ", ".join(map(str, d.possiveis_outliers))
        partes.append(f"Possível(is) outlier(s): {lista} (resíduo studentizado > 3).")
    return " ".join(partes) or "Nenhum ensaio influente ou outlier."


# --- 9. Superfícies -----------------------------------------------------------


def _secao_superficie(
    pdf: RelatorioPDF,
    resultado: AnalysisResult,
    ajuste: AjusteResposta,
    sel: frozenset[str],
) -> None:
    assert resultado.planejamento is not None
    fatores = fatores_do_contrato(resultado.planejamento)
    por_nome = {f.nome: f for f in fatores}
    x, y = par_inicial(ajuste, [f.nome for f in fatores])
    otimo = resultado.ponto_otimo
    fixos = {
        f.nome: (otimo.coordenadas[f.nome] if otimo else f.centro)
        for f in fatores
        if f.nome not in (x, y) and (otimo is None or f.nome in otimo.coordenadas)
    }
    rotulos = {
        "rotulo_x": _rotulo_fator(por_nome[x].nome, por_nome[x].unidade),
        "rotulo_y": _rotulo_fator(por_nome[y].nome, por_nome[y].unidade),
    }
    graficos: list[bytes] = []
    if "E2" in sel:
        grade = grade_superficie(
            ajuste, fatores, x, y, fixos=fixos, pontos=_PONTOS_CONTORNO
        )
        destaque = (
            (otimo.coordenadas[x], otimo.coordenadas[y])
            if otimo and x in otimo.coordenadas and y in otimo.coordenadas
            else None
        )
        graficos.append(
            charts.grafico_contorno(grade, destaque=destaque, tema=pdf.tema, **rotulos)
        )
    if "E1" in sel:
        grade = grade_superficie(ajuste, fatores, x, y, fixos=fixos)
        graficos.append(charts.grafico_superficie_3d(grade, tema=pdf.tema, **rotulos))
    pdf.titulo_secao(
        f"Superfície de resposta — {nome_legivel(ajuste.resposta)}",
        reservar=pdf.altura_png(graficos[0], _LARGURA_SUPERFICIE) + 8
        if graficos
        else 30.0,
    )
    if graficos and fixos:
        onde = "no ótimo" if otimo else "no centro"
        lista = "; ".join(
            f"{nome_legivel(n)} = {numero_sig(v)}" for n, v in fixos.items()
        )
        pdf.nota(f"Demais fatores fixos {onde}: {lista}.")
    for png in graficos:
        pdf.imagem_png(png, largura=_LARGURA_SUPERFICIE)
    pe = ajuste.ponto_estacionario
    if "E3" in sel and pe is not None:
        coordenadas = "; ".join(
            f"{nome_legivel(n)} = {numero_sig(v)} ({numero_ptbr(pe.codificado[n], 2)})"
            for n, v in pe.real.items()
        )
        regiao = "dentro" if pe.dentro_da_regiao else "fora"
        pdf.paragrafo(
            f"Ponto estacionário: {_NATUREZA[pe.natureza]}, em {coordenadas} "
            f"(real e codificado), {regiao} da região estudada; resposta prevista "
            f"{numero_sig(pe.resposta_prevista)}."
        )


def _rotulo_fator(nome: str, unidade: str) -> str:
    return f"{nome_legivel(nome)} ({unidade})" if unidade else nome_legivel(nome)


# --- 10. Otimização ------------------------------------------------------------


def _secao_otimizacao(pdf: RelatorioPDF, resultado: AnalysisResult) -> None:
    otimo = resultado.ponto_otimo
    assert otimo is not None
    pdf.titulo_secao("Otimização e desejabilidade")
    pdf.subtitulo("Melhor condição")
    pdf.tabela(
        ["Fator", "Valor real", "Codificado"],
        [
            [
                nome_legivel(f),
                numero_sig(v),
                numero_ptbr(otimo.coordenadas_codificadas[f], 3)
                if f in otimo.coordenadas_codificadas
                else "—",
            ]
            for f, v in otimo.coordenadas.items()
        ],
        larguras=[70, 50, 50],
    )
    pdf.subtitulo("Respostas previstas")
    pdf.tabela(
        ["Resposta", "Meta", "Prevista", "Desejabilidade"],
        [
            [
                nome_legivel(r),
                _SENTIDO.get(otimo.metas.get(r, ""), otimo.metas.get(r, "—")),
                numero_sig(v),
                numero_ptbr(otimo.desejabilidades_individuais[r], 3)
                if r in otimo.desejabilidades_individuais
                else "—",
            ]
            for r, v in otimo.resposta_prevista.items()
        ],
        larguras=[60, 36, 40, 34],
    )
    pdf.rotulo_valor(
        "Desejabilidade global (D)", numero_ptbr(otimo.desejabilidade_global, 3)
    )
    pdf.nota(
        "D vai de 0 (alguma meta não atendida) a 1 (todas atendidas). A busca fica "
        "dentro da região estudada; confirme a condição com um ensaio antes de "
        "adotá-la."
    )


# --- 11–12. Texto e apêndice -----------------------------------------------------


def _secao_interpretacao(pdf: RelatorioPDF, relatorio: RelatorioTextual) -> None:
    pdf.titulo_secao("Interpretação")
    pdf.paragrafo(f"Texto escrito por: {relatorio.origem}.", tamanho=9)
    fid = relatorio.fidelidade
    if fid is not None and relatorio.modo != "m0":
        pdf.paragrafo(f"Conferência dos números: {fid.resumo()}", tamanho=9)
        if fid.nao_rastreaveis:
            corpo = relatorio.corpo()
            soltos = "; ".join(corpo[n.inicio : n.fim] for n in fid.nao_rastreaveis)
            pdf.paragrafo(
                f"Números sem correspondência nos resultados: {soltos}.", tamanho=9
            )
        for contradicao in fid.contradicoes:
            pdf.paragrafo(f"Aviso: {contradicao.descricao()}", tamanho=9)
    for aviso in relatorio.avisos:
        pdf.paragrafo(f"Aviso: {aviso}", tamanho=9)
    for secao in relatorio.secoes:
        pdf.subtitulo(secao.titulo)
        pdf.paragrafo(secao.texto)


def _apendice(
    pdf: RelatorioPDF,
    resultado: AnalysisResult,
    relatorio: RelatorioTextual,
    sel: frozenset[str],
) -> None:
    meta = resultado.metadados
    pdf.titulo_secao("Apêndice")
    if meta.tipo_modelo is not None:
        pdf.rotulo_valor("Modelo", NOME_MODELO[meta.tipo_modelo])
    pdf.rotulo_valor(
        "Termo de erro",
        "erro puro das réplicas" if meta.termo_erro == "erro_puro" else "resíduo",
    )
    pdf.rotulo_valor("Redução do modelo", "sim" if meta.reducao_backward else "não")
    pdf.rotulo_valor(
        "Análises incluídas",
        "; ".join(f"{a.id} {a.nome}" for a in CATALOGO if a.id in sel),
    )
    pdf.rotulo_valor("Esquema do contrato", meta.schema_version)
    pdf.rotulo_valor("Versão do prompt", relatorio.prompt_version)
    if relatorio.modelo_usado:
        pdf.rotulo_valor("Modelo de linguagem", relatorio.modelo_usado)
    pdf.rotulo_valor(
        "Versões das bibliotecas", _versoes_bibliotecas(meta.versao_ensaia)
    )
    if resultado.avisos:
        pdf.subtitulo("Avisos da análise")
        for aviso in resultado.avisos:
            pdf.paragrafo(f"• {aviso}", tamanho=9)


def _versoes_bibliotecas(versao_ensaia: str) -> str:
    """Versões das dependências, começando pela do próprio EnsaIA.

    A do EnsaIA vem do metadado da execução (sempre disponível); as demais, de
    `importlib.metadata`, que reflete o que está instalado no ambiente.
    """
    from importlib.metadata import PackageNotFoundError, version

    partes = [f"ensaia {versao_ensaia}"]
    for pacote in ["numpy", "scipy", "pydantic", "fpdf2", "matplotlib"]:
        try:
            partes.append(f"{pacote} {version(pacote)}")
        except PackageNotFoundError:  # pragma: no cover - ambiente sem o pacote
            continue
    return "; ".join(partes)


def _fmt_p(valor: float, casas: int) -> str:
    """p-valor em pt-BR; abaixo do menor representável, usa '< 0,0001'."""
    limite = 10 ** (-casas)
    if 0 <= valor < limite:
        return "< " + numero_ptbr(limite, casas)
    return numero_ptbr(valor, casas)


def _num_alfa(alfa: float) -> str:
    return numero_ptbr(alfa, 2)


__all__: Sequence[str] = ["gerar_pdf"]
