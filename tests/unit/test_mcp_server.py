"""Servidor MCP (spec §11): ferramentas, recursos e prompts pelo cliente em memória.

`Client(mcp)` conecta direto no objeto do servidor, sem processo, porta nem
rede; é o jeito que o próprio SDK testa os seus exemplos.
"""

from __future__ import annotations

import base64
import csv
import io
import itertools
import subprocess
import sys

import pytest

pytest.importorskip("mcp")

from mcp import Client
from mcp.types import (
    BlobResourceContents,
    EmbeddedResource,
    TextResourceContents,
)

from ensaia import __version__
from ensaia.core.fluxo import analisar_tabela
from ensaia.io.modelo import planilha_modelo_xlsx
from ensaia.io.readers import ler_dados_de_bytes
from ensaia.mcp_server.server import mcp

FATORES = ["dose_adsorvente", "tempo_mistura", "ph"]
RESPOSTA = "remocao_mnz"

# DCCR sintético de 3 fatores (8 pontos fatoriais + 6 axiais + 6 centrais = 20
# ensaios, α=1,682 rotacional). Não há exemplo DCCR público curado ainda (ver
# ensaia/exemplos/__init__.py), então os testes do servidor MCP usam dados
# fabricados com uma resposta quadrática côncava conhecida — máximo interior
# garantido, bom para exercitar ponto estacionário e otimização.
_ALFA = 1.682
_CENTRO_PASSO = {
    "dose_adsorvente": (0.6, 0.15),
    "tempo_mistura": (35.0, 10.0),
    "ph": (7.0, 1.5),
}
_RUIDO = [
    1.8, -1.2, 0.6, -2.4, 1.2, 0.6, -1.8, 1.2, 0.6, -0.6,
    1.2, -1.2, 0.6, -0.6, 0.3, -0.3, 0.0, 0.6, -0.6, 0.3,
]


def _dccr_csv() -> str:
    pontos = [
        *itertools.product((-1.0, 1.0), repeat=3),
        (-_ALFA, 0.0, 0.0), (_ALFA, 0.0, 0.0),
        (0.0, -_ALFA, 0.0), (0.0, _ALFA, 0.0),
        (0.0, 0.0, -_ALFA), (0.0, 0.0, _ALFA),
        *([(0.0, 0.0, 0.0)] * 6),
    ]
    linhas = []
    for (x1, x2, x3), ruido in zip(pontos, _RUIDO, strict=True):
        y = (
            90 + 5 * x1 + 3 * x2 - 2 * x3
            - 4 * x1**2 - 3 * x2**2 - 2 * x3**2 + x1 * x2
            + ruido
        )
        linha = {
            nome: round(centro + coord * passo, 4)
            for (nome, (centro, passo)), coord in zip(
                _CENTRO_PASSO.items(), (x1, x2, x3), strict=True
            )
        }
        linha[RESPOSTA] = round(y, 2)
        linhas.append(linha)
    buf = io.StringIO()
    escritor = csv.DictWriter(buf, fieldnames=[*_CENTRO_PASSO, RESPOSTA])
    escritor.writeheader()
    escritor.writerows(linhas)
    return buf.getvalue()


CSV = _dccr_csv()

# Fatorial 2² com 3 pontos centrais: triagem, com efeitos e curvatura.
FATORIAL = "a,b,y\n-1,-1,10\n1,-1,18\n-1,1,12\n1,1,25\n0,0,16\n0,0,15.5\n0,0,16.4\n"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _chamar(nome: str, argumentos: dict[str, object]) -> dict[str, object]:
    async with Client(mcp) as cliente:
        resultado = await cliente.call_tool(nome, argumentos)
    assert not resultado.is_error, resultado.content
    assert isinstance(resultado.structured_content, dict)
    return resultado.structured_content


@pytest.mark.anyio
async def test_lista_as_ferramentas_da_spec() -> None:
    async with Client(mcp) as cliente:
        nomes = {t.name for t in (await cliente.list_tools()).tools}
    assert nomes == {
        "read_table",
        "detect_design",
        "fit_model",
        "compute_effects",
        "check_residuals",
        "find_stationary_point",
        "optimize",
        "run_full_analysis",
        "render_pdf",
        "verify_text",
    }


@pytest.mark.anyio
async def test_read_table_sugere_papeis_e_devolve_csv_normalizado() -> None:
    lido = await _chamar("read_table", {"data_csv": CSV})
    papeis = {c["nome"]: c["papel_sugerido"] for c in lido["colunas"]}
    assert papeis == {**dict.fromkeys(FATORES, "fator"), RESPOSTA: "resposta"}
    assert lido["linhas"] == 20
    assert str(lido["data_csv"]).startswith("dose_adsorvente,tempo_mistura,ph,")


@pytest.mark.anyio
async def test_read_table_le_xlsx_em_base64_e_recusa_caminho_no_http() -> None:
    planilha = base64.b64encode(planilha_modelo_xlsx()).decode("ascii")
    lido = await _chamar(
        "read_table",
        {"file_base64": planilha, "filename": "modelo.xlsx", "sheet": "Dados"},
    )
    assert lido["abas"] == ["Dados", "Como preencher"]
    async with Client(mcp) as cliente:
        recusa = await cliente.call_tool("read_table", {"path": "/etc/passwd"})
    assert recusa.is_error
    assert "seu computador" in str(recusa.content[0])


