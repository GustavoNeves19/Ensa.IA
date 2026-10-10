"""Montagem do relatório PDF a partir do resultado e do texto.

Recebe o `AnalysisResult` congelado (os números) e o `RelatorioTextual` (a prosa
do modo escolhido), e monta as seções da spec §13 que já são possíveis sem dados
crus nem superfícies: capa, resumo, modelo, ANOVA/R², diagnóstico, interpretação
e apêndice. Estatística descritiva, matriz de dados e superfícies entram quando o
contrato carregar o que elas pedem.

Nada se calcula aqui: tabelas e gráficos leem o que o núcleo já produziu.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

from ensaia.ai.report import RelatorioTextual
from ensaia.core.design import INTERCEPTO
from ensaia.core.results import NOME_PLANEJAMENTO, AjusteResposta, AnalysisResult
from ensaia.report.charts import grafico_coeficientes, grafico_pareto
from ensaia.report.pdf import RelatorioPDF, numero_ptbr
from ensaia.report.theme import TEMA, Tema


def _nome_tipo(resultado: AnalysisResult) -> str:
    """Nome do planejamento com inicial maiúscula (título e resumo do PDF)."""
    nome = NOME_PLANEJAMENTO.get(
        resultado.tipo_planejamento, resultado.tipo_planejamento
    )
    return nome[:1].upper() + nome[1:]


def gerar_pdf(
    resultado: AnalysisResult,
    relatorio: RelatorioTextual,
    *,
    gerado_em: str | None = None,
    destino: str | Path | None = None,
    tema: Tema = TEMA,
) -> bytes:
    """Monta o relatório PDF e devolve os bytes (e grava, se `destino` for dado).

    `gerado_em` é a data/hora da capa, recebida de fora para o PDF continuar
    reproduzível em teste (sem relógio interno).
    """
    pdf = RelatorioPDF(versao=resultado.metadados.versao_ensaia, tema=tema)

    _capa(pdf, resultado, gerado_em)
    pdf.mostrar_cabecalho = True

    _resumo(pdf, resultado)
    for ajuste in resultado.ajustes:
        _secao_modelo(pdf, ajuste)
        _secao_anova(pdf, ajuste)
        _secao_diagnostico(pdf, ajuste)
    _secao_interpretacao(pdf, relatorio)
    _apendice(pdf, resultado, relatorio)

    saida = bytes(pdf.output())
    if destino is not None:
        Path(destino).write_bytes(saida)
    return saida


def _capa(pdf: RelatorioPDF, resultado: AnalysisResult, gerado_em: str | None) -> None:
    pdf.add_page()
    tema = pdf.tema
    pdf.ln(28)
    pdf.set_font(tema.familia, "B", 26)
    pdf.multi_cell(0, 12, "Relatório de Análise", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(tema.familia, "", 13)
    pdf.set_text_color(*tema.cinza)
    tipo = _nome_tipo(resultado)
    pdf.multi_cell(0, 7, tipo, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*tema.tinta)

    pdf.ln(4)
    pdf.set_draw_color(*tema.acento)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 60, pdf.get_y())
    pdf.ln(10)

    hash_curto = hashlib.sha256(resultado.to_json().encode("utf-8")).hexdigest()[:12]
    pdf.rotulo_valor("Fatores", ", ".join(resultado.fatores))
    pdf.rotulo_valor("Respostas", ", ".join(resultado.respostas))
    if gerado_em:
        pdf.rotulo_valor("Gerado em", gerado_em)
    pdf.rotulo_valor(
        "Versão do sistema", f"EnsaIA v{resultado.metadados.versao_ensaia}"
    )
    pdf.rotulo_valor("Nível de significância (α)", _num_alfa(resultado.metadados.alfa))
    pdf.rotulo_valor("Identificador (SHA-256)", hash_curto)


def _resumo(pdf: RelatorioPDF, resultado: AnalysisResult) -> None:
    pdf.titulo_secao("Resumo")
    tema = pdf.tema
    tipo = _nome_tipo(resultado)
    pdf.paragrafo(
        f"{tipo} com {len(resultado.fatores)} fator(es) e "
        f"{len(resultado.respostas)} resposta(s)."
    )
    for ajuste in resultado.ajustes:
        significativos = [
            c.termo
            for c in ajuste.coeficientes
            if c.termo != INTERCEPTO and c.significativo
        ]
        termos = ", ".join(significativos) if significativos else "nenhum termo"
        pdf.rotulo_valor(
            ajuste.resposta,
            f"R² = {numero_ptbr(ajuste.r2, tema.casas_r2)}; "
            f"significativos: {termos}.",
        )


def _secao_modelo(pdf: RelatorioPDF, ajuste: AjusteResposta) -> None:
    tema = pdf.tema
    pdf.titulo_secao(f"Modelo ajustado — {ajuste.resposta}")
    linhas = [
        [
            c.termo,
            numero_ptbr(c.estimativa, tema.casas_coef),
            numero_ptbr(c.erro_padrao, tema.casas_coef),
            numero_ptbr(c.valor_t, 2),
            _fmt_p(c.valor_p, tema.casas_p),
            "sim" if c.significativo else "não",
        ]
        for c in ajuste.coeficientes
    ]
    pdf.tabela(
        ["Termo", "Coef.", "Erro padrão", "t", "p", "Signif."],
        linhas,
        larguras=[54, 24, 28, 20, 24, 24],
    )
    pdf.imagem_png(grafico_coeficientes(ajuste, tema=tema), largura=150)


def _secao_anova(pdf: RelatorioPDF, ajuste: AjusteResposta) -> None:
    tema = pdf.tema
    pdf.titulo_secao(f"ANOVA e R² — {ajuste.resposta}")
    pdf.rotulo_valor(
        "R²",
        f"{numero_ptbr(ajuste.r2, tema.casas_r2)} "
        f"(ajustado {numero_ptbr(ajuste.r2_ajustado, tema.casas_r2)})",
    )
    if ajuste.anova:
        linhas = [
            [
                linha.fonte,
                numero_ptbr(linha.soma_quadrados, 2),
                str(linha.graus_liberdade),
                numero_ptbr(linha.quadrado_medio, 2),
                numero_ptbr(linha.valor_f, 2) if linha.valor_f is not None else "—",
                _fmt_p(linha.valor_p, tema.casas_p)
                if linha.valor_p is not None
                else "—",
            ]
            for linha in ajuste.anova
        ]
        pdf.tabela(
            ["Fonte", "SQ", "gl", "QM", "F", "p"],
            linhas,
            larguras=[54, 30, 16, 30, 22, 22],
        )
    pdf.imagem_png(grafico_pareto(ajuste, tema=tema), largura=150)


def _secao_diagnostico(pdf: RelatorioPDF, ajuste: AjusteResposta) -> None:
    tema = pdf.tema
    pdf.titulo_secao(f"Diagnóstico — {ajuste.resposta}")
    falta = ajuste.falta_de_ajuste
    if not falta.aplicavel:
        motivo = falta.motivo_inaplicavel or "não há réplicas genuínas no delineamento"
        pdf.paragrafo(f"Teste de falta de ajuste não aplicável: {motivo.rstrip('.')}.")
        return
    assert falta.valor_p is not None
    p = numero_ptbr(falta.valor_p, tema.casas_p)
    if falta.significativa:
        pdf.paragrafo(
            f"Há evidência de falta de ajuste (p = {p}): o modelo pode não "
            f"descrever bem os dados."
        )
    else:
        pdf.paragrafo(f"Não há evidência de falta de ajuste (p = {p}).")


def _secao_interpretacao(pdf: RelatorioPDF, relatorio: RelatorioTextual) -> None:
    pdf.titulo_secao("Interpretação")
    pdf.paragrafo(f"Texto gerado no modo {relatorio.modo.upper()}.", tamanho=9)
    for aviso in relatorio.avisos:
        pdf.paragrafo(f"Aviso: {aviso}", tamanho=9)
    for secao in relatorio.secoes:
        pdf.set_font(pdf.tema.familia, "B", 10)
        pdf.multi_cell(0, 5.5, secao.titulo, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.paragrafo(secao.texto)


def _apendice(
    pdf: RelatorioPDF, resultado: AnalysisResult, relatorio: RelatorioTextual
) -> None:
    pdf.titulo_secao("Apêndice")
    pdf.rotulo_valor("Esquema do contrato", resultado.metadados.schema_version)
    pdf.rotulo_valor("Versão do prompt", relatorio.prompt_version)
    if relatorio.modelo_usado:
        pdf.rotulo_valor("Modelo de linguagem", relatorio.modelo_usado)
    pdf.rotulo_valor(
        "Versões das bibliotecas",
        _versoes_bibliotecas(resultado.metadados.versao_ensaia),
    )
    if resultado.avisos:
        pdf.ln(1)
        pdf.set_font(pdf.tema.familia, "B", 10)
        pdf.multi_cell(
            0, 5.5, "Avisos da análise", new_x="LMARGIN", new_y="NEXT", align="L"
        )
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
