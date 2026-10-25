"""As ferramentas, os recursos e os prompts do EnsaIA para assistentes de IA.

## O que é o MCP, do zero

O *Model Context Protocol* é um jeito padronizado de um assistente de IA usar
programas de fora. O servidor (este arquivo) diz "tenho estas ferramentas, com
estes parâmetros"; o assistente decide chamar uma, recebe a resposta em JSON e
continua a conversa. Aqui, cada ferramenta é uma etapa da análise do EnsaIA.

O assistente orquestra e escreve; quem calcula é sempre o núcleo, pelo mesmo
caminho da tela (`core.fluxo`). Por isso um modelo pequeno, rodando no
computador do usuário, entrega os mesmos números de um químico usando a tela.

Sem estado (spec §11.1): toda ferramenta recebe os dados no próprio chamado.
Planilhas de DOE têm dezenas de linhas, então repassar o CSV é barato e nada
precisa ficar guardado no servidor (princípio P1).

## Como subir

    ensaia-mcp          # stdio: local e privado (Claude Desktop, LM Studio…)

No servidor web, o mesmo `mcp` atende em `/api/mcp` (ver `montagem.py`).
"""

from __future__ import annotations

import base64
import binascii
import os
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import BlobResourceContents, EmbeddedResource
from pydantic import BaseModel
from starlette.applications import Starlette

from ensaia import __version__
from ensaia.ai.fidelity import verificar_texto
from ensaia.ai.report import gerar_relatorio, relatorio_colado
from ensaia.core.catalogo import CATALOGO
from ensaia.core.descritiva import matriz_ensaios
from ensaia.core.design import INTERCEPTO, Planejamento
from ensaia.core.facts import fatos_por_secao
from ensaia.core.fluxo import AnaliseDaTabela, analisar_tabela, sugerir_mapeamento
from ensaia.core.indicativos import proximos_passos
from ensaia.core.pipeline import fatores_do_contrato, limite_da_regiao
from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    Sentido,
    TermoErro,
    TipoModelo,
)
from ensaia.core.table import Table
from ensaia.exemplos import EXEMPLOS, conteudo_exemplo
from ensaia.io.escrita import tabela_para_csv
from ensaia.io.readers import formato_csv, ler_dados_de_bytes, listar_abas

# Mesmo teto do envio pela tela (RF-01).
MAX_BYTES = 5 * 1024 * 1024
_LINHAS_PREVIA = 10
_CONTEUDO = files("ensaia") / "conteudo"

Modelo = Literal["auto", "linear", "interacoes", "quadratico"]

mcp = MCPServer(
    "EnsaIA",
    title="EnsaIA: análise de experimentos químicos (DOE)",
    version=__version__,
    instructions=(
        "Ferramentas de planejamento de experimentos (DOE). Fluxo sugerido: "
        "read_table para ler a planilha e ver o papel sugerido de cada coluna; "
        "run_full_analysis para obter todos os resultados de uma vez; escreva a "
        "explicação usando SOMENTE os números e os fatos devolvidos; confira o "
        "texto com verify_text. Nunca calcule nada por conta própria."
    ),
)

# `path` só faz sentido (e só é seguro) no modo local, stdio: no servidor web,
# ler um caminho seria ler arquivos do próprio servidor.
_LER_CAMINHO = False


# --- Ferramentas --------------------------------------------------------------


