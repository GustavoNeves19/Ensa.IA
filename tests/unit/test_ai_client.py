"""Testes do adaptador HTTP da camada de IA.

Tudo offline: `httpx.MockTransport` finge ser o provedor e a função de espera é
substituída por uma que só anota quanto dormiria. Nenhum teste toca a rede ou
gasta chave de API.
"""

from __future__ import annotations

import json

import httpx
import pytest

from ensaia.ai.client import (
    ClienteModelo,
    ConfiguracaoModelo,
    ErroDeConexao,
    ErroDeResposta,
    Mensagem,
    RespostaInvalida,
)

URL_BASE = "http://localhost:11434/v1"


def _resposta_ok(texto: str = "Texto gerado.", *, modelo: str = "modelo-teste") -> dict:
    return {
        "model": modelo,
        "choices": [{"message": {"role": "assistant", "content": texto}}],
        "usage": {"prompt_tokens": 42, "completion_tokens": 7},
    }


def _cliente(handler, *, chave_api=None, **kwargs) -> ClienteModelo:
    """Cliente apontado para um MockTransport, que nunca dorme de verdade."""
    config = ConfiguracaoModelo(
        url_base=URL_BASE, modelo="modelo-teste", chave_api=chave_api, **kwargs
    )
    esperas: list[float] = []
    cliente = ClienteModelo(
        config,
        transporte=httpx.MockTransport(handler),
        dormir=esperas.append,
    )
    cliente.esperas = esperas  # type: ignore[attr-defined]  # inspeção nos testes
    return cliente


# --- caminho feliz --------------------------------------------------------


def test_completar_devolve_texto_modelo_e_uso() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_resposta_ok("Olá."))

    with _cliente(handler) as cliente:
        resp = cliente.completar([Mensagem.usuario("oi")])

    assert resp.texto == "Olá."
    assert resp.modelo == "modelo-teste"
    assert resp.tokens_prompt == 42
    assert resp.tokens_resposta == 7


def test_monta_payload_openai_correto() -> None:
    capturado: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado.update(json.loads(request.content))
        return httpx.Response(200, json=_resposta_ok())

    with _cliente(handler) as cliente:
        cliente.completar(
            [Mensagem.sistema("regras"), Mensagem.usuario("fatos")],
            temperatura=0.2,
            max_tokens=120,
        )

    assert capturado["model"] == "modelo-teste"
    assert capturado["stream"] is False
    assert capturado["temperature"] == 0.2
    assert capturado["max_tokens"] == 120
    assert capturado["messages"] == [
        {"role": "system", "content": "regras"},
        {"role": "user", "content": "fatos"},
    ]


def test_temperatura_padrao_vem_da_config() -> None:
    capturado: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado.update(json.loads(request.content))
        return httpx.Response(200, json=_resposta_ok())

    with _cliente(handler, temperatura=0.0) as cliente:
        cliente.completar([Mensagem.usuario("oi")])

    assert capturado["temperature"] == 0.0
    assert "max_tokens" not in capturado  # omitido quando não informado


def test_endpoint_preserva_o_v1() -> None:
    visto: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        visto["url"] = str(request.url)
        return httpx.Response(200, json=_resposta_ok())

    with _cliente(handler) as cliente:
        cliente.completar([Mensagem.usuario("oi")])

    assert visto["url"] == "http://localhost:11434/v1/chat/completions"


# --- autenticação ---------------------------------------------------------


