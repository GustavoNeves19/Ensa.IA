"""Adaptador HTTP para modelos de linguagem compatíveis com OpenAI.

Este é o único ponto do sistema que fala com um modelo de linguagem. Ele manda
um prompt e recebe texto — nada de cadeia, agente ou RAG (ADR 0006). O formato
é o `/v1/chat/completions` da OpenAI, que Ollama, LM Studio e a maioria dos
provedores de nuvem também expõem; por isso o mesmo adaptador atende o modo M2
(Ollama local) e o M3 (nuvem com chave do usuário), mudando só URL, modelo e
chave.

O que o adaptador faz, e que justifica existir em vez de uma chamada crua:

- **Timeout** explícito (um servidor que "adormece" não pode travar a UI).
- **Retry** com espera crescente para falhas transitórias (queda de conexão,
  429 "muitas requisições", 5xx do provedor) — e só para essas; um 400 é erro
  nosso de prompt e não adianta repetir.
- **Erros tipados**, para a camada de cima distinguir "a rede caiu" de "o
  provedor recusou" de "veio uma resposta sem texto" e decidir o fallback.

Projetado para ser testável sem rede: o `transporte` e a função de espera são
injetáveis, então os testes usam `httpx.MockTransport` e não dormem de verdade
nem gastam chave de API.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import sleep
from types import TracebackType

import httpx

# Papéis da conversa no protocolo da OpenAI. São valores de fio (como um verbo
# HTTP), por isso ficam em inglês mesmo num código em português — o servidor só
# entende exatamente estas três palavras.
Papel = str

# Status HTTP que vale a pena repetir: "muitas requisições" e falhas do lado do
# servidor costumam ser passageiras. Um 4xx (exceto 429) é erro da requisição e
# repetir só desperdiça tempo.
_STATUS_REPETIVEIS = frozenset({429, 500, 502, 503, 504})


class ErroDeIA(Exception):
    """Base de todas as falhas da camada de IA."""


class ErroDeConexao(ErroDeIA):
    """A requisição não chegou a receber resposta (rede, DNS, timeout)."""


class ErroDeResposta(ErroDeIA):
    """O provedor respondeu com um status de erro (4xx/5xx)."""

    def __init__(self, mensagem: str, *, status: int) -> None:
        super().__init__(mensagem)
        self.status = status


class RespostaInvalida(ErroDeIA):
    """A resposta veio com status de sucesso, mas sem texto utilizável."""


@dataclass(frozen=True)
class Mensagem:
    """Uma fala da conversa enviada ao modelo."""

    papel: Papel
    conteudo: str

    @classmethod
    def sistema(cls, conteudo: str) -> Mensagem:
        """Instrução de papel/regras (o "system prompt")."""
        return cls("system", conteudo)

    @classmethod
    def usuario(cls, conteudo: str) -> Mensagem:
        """O pedido em si (os fatos a reescrever)."""
        return cls("user", conteudo)

    @classmethod
    def assistente(cls, conteudo: str) -> Mensagem:
        """Uma resposta de exemplo (usada em few-shot)."""
        return cls("assistant", conteudo)

    def para_openai(self) -> dict[str, str]:
        return {"role": self.papel, "content": self.conteudo}


@dataclass(frozen=True)
class RespostaModelo:
    """O que o modelo devolveu: o texto e, quando o provedor informa, o uso.

    `tokens_prompt`/`tokens_resposta` alimentam a métrica de tempo/custo do TCC
    (seção 14.1); vêm `None` quando o provedor não reporta uso (comum no Ollama).
    """

    texto: str
    modelo: str
    tokens_prompt: int | None = None
    tokens_resposta: int | None = None


@dataclass(frozen=True)
class ConfiguracaoModelo:
    """Para onde chamar e como. Cobre M2 (Ollama) e M3 (nuvem) só mudando campos.

    - `url_base`: a raiz da API compatível com OpenAI, incluindo `/v1`
      (ex.: ``http://localhost:11434/v1`` no Ollama).
    - `modelo`: o nome do modelo no provedor (ex.: ``qwen3:8b``).
    - `chave_api`: o Bearer token; ``None`` para servidores locais sem chave.
    - `timeout_s`: teto de espera por requisição.
    - `max_tentativas`: total de tentativas (1 = sem retry).
    - `espera_base_s`: primeira espera do backoff exponencial (0,5 → 1 → 2 …).
    - `temperatura`: 0,0 por padrão — o relatório tem que ser reprodutível para
      a métrica de fidelidade medir o sistema, não o acaso da amostragem.
    """

    url_base: str
    modelo: str
    chave_api: str | None = None
    timeout_s: float = 60.0
    max_tentativas: int = 3
    espera_base_s: float = 0.5
    temperatura: float = 0.0

    def __post_init__(self) -> None:
        if not self.url_base:
            raise ValueError("url_base é obrigatória.")
        if not self.modelo:
            raise ValueError("modelo é obrigatório.")
        if self.max_tentativas < 1:
            raise ValueError("max_tentativas deve ser ≥ 1.")
        if not 0.0 <= self.temperatura <= 2.0:
            raise ValueError("temperatura deve estar entre 0,0 e 2,0.")

    @property
    def endpoint(self) -> str:
        """URL final do chat/completions, sem ambiguidade de barra."""
        return f"{self.url_base.rstrip('/')}/chat/completions"


class ClienteModelo:
    """Cliente de uma conversa só: recebe mensagens, devolve texto.

    Use como gerenciador de contexto (``with ClienteModelo(cfg) as c:``) para
    fechar a conexão ao final; ou chame ``fechar()`` manualmente.
    """

    def __init__(
        self,
        config: ConfiguracaoModelo,
        *,
        transporte: httpx.BaseTransport | None = None,
        dormir: Callable[[float], None] = sleep,
    ) -> None:
        self.config = config
        self._dormir = dormir
        cabecalhos = {"Content-Type": "application/json"}
        if config.chave_api:
            cabecalhos["Authorization"] = f"Bearer {config.chave_api}"
        self._cliente = httpx.Client(
            timeout=config.timeout_s,
            headers=cabecalhos,
            transport=transporte,
        )

    def completar(
        self,
        mensagens: Sequence[Mensagem],
        *,
        temperatura: float | None = None,
        max_tokens: int | None = None,
    ) -> RespostaModelo:
        """Envia a conversa e devolve a resposta do modelo.

        Levanta `ErroDeConexao` se a requisição não obteve resposta,
        `ErroDeResposta` num status de erro (depois de esgotar os retries, se o
        status for repetível) e `RespostaInvalida` se o corpo veio sem texto.
        """
        payload: dict[str, object] = {
            "model": self.config.modelo,
            "messages": [m.para_openai() for m in mensagens],
            "temperature": (
                temperatura if temperatura is not None else self.config.temperatura
            ),
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        resposta = self._postar_com_retry(payload)
        return self._extrair(resposta)

    def listar_modelos(self) -> list[str]:
        """Nomes dos modelos que o provedor oferece (`GET /models`), em ordem.

        Serve para a tela oferecer uma lista em vez de pedir que o usuário
        adivinhe o nome exato — que muda a cada geração de modelos. É também o
        teste de conexão: uma chave recusada aparece aqui, antes de narrar.
        """
        url = f"{self.config.url_base.rstrip('/')}/models"
        try:
            resposta = self._cliente.get(url)
        except httpx.TimeoutException as exc:
            raise ErroDeConexao(f"Tempo esgotado ao chamar {url}.") from exc
        except httpx.TransportError as exc:
            raise ErroDeConexao(f"Falha de conexão com {url}: {exc}") from exc
        if resposta.status_code >= 400:
            raise ErroDeResposta(
                f"O provedor respondeu {resposta.status_code}: "
                f"{_corpo_resumido(resposta)}",
                status=resposta.status_code,
            )
        try:
            dados = resposta.json()
        except json.JSONDecodeError as exc:
            raise RespostaInvalida("A lista de modelos não é um JSON válido.") from exc
        itens = dados.get("data") if isinstance(dados, dict) else None
        if not isinstance(itens, list):
            raise RespostaInvalida("A resposta não trouxe a lista de modelos (data).")
        # O Gemini devolve "models/gemini-…"; o chat aceita o nome sem o prefixo.
        nomes = {
            str(item["id"]).removeprefix("models/")
            for item in itens
            if isinstance(item, dict) and item.get("id")
        }
        return sorted(nomes)

    def fechar(self) -> None:
        self._cliente.close()

    def __enter__(self) -> ClienteModelo:
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        valor: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.fechar()

    # -- internos -----------------------------------------------------------

    def _postar_com_retry(self, payload: dict[str, object]) -> httpx.Response:
        """Faz o POST, repetindo só falhas transitórias com espera crescente."""
        for tentativa in range(1, self.config.max_tentativas + 1):
            ultima = tentativa == self.config.max_tentativas
            try:
                resposta = self._cliente.post(self.config.endpoint, json=payload)
            except httpx.TimeoutException as exc:
                if ultima:
                    raise ErroDeConexao(
                        f"Tempo esgotado ao chamar {self.config.endpoint}."
                    ) from exc
                self._esperar(tentativa)
                continue
            except httpx.TransportError as exc:
                if ultima:
                    raise ErroDeConexao(
                        f"Falha de conexão com {self.config.endpoint}: {exc}"
                    ) from exc
                self._esperar(tentativa)
                continue

            if resposta.status_code in _STATUS_REPETIVEIS and not ultima:
                self._esperar(tentativa)
                continue
            if resposta.status_code >= 400:
                raise ErroDeResposta(
                    f"O provedor respondeu {resposta.status_code}: "
                    f"{_corpo_resumido(resposta)}",
                    status=resposta.status_code,
                )
            return resposta

        # Inalcançável: o laço ou retorna, ou levanta na última tentativa.
        raise ErroDeConexao("Falha ao obter resposta do modelo.")

    def _esperar(self, tentativa: int) -> None:
        self._dormir(self.config.espera_base_s * (2 ** (tentativa - 1)))

    def _extrair(self, resposta: httpx.Response) -> RespostaModelo:
        try:
            dados = resposta.json()
        except json.JSONDecodeError as exc:
            raise RespostaInvalida("A resposta não é um JSON válido.") from exc

        escolhas = dados.get("choices") if isinstance(dados, dict) else None
        if not escolhas:
            raise RespostaInvalida("A resposta não trouxe nenhuma escolha (choices).")
        conteudo = escolhas[0].get("message", {}).get("content")
        if not isinstance(conteudo, str) or not conteudo.strip():
            raise RespostaInvalida("A resposta veio sem texto utilizável.")

        uso = dados.get("usage") or {}
        return RespostaModelo(
            texto=conteudo,
            modelo=dados.get("model") or self.config.modelo,
            tokens_prompt=uso.get("prompt_tokens"),
            tokens_resposta=uso.get("completion_tokens"),
        )


def _corpo_resumido(resposta: httpx.Response, *, limite: int = 200) -> str:
    """Primeiros caracteres do corpo do erro, para a mensagem da exceção."""
    texto = resposta.text.strip().replace("\n", " ")
    return texto[:limite] + "…" if len(texto) > limite else texto