@mcp.tool(title="Ler planilha")
def read_table(
    data_csv: str | None = None,
    file_base64: str | None = None,
    filename: str | None = None,
    sheet: str | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Lê a planilha do experimento e sugere o papel de cada coluna.

    Passe UMA das entradas: `data_csv` (o texto do CSV), `file_base64` +
    `filename` (arquivo .xlsx, .xls, .ods, .csv codificado em base64) ou
    `path` (só quando o EnsaIA roda no seu computador). `sheet` escolhe a aba.
    Devolve as colunas, uma prévia, o formato detectado e `data_csv`
    normalizado: use esse `data_csv` nas outras ferramentas.

    Exemplo: read_table(data_csv="temp,ph,rend\\n40,5,61.2\\n60,5,70.4\\n...")
    """
    conteudo, nome = _entrada(data_csv, file_base64, filename, path)
    try:
        abas = listar_abas(conteudo, nome)
        tabela = ler_dados_de_bytes(conteudo, nome, aba=sheet)
    except (ValueError, FileNotFoundError) as erro:
        raise ToolError(str(erro)) from erro
    papeis = sugerir_mapeamento(tabela)
    formato = formato_csv(conteudo, nome)
    return {
        "linhas": len(tabela),
        "colunas": [
            {
                "nome": c,
                "tipo": "numérica" if tabela.e_numerica(c) else "texto",
                "papel_sugerido": papeis[c],
            }
            for c in tabela.colunas
        ],
        "previa": [
            {c: tabela.texto(c)[i] for c in tabela.colunas}
            for i in range(min(len(tabela), _LINHAS_PREVIA))
        ],
        "abas": abas,
        "formato": (
            {
                "separador": formato.separador,
                "decimal": formato.decimal,
                "codificacao": formato.codificacao,
            }
            if formato
            else None
        ),
        "data_csv": tabela_para_csv(tabela),
    }


@mcp.tool(title="Reconhecer o planejamento")
def detect_design(
    data_csv: str, factors: list[str], responses: list[str]
) -> dict[str, Any]:
    """Reconhece o planejamento (só o composto central rotacional — DCCR).

    Devolve o tipo, o número de ensaios e de pontos centrais, a codificação de
    cada fator (centro e passo, em unidades reais) e os avisos. Outras
    geometrias (fatorial, Box-Behnken etc.) voltam como "desconhecido", com um
    aviso que diz a que mais se parecem — fora do escopo atual (ADR 0013).

    Exemplo: detect_design(data_csv, factors=["temp", "ph"], responses=["rend"])
    """
    feita = _analisar(data_csv, factors, responses, analises=["A2"])
    resultado = feita.resultado
    return {
        "tipo_planejamento": resultado.tipo_planejamento,
        "planejamento": _json(resultado.planejamento),
        "avisos": resultado.avisos,
    }


@mcp.tool(title="Ajustar o modelo")
def fit_model(
    data_csv: str,
    factors: list[str],
    response: str,
    model_type: Modelo = "auto",
    excluded_terms: list[str] | None = None,
    error_term: TermoErro = "residuo",
    alpha: float = 0.05,
    block_column: str | None = None,
) -> dict[str, Any]:
    """Ajusta o modelo de regressão: coeficientes, ANOVA, R² e equações.

    `model_type`: "auto" (escolhe pelo planejamento), "linear", "interacoes"
    ou "quadratico". `excluded_terms` tira termos (ex.: ["temp:ph"]).
    `error_term`: "residuo" ou "erro_puro" (exige réplicas).
    `block_column`: coluna que agrupa os ensaios em blocos (dias, lotes); a
    diferença entre blocos sai do erro e aparece na linha "Blocos" da ANOVA.

    Exemplo: fit_model(data_csv, ["temp", "ph"], "rend", model_type="quadratico")
    """
    ajuste = _um_ajuste(
        data_csv,
        factors,
        response,
        ["C1", "C2", "C3", "C4", "C5"],
        model_type,
        excluded_terms,
        error_term,
        alpha,
        coluna_bloco=block_column,
    )
    return _dict(
        ajuste,
        incluir={
            "efeitos_bloco",
            "resposta",
            "coeficientes",
            "anova",
            "anova_regressao",
            "r2",
            "r2_ajustado",
            "r2_predicao",
            "r2_maximo",
            "falta_de_ajuste",
            "equacao",
            "termos_incluidos",
            "termos_descartados",
            "termo_erro",
            "t_critico",
        },
    )


@mcp.tool(title="Calcular os efeitos")
def compute_effects(
    data_csv: str,
    factors: list[str],
    response: str,
    error_term: TermoErro = "residuo",
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Efeitos de um fatorial: efeito de cada termo, Pareto, Lenth e curvatura.

    Efeito, Lenth e curvatura só saem para um fatorial 2^k de triagem — fora do
    escopo atual (ADR 0013), então sempre vêm vazios num DCCR. Os dados do
    Pareto (|t| de cada termo) saem sempre, para qualquer planejamento.

    Exemplo: compute_effects(data_csv, ["a", "b", "c"], "rend")
    """
    ajuste = _um_ajuste(
        data_csv,
        factors,
        response,
        ["C1"],
        "auto",
        None,
        error_term,
        alpha,
    )
    termos = sorted(
        (c for c in ajuste.coeficientes if c.termo != INTERCEPTO),
        key=lambda c: abs(c.valor_t),
        reverse=True,
    )
    pareto = [
        {"termo": c.termo, "t": abs(c.valor_t), "significativo": c.significativo}
        for c in termos
    ]
    return {
        "efeitos_fatorial": _json(ajuste.efeitos_fatorial),
        "pareto": pareto,
        "t_critico": ajuste.t_critico,
    }


@mcp.tool(title="Diagnóstico dos resíduos")
def check_residuals(
    data_csv: str,
    factors: list[str],
    response: str,
    model_type: Modelo = "auto",
    order_column: str | None = None,
) -> dict[str, Any]:
    """Resíduos por ensaio, normalidade (Shapiro-Wilk), alavancagem e Cook.

    `order_column` é a coluna com a ordem de execução, se houver.

    Exemplo: check_residuals(data_csv, ["temp", "ph"], "rend")
    """
    ajuste = _um_ajuste(
        data_csv,
        factors,
        response,
        ["C6", "D1", "D2", "D3", "D4"],
        model_type,
        None,
        "residuo",
        0.05,
        order_column,
    )
    return {"diagnostico": _json(ajuste.diagnostico)}


@mcp.tool(title="Ponto estacionário")
def find_stationary_point(
    data_csv: str, factors: list[str], response: str
) -> dict[str, Any]:
    """Onde a superfície fica plana: máximo, mínimo ou sela, e se cai na região.

    Exemplo: find_stationary_point(data_csv, ["temp", "ph", "tempo"], "rend")
    """
    ajuste = _um_ajuste(
        data_csv, factors, response, ["E3"], "auto", None, "residuo", 0.05
    )
    if ajuste.ponto_estacionario is None:
        raise ToolError(
            "Sem ponto estacionário: o modelo precisa de termos quadráticos "
            "(planejamento com três ou mais níveis por fator)."
        )
    return {"ponto_estacionario": _json(ajuste.ponto_estacionario)}


@mcp.tool(title="Otimizar")
def optimize(
    data_csv: str,
    factors: list[str],
    responses: list[str],
    goals: dict[str, Sentido] | None = None,
) -> dict[str, Any]:
    """Melhor condição dentro da região estudada, por desejabilidade.

    `goals` diz o que fazer com cada resposta: "maximizar" ou "minimizar"
    (padrão: maximizar todas).

    Exemplo: optimize(data_csv, ["temp", "ph"], ["rend"], {"rend": "maximizar"})
    """
    feita = _analisar(
        data_csv, factors, responses, analises=["E4", "E5"], objetivos=goals
    )
    if feita.resultado.ponto_otimo is None:
        raise ToolError("Não foi possível otimizar com estes dados.")
    return {"ponto_otimo": _json(feita.resultado.ponto_otimo)}


@mcp.tool(title="Análise completa")
def run_full_analysis(
    data_csv: str,
    factors: list[str],
    responses: list[str],
    analyses: list[str] | None = None,
    model_type: Modelo = "auto",
    error_term: TermoErro = "residuo",
    alpha: float = 0.05,
    goals: dict[str, Sentido] | None = None,
    order_column: str | None = None,
    block_column: str | None = None,
) -> dict[str, Any]:
    """Tudo numa chamada só: o resultado completo e os fatos já interpretados.

    `block_column` (opcional): coluna que agrupa os ensaios em blocos (dias,
    lotes); a diferença entre blocos sai do erro antes de testar os fatores.

    `analyses` escolhe as análises pelos IDs do catálogo (A1–E5; padrão: todas
    as que os dados permitem). Devolve `analysis_result` (o resultado completo,
    para render_pdf e verify_text), `fatos`: frases prontas por seção, com os
    números já verificados — escreva a explicação a partir delas — e
    `proximos_passos`: o que o usuário pode fazer em seguida.

    Exemplo: run_full_analysis(data_csv, ["temp", "ph"], ["rend"])
    """
    feita = _analisar(
        data_csv,
        factors,
        responses,
        analises=analyses,
        tipo_modelo=model_type,
        termo_erro=error_term,
        alfa=alpha,
        objetivos=goals,
        coluna_ordem=order_column,
        coluna_bloco=block_column,
    )
    resultado = feita.resultado
    return {
        "analysis_result": _json(resultado),
        "fatos": fatos_por_secao(resultado, alfa=resultado.metadados.alfa),
        "proximos_passos": proximos_passos(
            resultado, limite_codificado=limite_da_regiao(feita.planejamento)
        ),
    }


@mcp.tool(title="Gerar o PDF")
def render_pdf(
    analysis_result: dict[str, Any],
    text: str | None = None,
    data_csv: str | None = None,
) -> EmbeddedResource:
    """Relatório PDF do resultado, com as seções das análises feitas.

    `analysis_result` é o devolvido por run_full_analysis. `text`, se vier, é o
    texto que você escreveu: ele entra no PDF com a conferência dos números.
    `data_csv` acrescenta a matriz dos ensaios. Devolve o PDF em base64.
    """
    try:
        from ensaia.report import gerar_pdf  # extra [report]: fpdf2 + matplotlib
    except ImportError as erro:
        raise ToolError("Este servidor não tem o extra [report] instalado.") from erro
    resultado = _resultado(analysis_result)
    relatorio = (
        relatorio_colado(resultado, text) if text else gerar_relatorio(resultado)
    )
    dados = None
    if data_csv and resultado.planejamento is not None:
        tabela = _tabela(data_csv)
        plan = Planejamento(
            resultado.tipo_planejamento, fatores_do_contrato(resultado.planejamento)
        )
        dados = matriz_ensaios(tabela, plan, resultado.respostas)
    pdf = gerar_pdf(resultado, relatorio, dados=dados)
    return EmbeddedResource(
        type="resource",
        resource=BlobResourceContents(
            uri="ensaia://relatorio.pdf",
            mime_type="application/pdf",
            blob=base64.b64encode(pdf).decode("ascii"),
        ),
    )


@mcp.tool(title="Conferir um texto")
def verify_text(text: str, analysis_result: dict[str, Any]) -> dict[str, Any]:
    """Confere cada número do texto contra o resultado (fidelidade, spec §12.5).

    Devolve quantos números conferem, os que não têm correspondência (com o
    trecho) e as afirmações de significância que contradizem os p-valores.
    Corrija o texto até `fiel` ser verdadeiro.
    """
    resultado = _resultado(analysis_result)
    fid = verificar_texto(text, resultado)
    return {
        "fiel": fid.fiel,
        "resumo": fid.resumo(),
        "total_numeros": fid.total,
        "numeros_que_conferem": fid.rastreaveis,
        "percentual": fid.percentual,
        "sem_correspondencia": [text[n.inicio : n.fim] for n in fid.nao_rastreaveis],
        "contradicoes": [c.descricao() for c in fid.contradicoes],
    }


# --- Recursos -------------------------------------------------------------------


@mcp.resource("doe://glossario", mime_type="text/markdown")
def glossario() -> str:
    """Glossário de DOE em linguagem simples."""
    return (_CONTEUDO / "glossario.md").read_text(encoding="utf-8")


@mcp.resource("doe://guia-interpretacao", mime_type="text/markdown")
def guia_interpretacao() -> str:
    """Como ler ANOVA, p-valor, R², falta de ajuste e desejabilidade."""
    return (_CONTEUDO / "guia-interpretacao.md").read_text(encoding="utf-8")


@mcp.resource("doe://catalogo", mime_type="text/markdown")
def catalogo() -> str:
    """Os IDs das análises (A1–E5) aceitos por run_full_analysis."""
    return "\n".join(f"- {a.id}: {a.nome}" for a in CATALOGO)


@mcp.resource("doe://exemplos", mime_type="text/markdown")
def exemplos() -> str:
    """Datasets públicos de exemplo, com a fonte de cada um."""
    return "\n".join(
        f"- doe://exemplos/{e.id}: {e.titulo}. {e.descricao} Fonte: {e.citacao}"
        for e in EXEMPLOS.values()
    )


@mcp.resource("doe://exemplos/{nome}", mime_type="text/csv")
def exemplo(nome: str) -> str:
    """Um dataset público de exemplo, em CSV (ver doe://exemplos)."""
    if nome not in EXEMPLOS:
        raise ValueError(f"Exemplo {nome!r} não existe. Opções: {sorted(EXEMPLOS)}.")
    return conteudo_exemplo(nome).decode("utf-8")


# --- Prompts ----------------------------------------------------------------------


@mcp.prompt(title="Relatório completo")
def relatorio_completo(contexto: str = "") -> str:
    """Redige o relatório em seções a partir de run_full_analysis."""
    return (
        "Analise o experimento com as ferramentas do EnsaIA e escreva um relatório "
        "técnico em português do Brasil.\n"
        "1. Chame read_table com a planilha e confirme fatores e respostas.\n"
        "2. Chame run_full_analysis com o data_csv devolvido.\n"
        "3. Escreva uma seção para cada grupo de `fatos` (planejamento, modelo, "
        "ANOVA, diagnóstico, otimização), usando SOMENTE os números deles, sem "
        "refazer contas nem arredondar de outro jeito.\n"
        "4. Chame verify_text com o seu texto e corrija o que não conferir.\n"
        f"{_contexto(contexto)}"
    )


@mcp.prompt(title="Explicar para quem não é da área")
def explicar_para_leigo(contexto: str = "") -> str:
    """Explica os resultados sem jargão."""
    return (
        "Explique o resultado do run_full_analysis para alguém que não é da "
        "área: o que foi testado, o que fez diferença na resposta e qual a "
        "melhor condição. Sem jargão estatístico; quando um termo técnico for "
        "inevitável, explique-o em uma frase (veja doe://glossario). Use só os "
        f"números dos fatos.\n{_contexto(contexto)}"
    )


@mcp.prompt(title="Explicar a ANOVA")
def explicar_anova(contexto: str = "") -> str:
    """Explica a tabela ANOVA passo a passo."""
    return (
        "Explique a tabela ANOVA do resultado passo a passo: o que é cada linha "
        "(regressão, resíduo, falta de ajuste, erro puro), o que significam F e "
        "p, o que diz o R² e se o modelo é adequado. Siga doe://guia-interpretacao "
        f"e use só os números do resultado.\n{_contexto(contexto)}"
    )


@mcp.prompt(title="Próximo experimento")
def proximo_experimento(contexto: str = "") -> str:
    """Sugere próximos passos a partir do resultado."""
    return (
        "A partir do resultado, sugira o próximo experimento: se o ponto "
        "estacionário ou o ótimo caem fora ou na borda da região, proponha "
        "deslocar a região naquela direção; se há falta de ajuste, um modelo de "
        "ordem maior; sempre um ensaio de confirmação na melhor condição. "
        "Justifique cada sugestão com os números do resultado.\n"
        f"{_contexto(contexto)}"
    )


# --- HTTP e stdio -------------------------------------------------------------------


def app_http() -> Starlette:
    """O app ASGI do MCP em modo HTTP sem estado, para montar em `/api`.

    `ENSAIA_HOSTS` (domínios públicos separados por vírgula) libera o servidor
    para atender por esses nomes; sem ela, só localhost é aceito (proteção do
    SDK contra *DNS rebinding*).
    """
    hosts = [h.strip() for h in os.environ.get("ENSAIA_HOSTS", "").split(",")]
    hosts = [h for h in hosts if h]
    seguranca = None
    if hosts:
        locais = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
        seguranca = TransportSecuritySettings(
            allowed_hosts=[*locais, *hosts, *(f"{h}:*" for h in hosts)],
            allowed_origins=[f"https://{h}" for h in hosts],
        )
    return mcp.streamable_http_app(
        stateless_http=True, json_response=True, transport_security=seguranca
    )


def main() -> None:
    """`ensaia-mcp`: o servidor por stdio, local e privado (spec §11.1)."""
    global _LER_CAMINHO
    _LER_CAMINHO = True
    mcp.run()


# --- Internos ------------------------------------------------------------------------


def _entrada(
    data_csv: str | None,
    file_base64: str | None,
    filename: str | None,
    path: str | None,
) -> tuple[bytes, str]:
    if data_csv is not None:
        conteudo, nome = data_csv.encode("utf-8"), "dados.csv"
    elif file_base64 is not None:
        try:
            conteudo = base64.b64decode(file_base64, validate=True)
        except (binascii.Error, ValueError) as erro:
            raise ToolError("file_base64 não é um base64 válido.") from erro
        nome = filename or "dados.csv"
    elif path is not None:
        if not _LER_CAMINHO:
            raise ToolError(
                "`path` só funciona com o EnsaIA rodando no seu computador "
                "(ensaia-mcp). Envie o arquivo em file_base64."
            )
        caminho = Path(path).expanduser()
        if not caminho.is_file():
            raise ToolError(f"Arquivo não encontrado: {caminho}.")
        conteudo, nome = caminho.read_bytes(), caminho.name
    else:
        raise ToolError("Passe data_csv, file_base64 (com filename) ou path.")
    if len(conteudo) > MAX_BYTES:
        raise ToolError("Arquivo acima de 5 MB.")
    return conteudo, nome


def _tabela(data_csv: str) -> Table:
    try:
        return ler_dados_de_bytes(data_csv.encode("utf-8"), "dados.csv")
    except ValueError as erro:
        raise ToolError(str(erro)) from erro


def _analisar(
    data_csv: str,
    fatores: Sequence[str],
    respostas: Sequence[str],
    *,
    analises: Sequence[str] | None = None,
    tipo_modelo: Modelo = "auto",
    excluidos: Sequence[str] = (),
    termo_erro: TermoErro = "residuo",
    alfa: float = 0.05,
    objetivos: dict[str, Sentido] | None = None,
    coluna_ordem: str | None = None,
    coluna_bloco: str | None = None,
) -> AnaliseDaTabela:
    tabela = _tabela(data_csv)
    modelo: TipoModelo | None = None if tipo_modelo == "auto" else tipo_modelo
    try:
        return analisar_tabela(
            tabela,
            fatores,
            respostas,
            versao_ensaia=__version__,
            alfa=alfa,
            tipo_modelo=modelo,
            excluidos=excluidos,
            termo_erro=termo_erro,
            coluna_ordem=coluna_ordem,
            analises=analises,
            objetivos=objetivos,
            coluna_bloco=coluna_bloco,
        )
    except (ValueError, KeyError) as erro:
        raise ToolError(str(erro)) from erro


def _um_ajuste(
    data_csv: str,
    fatores: Sequence[str],
    resposta: str,
    analises: Sequence[str],
    tipo_modelo: Modelo,
    excluidos: Sequence[str] | None,
    termo_erro: TermoErro,
    alfa: float,
    coluna_ordem: str | None = None,
    coluna_bloco: str | None = None,
) -> AjusteResposta:
    feita = _analisar(
        data_csv,
        fatores,
        [resposta],
        analises=analises,
        tipo_modelo=tipo_modelo,
        excluidos=excluidos or (),
        termo_erro=termo_erro,
        alfa=alfa,
        coluna_ordem=coluna_ordem,
        coluna_bloco=coluna_bloco,
    )
    return feita.resultado.ajustes[0]


def _resultado(dados: dict[str, Any]) -> AnalysisResult:
    try:
        return AnalysisResult.model_validate(dados)
    except ValueError as erro:
        raise ToolError(
            "analysis_result inválido: passe o objeto devolvido por "
            f"run_full_analysis. Detalhe: {erro}"
        ) from erro


def _json(modelo: BaseModel | None) -> dict[str, Any] | None:
    """Um modelo do contrato em JSON puro (o que o assistente recebe)."""
    return None if modelo is None else _dict(modelo)


def _dict(modelo: BaseModel, incluir: set[str] | None = None) -> dict[str, Any]:
    return modelo.model_dump(mode="json", include=incluir)


def _contexto(contexto: str) -> str:
    return f"\nContexto do usuário: {contexto}" if contexto.strip() else ""
