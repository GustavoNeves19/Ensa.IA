"""Contrato de saída do núcleo determinístico.

Este módulo define `AnalysisResult` e seus tipos auxiliares. Ele é a
**fronteira arquitetural** do LYRA: tudo que o núcleo estatístico calcula sai
por aqui, e tudo que a camada de LLM narra entra por aqui.

Por que isso importa (e por que estes tipos são congelados):

A hipótese de trabalho do TCC é que um pipeline determinístico acoplado a uma
camada de LLM produz resultados *estatisticamente equivalentes* aos de
softwares pagos. Essa afirmação só se sustenta se o LLM não puder alterar
número nenhum. `AnalysisResult` é `frozen`, serializável e auto-contido
justamente para que a camada narrativa receba os resultados como dado morto,
sem meio de recalcular ou "corrigir" nada.

Ver docs/decisoes/0001-fronteira-deterministica-llm.md.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# Versão do esquema de serialização. Incrementar sempre que a forma de
# AnalysisResult mudar de modo incompatível — os arquivos de resultado
# guardados em resultados/ e os valores de referência dos casos de estudo
# dependem disso para continuarem legíveis.
SCHEMA_VERSION = "1.0"

TipoPlanejamento = Literal[
    "fatorial_completo",
    "fatorial_fracionado",
    "composto_central",
    "box_behnken",
    "desconhecido",
]

Sentido = Literal["maximizar", "minimizar", "alvo"]


@dataclass(frozen=True)
class Coeficiente:
    """Um termo do modelo de regressão ajustado.

    `termo` usa notação canônica para que a comparação com valores publicados
    seja possível sem heurística de string: "Intercepto", "x1", "x1^2",
    "x1:x2". A ordem dos fatores numa interação é sempre crescente.
    """

    termo: str
    estimativa: float
    erro_padrao: float
    valor_t: float
    valor_p: float
    significativo: bool
    ic_inferior: float | None = None
    ic_superior: float | None = None


@dataclass(frozen=True)
class LinhaAnova:
    """Uma linha da tabela de ANOVA."""

    fonte: str
    soma_quadrados: float
    graus_liberdade: int
    quadrado_medio: float
    valor_f: float | None = None
    valor_p: float | None = None


@dataclass(frozen=True)
class FaltaDeAjuste:
    """Teste de falta de ajuste (lack-of-fit).

    Só é calculável quando o planejamento tem repetições genuínas — em geral
    os pontos centrais. Quando não há, `aplicavel` é False e o resto é None:
    isso é informação, não falha, e a camada narrativa precisa saber a
    diferença entre "não houve falta de ajuste" e "não deu para testar".
    """

    aplicavel: bool
    soma_quadrados_falta: float | None = None
    soma_quadrados_erro_puro: float | None = None
    graus_liberdade_falta: int | None = None
    graus_liberdade_erro_puro: int | None = None
    valor_f: float | None = None
    valor_p: float | None = None
    significativa: bool | None = None
    motivo_inaplicavel: str | None = None


@dataclass(frozen=True)
class PontoOtimo:
    """Condição ótima encontrada pela função de desejabilidade."""

    coordenadas: dict[str, float]
    resposta_prevista: dict[str, float]
    desejabilidade_global: float
    desejabilidades_individuais: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class AjusteResposta:
    """Resultado completo do ajuste para UMA variável resposta."""

    resposta: str
    coeficientes: list[Coeficiente]
    anova: list[LinhaAnova]
    r2: float
    r2_ajustado: float
    falta_de_ajuste: FaltaDeAjuste
    n_observacoes: int
    graus_liberdade_residuo: int
    termos_incluidos: list[str]
    termos_descartados: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MetadadosExecucao:
    """Tudo que é preciso para reproduzir esta análise.

    Sem isto, um resultado guardado em resultados/ é um número órfão. Com
    isto, qualquer pessoa da banca consegue refazer a mesma execução.
    """

    versao_lyra: str
    schema_version: str = SCHEMA_VERSION
    alfa: float = 0.05
    semente: int | None = None
    tempo_execucao_s: float | None = None
    # Preenchido pelo chamador, não por relógio interno, para que o resultado
    # continue reprodutível byte a byte em teste.
    executado_em: str | None = None


@dataclass(frozen=True)
class AnalysisResult:
    """Saída completa e auto-contida do pipeline determinístico.

    A camada de LLM recebe **este objeto e nada mais**. Se algum dado for
    necessário para escrever o relatório e não estiver aqui, o lugar de
    corrigir é o núcleo — nunca dar acesso extra ao LLM.
    """

    tipo_planejamento: TipoPlanejamento
    fatores: list[str]
    respostas: list[str]
    ajustes: list[AjusteResposta]
    metadados: MetadadosExecucao
    ponto_otimo: PontoOtimo | None = None
    avisos: list[str] = field(default_factory=list)

    def ajuste(self, resposta: str) -> AjusteResposta:
        """Recupera o ajuste de uma resposta pelo nome."""
        for a in self.ajustes:
            if a.resposta == resposta:
                return a
        raise KeyError(
            f"Resposta {resposta!r} não está neste resultado. "
            f"Disponíveis: {[a.resposta for a in self.ajustes]}"
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