@pytest.mark.anyio
async def test_analise_completa_da_os_mesmos_numeros_da_tela() -> None:
    feita = await _chamar(
        "run_full_analysis",
        {"data_csv": CSV, "factors": FATORES, "responses": [RESPOSTA]},
    )
    tabela = ler_dados_de_bytes(CSV.encode("utf-8"), "dccr.csv")
    tela = analisar_tabela(tabela, FATORES, [RESPOSTA], versao_ensaia=__version__)
    resultado = feita["analysis_result"]
    assert resultado["ajustes"][0]["r2"] == pytest.approx(tela.resultado.ajustes[0].r2)
    assert resultado["tipo_planejamento"] == "composto_central"
    assert feita["fatos"]["modelo"]


@pytest.mark.anyio
async def test_ferramentas_de_cada_etapa() -> None:
    base = {"data_csv": CSV, "factors": FATORES}
    planejamento = await _chamar("detect_design", {**base, "responses": [RESPOSTA]})
    assert planejamento["planejamento"]["n_pontos_centrais"] == 6
    modelo = await _chamar("fit_model", {**base, "response": RESPOSTA})
    assert modelo["equacao"]["codificada"].startswith("ŷ")
    residuos = await _chamar("check_residuals", {**base, "response": RESPOSTA})
    assert len(residuos["diagnostico"]["residuos"]) == 20
    estacionario = await _chamar(
        "find_stationary_point", {**base, "response": RESPOSTA}
    )
    assert estacionario["ponto_estacionario"]["natureza"] == "maximo"
    otimo = await _chamar(
        "optimize", {**base, "responses": [RESPOSTA], "goals": {RESPOSTA: "maximizar"}}
    )
    assert otimo["ponto_otimo"]["desejabilidade_global"] > 0.9


@pytest.mark.anyio
async def test_efeitos_de_um_fatorial_fica_sem_grupo_b() -> None:
    # Um fatorial 2² (mesmo com pontos centrais) não é mais um tipo
    # reconhecido (ADR 0013): "efeitos_fatorial" (Grupo B) vem None. O Pareto
    # (B2) não depende do tipo fatorial e continua disponível.
    efeitos = await _chamar(
        "compute_effects",
        {"data_csv": FATORIAL, "factors": ["a", "b"], "response": "y"},
    )
    assert efeitos["efeitos_fatorial"] is None
    assert efeitos["pareto"][0]["termo"] == "a"


@pytest.mark.anyio
async def test_pdf_e_conferencia_do_texto() -> None:
    feita = await _chamar(
        "run_full_analysis",
        {"data_csv": CSV, "factors": FATORES, "responses": [RESPOSTA]},
    )
    async with Client(mcp) as cliente:
        pdf = await cliente.call_tool(
            "render_pdf",
            {"analysis_result": feita["analysis_result"], "data_csv": CSV},
        )
    (bloco,) = pdf.content
    assert isinstance(bloco, EmbeddedResource)
    assert isinstance(bloco.resource, BlobResourceContents)
    assert base64.b64decode(bloco.resource.blob)[:5] == b"%PDF-"

    conferido = await _chamar(
        "verify_text",
        {
            "text": "O modelo explicou 99,7% da variação (R² = 0,995).",
            "analysis_result": feita["analysis_result"],
        },
    )
    assert conferido["fiel"] is False
    assert conferido["sem_correspondencia"] == ["99,7"]


@pytest.mark.anyio
async def test_erro_de_dados_volta_em_portugues_sem_derrubar_o_servidor() -> None:
    async with Client(mcp) as cliente:
        resultado = await cliente.call_tool(
            "run_full_analysis",
            {"data_csv": CSV, "factors": ["nao_existe"], "responses": [RESPOSTA]},
        )
    assert resultado.is_error
    assert "nao_existe" in str(resultado.content[0])


@pytest.mark.anyio
async def test_recursos_e_prompts() -> None:
    # Sem exemplo DCCR curado ainda (ver ensaia/exemplos/__init__.py), então
    # "doe://exemplos/{nome}" não tem nenhum id válido para testar o caminho
    # feliz agora — só confere que ele falha com uma mensagem útil.
    async with Client(mcp) as cliente:
        glossario = await cliente.read_resource("doe://glossario")
        catalogo = await cliente.read_resource("doe://catalogo")
        prompt = await cliente.get_prompt("relatorio_completo", {"contexto": "TCC"})
        with pytest.raises(Exception, match="metronidazol"):
            await cliente.read_resource("doe://exemplos/metronidazol")
    textos = [
        c.text
        for r in (glossario, catalogo)
        for c in r.contents
        if isinstance(c, TextResourceContents)
    ]
    assert "Fator" in textos[0]
    assert "E5" in textos[1]
    assert "run_full_analysis" in str(prompt.messages[0].content)


def test_interface_nao_importa_o_sdk_do_mcp_na_partida() -> None:
    codigo = (
        "import sys, ensaia.app.main as m; "
        "print(m.mcp_http is not None, 'mcp' in sys.modules)"
    )
    saida = subprocess.run(
        [sys.executable, "-c", codigo], capture_output=True, text=True, check=True
    )
    assert saida.stdout.split()[-2:] == ["True", "False"]


@pytest.mark.anyio
async def test_rota_http_carrega_o_mcp_so_na_primeira_chamada() -> None:
    import httpx
    from fastapi import FastAPI

    from ensaia.mcp_server.montagem import MCPSobDemanda

    sob_demanda = MCPSobDemanda()
    app = FastAPI()
    app.mount("/api", sob_demanda)
    assert not sob_demanda.carregado
    pedido = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "teste", "version": "1"},
        },
    }
    transporte = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(
            transport=transporte, base_url="http://localhost:8080"
        ) as cliente:
            resposta = await cliente.post(
                "/api/mcp",
                json=pedido,
                headers={"Accept": "application/json, text/event-stream"},
            )
        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["result"]["serverInfo"]["name"] == "EnsaIA"
        assert sob_demanda.carregado
    finally:
        await sob_demanda.encerrar()