def test_envia_bearer_quando_ha_chave() -> None:
    visto: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        visto["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=_resposta_ok())

    with _cliente(handler, chave_api="segredo-123") as cliente:
        cliente.completar([Mensagem.usuario("oi")])

    assert visto["auth"] == "Bearer segredo-123"


def test_sem_chave_nao_manda_authorization() -> None:
    visto: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        visto["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=_resposta_ok())

    with _cliente(handler, chave_api=None) as cliente:
        cliente.completar([Mensagem.usuario("oi")])

    assert visto["auth"] is None


# --- retry ----------------------------------------------------------------


def test_repete_status_transitorio_e_depois_tem_sucesso() -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        if chamadas["n"] < 3:
            return httpx.Response(503, text="indisponível")
        return httpx.Response(200, json=_resposta_ok("depois de retry"))

    cliente = _cliente(handler)
    resp = cliente.completar([Mensagem.usuario("oi")])

    assert resp.texto == "depois de retry"
    assert chamadas["n"] == 3
    assert cliente.esperas == [0.5, 1.0]  # backoff exponencial, 2 esperas


def test_repete_erro_de_conexao() -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        if chamadas["n"] < 2:
            raise httpx.ConnectError("sem rota", request=request)
        return httpx.Response(200, json=_resposta_ok())

    cliente = _cliente(handler)
    resp = cliente.completar([Mensagem.usuario("oi")])

    assert resp.texto == "Texto gerado."
    assert chamadas["n"] == 2


def test_nao_repete_erro_do_cliente() -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        return httpx.Response(400, text="prompt inválido")

    cliente = _cliente(handler)
    with pytest.raises(ErroDeResposta) as info:
        cliente.completar([Mensagem.usuario("oi")])

    assert info.value.status == 400
    assert chamadas["n"] == 1  # 4xx não repete
    assert cliente.esperas == []


def test_esgota_tentativas_em_status_transitorio() -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        return httpx.Response(503, text="indisponível")

    cliente = _cliente(handler, max_tentativas=3)
    with pytest.raises(ErroDeResposta) as info:
        cliente.completar([Mensagem.usuario("oi")])

    assert info.value.status == 503
    assert chamadas["n"] == 3


def test_timeout_vira_erro_de_conexao_sem_repetir() -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        raise httpx.ReadTimeout("demorou", request=request)

    cliente = _cliente(handler, max_tentativas=3)
    with pytest.raises(ErroDeConexao, match="não respondeu em 30 s"):
        cliente.completar([Mensagem.usuario("oi")])

    assert chamadas["n"] == 1  # tempo esgotado não repete
    assert cliente.esperas == []


def test_tempo_limite_configurado_no_httpx() -> None:
    config = ConfiguracaoModelo(url_base=URL_BASE, modelo="m", timeout_s=12.0)
    with ClienteModelo(config) as cliente:
        assert cliente._cliente.timeout.read == 12.0
        assert cliente._cliente.timeout.connect == 5.0


# --- respostas malformadas ------------------------------------------------


def test_resposta_sem_choices() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"model": "x", "choices": []})

    with _cliente(handler) as cliente, pytest.raises(RespostaInvalida):
        cliente.completar([Mensagem.usuario("oi")])


def test_resposta_com_conteudo_vazio() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "   "}}]}
        )

    with _cliente(handler) as cliente, pytest.raises(RespostaInvalida):
        cliente.completar([Mensagem.usuario("oi")])


def test_resposta_nao_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="não é json")

    with _cliente(handler) as cliente, pytest.raises(RespostaInvalida):
        cliente.completar([Mensagem.usuario("oi")])


def test_uso_ausente_vira_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "ok"}}]}
        )

    with _cliente(handler) as cliente:
        resp = cliente.completar([Mensagem.usuario("oi")])

    assert resp.tokens_prompt is None
    assert resp.tokens_resposta is None


# --- validação de configuração --------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"url_base": "", "modelo": "m"},
        {"url_base": URL_BASE, "modelo": ""},
        {"url_base": URL_BASE, "modelo": "m", "max_tentativas": 0},
        {"url_base": URL_BASE, "modelo": "m", "temperatura": 2.5},
        {"url_base": URL_BASE, "modelo": "m", "temperatura": -0.1},
        {"url_base": URL_BASE, "modelo": "m", "timeout_s": 0},
    ],
)
def test_config_invalida(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        ConfiguracaoModelo(**kwargs)


def test_endpoint_normaliza_barra_final() -> None:
    config = ConfiguracaoModelo(url_base="http://x/v1/", modelo="m")
    assert config.endpoint == "http://x/v1/chat/completions"


def test_mensagem_para_openai() -> None:
    assert Mensagem.sistema("r").para_openai() == {"role": "system", "content": "r"}
    assert Mensagem.usuario("u").para_openai() == {"role": "user", "content": "u"}
    assert Mensagem.assistente("a").para_openai() == {
        "role": "assistant",
        "content": "a",
    }
