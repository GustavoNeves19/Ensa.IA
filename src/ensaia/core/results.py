"""Contrato de saída do núcleo (AnalysisResult), em Pydantic congelado.
Tela, PDF, IA e MCP só leem este objeto; ninguém recalcula nada.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Versão do esquema: a maior sobe com mudança incompatível; a menor, com campo novo.
SCHEMA_VERSION = "1.7"

# Só o DCCR é reconhecido (ADR 0013); o resto volta como desconhecido.
TipoPlanejamento = Literal[
    "composto_central",
    "desconhecido",
]

# Nome de cada tipo em português corrido, para frases, PDF e tela (fonte única).
NOME_PLANEJAMENTO: dict[str, str] = {
    "composto_central": "delineamento composto central rotacional (DCCR)",
    "desconhecido": "delineamento não identificado",
}

Sentido = Literal["maximizar", "minimizar", "alvo"]

# Opções do modelo (spec §4, passo 4, "opções avançadas").
TipoModelo = Literal["linear", "interacoes", "quadratico"]
# Termo de erro dos testes t e F: resíduo ou erro puro.
TermoErro = Literal["residuo", "erro_puro"]


class _Congelado(BaseModel):
    """Base dos modelos do contrato: imutáveis após a construção."""

    model_config = ConfigDict(frozen=True)


class Coeficiente(_Congelado):
    """Um termo do modelo: estimativa, erro, t, p e intervalo."""

    termo: str
    estimativa: float
    erro_padrao: float
    valor_t: float
    valor_p: float
    significativo: bool
    ic_inferior: float | None = None
    ic_superior: float | None = None


class LinhaAnova(_Congelado):
    """Uma linha da tabela de ANOVA."""

    fonte: str
    soma_quadrados: float
    graus_liberdade: int
    quadrado_medio: float
    valor_f: float | None = None
    valor_p: float | None = None


class FaltaDeAjuste(_Congelado):
    """Resultado do teste de falta de ajuste (ou por que não se aplica)."""

    aplicavel: bool
    soma_quadrados_falta: float | None = None
    soma_quadrados_erro_puro: float | None = None
    graus_liberdade_falta: int | None = None
    graus_liberdade_erro_puro: int | None = None
    valor_f: float | None = None
    valor_p: float | None = None
    significativa: bool | None = None
    motivo_inaplicavel: str | None = None


class PontoOtimo(_Congelado):
    """Condição ótima, previsões e desejabilidade."""

    coordenadas: dict[str, float]
    resposta_prevista: dict[str, float]
    desejabilidade_global: float
    desejabilidades_individuais: dict[str, float] = Field(default_factory=dict)
    coordenadas_codificadas: dict[str, float] = Field(default_factory=dict)
    metas: dict[str, str] = Field(default_factory=dict)
    metodo: str = "desejabilidade"
    limite_codificado: float = 1.0


class PontoEstacionario(_Congelado):
    """Ponto estacionário do modelo quadrático e sua natureza."""

    codificado: dict[str, float]
    real: dict[str, float]
    natureza: Literal["maximo", "minimo", "sela"]
    autovalores: list[float]
    resposta_prevista: float
    dentro_da_regiao: bool


class AnovaRegressao(_Congelado):
    """ANOVA da regressão no formato da literatura, com F tabelado."""

    linhas: list[LinhaAnova]
    f_tabelado: float | None = None
    razao_f: float | None = None
    regressao_significativa: bool | None = None
    util_para_previsao: bool | None = None


class Equacao(_Congelado):
    """Equação do modelo, codificada e em unidades reais."""

    codificada: str
    real: str
    significativos: str
    variaveis: dict[str, str]
    coeficientes_reais: dict[str, float]


class Diagnostico(_Congelado):
    """Resíduos por ensaio, normalidade e influência."""

    observados: list[float]
    preditos: list[float]
    residuos: list[float]
    shapiro_w: float | None = None
    shapiro_p: float | None = None
    normalidade_rejeitada: bool | None = None
    motivo_sem_shapiro: str | None = None
    # D3: ordem de execução de cada ensaio, quando a planilha a informa.
    ordem: list[float] | None = None
    # D4: alavancagem, resíduo studentizado e distância de Cook.
    alavancagem: list[float] = Field(default_factory=list)
    residuos_studentizados: list[float | None] = Field(default_factory=list)
    distancia_cook: list[float | None] = Field(default_factory=list)
    # Ensaios influentes e possíveis outliers (contando de 1).
    ensaios_influentes: list[int] = Field(default_factory=list)
    possiveis_outliers: list[int] = Field(default_factory=list)


class Efeito(_Congelado):
    """Efeito de um termo num fatorial de 2 níveis."""

    termo: str
    efeito: float
    erro_padrao: float
    valor_t: float
    valor_p: float
    significativo: bool
    ativo_lenth: bool | None = None


class AnaliseLenth(_Congelado):
    """Resultado do método de Lenth para fatoriais sem réplicas."""

    pse: float
    me: float
    sme: float
    graus_liberdade: float


class TesteCurvatura(_Congelado):
    """Teste de curvatura de um fatorial com pontos centrais."""

    aplicavel: bool
    media_fatorial: float | None = None
    media_central: float | None = None
    soma_quadrados: float | None = None
    valor_f: float | None = None
    valor_p: float | None = None
    significativa: bool | None = None
    motivo_inaplicavel: str | None = None


class MediasNivel(_Congelado):
    """Média da resposta em cada nível de um fator."""

    fator: str
    niveis: list[float]
    medias: list[float]


class MediasInteracao(_Congelado):
    """Médias em cada combinação de níveis de dois fatores."""

    fator_a: str
    fator_b: str
    niveis_a: list[float]
    niveis_b: list[float]
    medias: list[list[float]]


class EfeitosFatorial(_Congelado):
    """Resultados do grupo B para um fatorial de 2 níveis."""

    efeitos: list[Efeito]
    lenth: AnaliseLenth | None = None
    curvatura: TesteCurvatura
    medias_principais: list[MediasNivel] = Field(default_factory=list)
    medias_interacoes: list[MediasInteracao] = Field(default_factory=list)


class EstatisticaDescritiva(_Congelado):
    """Resumo de uma resposta (A1)."""

    resposta: str
    n: int
    media: float
    desvio_padrao: float
    minimo: float
    maximo: float
    cv_percentual: float | None = None


class AjusteResposta(_Congelado):
    """Resultado completo do ajuste de uma resposta."""

    resposta: str
    coeficientes: list[Coeficiente]
    anova: list[LinhaAnova]
    r2: float
    r2_ajustado: float
    falta_de_ajuste: FaltaDeAjuste
    n_observacoes: int
    graus_liberdade_residuo: int
    termos_incluidos: list[str]
    termos_descartados: list[str] = Field(default_factory=list)
    # Limiar de |t| no nível α; None sem g.l. no resíduo.
    t_critico: float | None = None
    diagnostico: Diagnostico | None = None
    anova_regressao: AnovaRegressao | None = None
    r2_predicao: float | None = None
    # R² máximo: (SQ total − SQ erro puro) / SQ total; None sem réplicas.
    r2_maximo: float | None = None
    equacao: Equacao | None = None
    # Termo de erro efetivamente usado nesta resposta.
    termo_erro: TermoErro = "residuo"
    ponto_estacionario: PontoEstacionario | None = None
    efeitos_fatorial: EfeitosFatorial | None = None
    # Com blocos: o efeito de cada bloco (soma zero).
    efeitos_bloco: dict[str, float] = Field(default_factory=dict)


class FatorCodificado(_Congelado):
    """Como um fator foi codificado (centro e passo)."""

    nome: str
    centro: float
    passo: float
    unidade: str = ""


class InfoPlanejamento(_Congelado):
    """Geometria do experimento: tipo, fatores, α, centros e avisos."""

    k: int
    n_ensaios: int
    n_pontos_centrais: int
    alfa_axial: float | None = None
    fatores: list[FatorCodificado]
    avisos: list[str] = Field(default_factory=list)
    # Coluna de bloco e quantos blocos há (None sem blocos).
    coluna_bloco: str | None = None
    n_blocos: int | None = None


class MetadadosExecucao(_Congelado):
    """Tudo o que é preciso para reproduzir a análise."""

    versao_ensaia: str
    schema_version: str = SCHEMA_VERSION
    alfa: float = 0.05
    tipo_modelo: TipoModelo | None = None
    termo_erro: TermoErro = "residuo"
    reducao_backward: bool = False
    # Análises marcadas pelo usuário (IDs A1…E5).
    analises: list[str] = Field(default_factory=list)
    semente: int | None = None
    tempo_execucao_s: float | None = None
    # Preenchido por quem chama, para o resultado ser reprodutível.
    executado_em: str | None = None


class AnalysisResult(_Congelado):
    """Saída completa e autocontida do núcleo."""

    tipo_planejamento: TipoPlanejamento
    fatores: list[str]
    respostas: list[str]
    ajustes: list[AjusteResposta]
    metadados: MetadadosExecucao
    ponto_otimo: PontoOtimo | None = None
    avisos: list[str] = Field(default_factory=list)
    planejamento: InfoPlanejamento | None = None
    descritiva: list[EstatisticaDescritiva] = Field(default_factory=list)

    def ajuste(self, resposta: str) -> AjusteResposta:
        """Busca o ajuste de uma resposta pelo nome."""
        for a in self.ajustes:
            if a.resposta == resposta:
                return a
        raise KeyError(
            f"Resposta {resposta!r} não está neste resultado. "
            f"Disponíveis: {[a.resposta for a in self.ajustes]}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Resultado como dicionário."""
        return self.model_dump()

    def to_json(self, *, indent: int = 2) -> str:
        # Mesmo formato dos resultados já versionados.
        """Resultado como JSON, no formato dos arquivos versionados."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
