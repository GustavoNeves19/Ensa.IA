"""Cliente HTTP para modelos de linguagem compatíveis com OpenAI.
Único ponto que fala com a IA: tempo limite, novas tentativas e erros tipados.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import sleep
from types import TracebackType

import httpx

# Papéis da conversa no protocolo da OpenAI (ficam em inglês).
Papel = str

# Status HTTP que vale repetir: 429 e falhas do servidor.
_STATUS_REPETIVEIS = frozenset({429, 500, 502, 503, 504})


class ErroDeIA(Exception):
    """Base das falhas da camada de IA."""


class ErroDeConexao(ErroDeIA):
    """A requisição não recebeu resposta (rede, DNS, tempo limite)."""


class ErroDeResposta(ErroDeIA):
    """O provedor respondeu com status de erro."""

    def __init__(self, mensagem: str, *, status: int) -> None:
        """Guarda a mensagem e o status HTTP."""
        super().__init__(mensagem)
        self.status = status


class RespostaInvalida(ErroDeIA):
    """Resposta com sucesso, mas sem texto utilizável."""


@dataclass(frozen=True)
class Mensagem:
    """Uma fala da conversa enviada ao modelo."""

    papel: Papel
    conteudo: str

    @classmethod
    def sistema(cls, conteudo: str) -> Mensagem:
        """Mensagem de instrução (system)."""
        return cls("system", conteudo)

    @classmethod
    def usuario(cls, conteudo: str) -> Mensagem:
        """Mensagem do usuário (o pedido)."""
        return cls("user", conteudo)

    @classmethod
    def assistente(cls, conteudo: str) -> Mensagem:
        """Resposta de exemplo do assistente (few-shot)."""
        return cls("assistant", conteudo)

    def para_openai(self) -> dict[str, str]:
        """Mensagem no formato da API da OpenAI."""
        return {"role": self.papel, "content": self.conteudo}


@dataclass(frozen=True)
class RespostaModelo:
    """Texto devolvido pelo modelo e o uso de tokens, se informado."""

    texto: str
    modelo: str
    tokens_prompt: int | None = None
    tokens_resposta: int | None = None


@dataclass(frozen=True)
class ConfiguracaoModelo:
    """Para onde e como chamar o modelo (URL, modelo, chave, tentativas)."""

    url_base: str
    modelo: str
    chave_api: str | None = None
    # Espera máxima pela resposta; tempo esgotado não é repetido.
    timeout_s: float = 30.0
    timeout_conexao_s: float = 5.0
    max_tentativas: int = 3
    espera_base_s: float = 0.5
    temperatura: float = 0.0

    def __post_init__(self) -> None:
        """Valida URL, modelo e parâmetros de tentativa."""
        if not self.url_base:
            raise ValueError("url_base é obrigatória.")
        if not self.modelo:
            raise ValueError("modelo é obrigatório.")
        if self.max_tentativas < 1:
            raise ValueError("max_tentativas deve ser ≥ 1.")
        if self.timeout_s <= 0 or self.timeout_conexao_s <= 0:
            raise ValueError("Os tempos limite devem ser positivos.")
        if not 0.0 <= self.temperatura <= 2.0:
            raise ValueError("temperatura deve estar entre 0,0 e 2,0.")

    @property
    def endpoint(self) -> str:
        """URL final de /chat/completions."""
        return f"{self.url_base.rstrip('/')}/chat/completions"


class ClienteModelo:
    """Cliente de conversa: envia mensagens e devolve o texto."""

    def __init__(
        self,
        config: ConfiguracaoModelo,
        *,
        transporte: httpx.BaseTransport | None = None,
        dormir: Callable[[float], None] = sleep,
    ) -> None:
        """Cria o cliente HTTP com cabeçalhos e tempo limite."""
        self.config = config
        self._dormir = dormir
        cabecalhos = {"Content-Type": "application/json"}
        if config.chave_api:
            cabecalhos["Authorization"] = f"Bearer {config.chave_api}"
        self._cliente = httpx.Client(
            timeout=httpx.Timeout(config.timeout_s, connect=config.timeout_conexao_s),
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
        """Envia a conversa e devolve a resposta do modelo."""
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
        """Nomes dos modelos que o provedor oferece."""
        url = f"{self.config.url_base.rstrip('/')}/models"
        try:
            resposta = self._cliente.get(url)
        except httpx.TimeoutException as exc:
            raise ErroDeConexao(self._msg_tempo_esgotado(url)) from exc
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
        """Fecha a conexão HTTP."""
        self._cliente.close()

    def __enter__(self) -> ClienteModelo:
        """Abre o cliente num bloco with."""
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        valor: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Fecha o cliente ao sair do bloco with."""
        self.fechar()

    # -- internos -----------------------------------------------------------

    def _postar_com_retry(self, payload: dict[str, object]) -> httpx.Response:
        """Faz o POST, repetindo só falhas passageiras."""
        for tentativa in range(1, self.config.max_tentativas + 1):
            ultima = tentativa == self.config.max_tentativas
            try:
                resposta = self._cliente.post(self.config.endpoint, json=payload)
            except httpx.TimeoutException as exc:
                # Modelo lento não fica mais rápido na segunda vez: falha já.
                raise ErroDeConexao(
                    self._msg_tempo_esgotado(self.config.endpoint)
                ) from exc
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

    def _msg_tempo_esgotado(self, url: str) -> str:
        """Mensagem de tempo esgotado com o limite usado."""
        return (
            f"O modelo não respondeu em {self.config.timeout_s:g} s "
            f"(tempo esgotado ao chamar {url})."
        )

    def _esperar(self, tentativa: int) -> None:
        """Espera antes da próxima tentativa (crescente)."""
        self._dormir(self.config.espera_base_s * (2 ** (tentativa - 1)))

    def _extrair(self, resposta: httpx.Response) -> RespostaModelo:
        """Extrai o texto e o uso de tokens da resposta."""
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
    """Início do corpo da resposta de erro, para a mensagem."""
    texto = resposta.text.strip().replace("\n", " ")
    return texto[:limite] + "…" if len(texto) > limite else texto
