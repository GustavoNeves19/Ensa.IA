"""Contrato de saída do núcleo determinístico.

Este módulo define `AnalysisResult` e seus tipos auxiliares. Ele é a
**fronteira arquitetural** do EnsaIA: tudo que o núcleo estatístico calcula sai
por aqui, e tudo que a camada de LLM narra entra por aqui.

Por que isso importa (e por que estes tipos são congelados):

A hipótese de trabalho do TCC é que um pipeline determinístico acoplado a uma
camada de LLM produz resultados *estatisticamente equivalentes* aos de
softwares pagos. Essa afirmação só se sustenta se o LLM não puder alterar
número nenhum. `AnalysisResult` é `frozen`, serializável e auto-contido
justamente para que a camada narrativa receba os resultados como dado morto,
sem meio de recalcular ou "corrigir" nada.

São modelos Pydantic v2 (spec, seção 10): além de congelados, validam os tipos
na construção, então um JSON malformado vindo de uma ferramenta MCP ou de um
arquivo de resultado é rejeitado com erro claro, não propagado silenciosamente.

Ver docs/decisoes/0001-fronteira-deterministica-llm.md.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Versão do esquema de serialização. Incrementar a parte maior sempre que a
# forma de AnalysisResult mudar de modo incompatível — os arquivos de resultado
# guardados em resultados/ e os valores de referência dos casos de estudo
# dependem disso para continuarem legíveis. A parte menor sobe quando só se
# acrescentam campos opcionais (1.1: t crítico e diagnóstico por ensaio; 1.2:
# informações do planejamento; 1.3: ANOVA da regressão, R² de predição,
# equação e opções do modelo; 1.4: ponto estacionário e ótimo em unidades
# reais; 1.5: efeitos de fatorial, pontos influentes e estatística
# descritiva; 1.6: análises marcadas); um JSON 1.0 continua sendo lido.
SCHEMA_VERSION = "1.6"

TipoPlanejamento = Literal[
    "fatorial_completo",
    "fatorial_fracionado",
    "composto_central",
    "box_behnken",
    "fatorial_3k",
    "desconhecido",
]

# Nome de cada tipo em português corrido, para frases, PDF e tela (fonte única).
NOME_PLANEJAMENTO: dict[str, str] = {
    "fatorial_completo": "fatorial completo",
    "fatorial_fracionado": "fatorial fracionado",
    "composto_central": "delineamento composto central",
    "box_behnken": "delineamento Box-Behnken",
    "fatorial_3k": "fatorial completo de 3 níveis (3^k)",
    "desconhecido": "delineamento não identificado",
}

Sentido = Literal["maximizar", "minimizar", "alvo"]

# Opções do modelo (spec §4, passo 4, "opções avançadas").
TipoModelo = Literal["linear", "interacoes", "quadratico"]
# Termo de erro dos testes t e F: o resíduo (tipo Minitab) ou o erro puro das
# réplicas (comum no Statistica e em artigos brasileiros). Essencial para
# comparar com um Artigo Alvo: usar o mesmo termo que o artigo usou.
TermoErro = Literal["residuo", "erro_puro"]


class _Congelado(BaseModel):
    """Base dos modelos do contrato: imutáveis após a construção."""

    model_config = ConfigDict(frozen=True)


class Coeficiente(_Congelado):
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


class LinhaAnova(_Congelado):
    """Uma linha da tabela de ANOVA."""

    fonte: str
    soma_quadrados: float
    graus_liberdade: int
    quadrado_medio: float
    valor_f: float | None = None
    valor_p: float | None = None


class FaltaDeAjuste(_Congelado):
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


class PontoOtimo(_Congelado):
    """Condição ótima (spec §9, E4 e E5).

    `coordenadas` estão em **unidades reais** — é como o artigo publica a
    condição ótima e como o usuário vai ajustar o equipamento;
    `coordenadas_codificadas` são as mesmas na escala do modelo. `metas` diz o
    que se pediu de cada resposta (maximizar, minimizar, alvo) e `metodo`
    distingue a otimização direta de uma resposta da desejabilidade.
    """

    coordenadas: dict[str, float]
    resposta_prevista: dict[str, float]
    desejabilidade_global: float
    desejabilidades_individuais: dict[str, float] = Field(default_factory=dict)
    coordenadas_codificadas: dict[str, float] = Field(default_factory=dict)
    metas: dict[str, str] = Field(default_factory=dict)
    metodo: str = "desejabilidade"
    limite_codificado: float = 1.0


class PontoEstacionario(_Congelado):
    """Ponto estacionário do modelo quadrático e sua natureza (spec §9, E3).

    `x_s = −½·B⁻¹·b`. Os autovalores de B dizem a forma da superfície ali:
    todos negativos → máximo; todos positivos → mínimo; sinais mistos → sela
    (nem máximo nem mínimo). `dentro_da_regiao` avisa quando o ponto cai fora
    da região experimental — o modelo não deve ser extrapolado até lá.
    """

    codificado: dict[str, float]
    real: dict[str, float]
    natureza: Literal["maximo", "minimo", "sela"]
    autovalores: list[float]
    resposta_prevista: float
    dentro_da_regiao: bool


class AnovaRegressao(_Congelado):
    """ANOVA da regressão como a literatura de DOE apresenta (spec §9, C2).

    Linhas: Regressão, Resíduo, Falta de ajuste e Erro puro (quando há réplicas)
    e Total. `f_tabelado` é o F crítico da regressão no nível α e `razao_f` é
    F calculado / F tabelado — o critério de Barros Neto et al. e Rodrigues e
    Iemma, muito usado em artigos brasileiros (razão > 1: regressão
    significativa).
    """

    linhas: list[LinhaAnova]
    f_tabelado: float | None = None
    razao_f: float | None = None
    regressao_significativa: bool | None = None


class Equacao(_Congelado):
    """Equação do modelo ajustado (spec §9, C5), já formatada em pt-BR.

    `codificada` usa X1, X2… (ver `variaveis`) e é a escala em que os artigos
    publicam os coeficientes. `real` é a mesma superfície reescrita nas unidades
    dos fatores, para prever direto com os valores do laboratório.
    `significativos` é a codificada só com os termos significativos (sem
    reajuste). `coeficientes_reais` traz os números da forma real por termo.
    """

    codificada: str
    real: str
    significativos: str
    variaveis: dict[str, str]
    coeficientes_reais: dict[str, float]


class Diagnostico(_Congelado):
    """Valores por ensaio e normalidade dos resíduos (spec §9: C6, D1, D2).

    As três listas estão na ordem das linhas da planilha, para que "ensaio 7"
    signifique a mesma coisa na tela, no PDF e no JSON. É daqui que saem os
    gráficos de preditos × observados, resíduos × preditos e Q-Q: a interface
    só desenha estes números, não os recalcula.

    `shapiro_w`/`shapiro_p` ficam None quando o teste não se aplica (menos de 3
    ensaios ou resíduos todos iguais, como num ajuste exato) — o motivo vai em
    `motivo_sem_shapiro`, para a interface dizer "não deu para testar" em vez
    de inventar normalidade. `normalidade_rejeitada` é a decisão no nível α
    (p < α), tomada aqui pelo mesmo motivo que `Coeficiente.significativo`: quem
    decide é o núcleo, a tela só mostra.
    """

    observados: list[float]
    preditos: list[float]
    residuos: list[float]
    shapiro_w: float | None = None
    shapiro_p: float | None = None
    normalidade_rejeitada: bool | None = None
    motivo_sem_shapiro: str | None = None
    # D3: ordem de execução de cada ensaio, quando a planilha a informa.
    ordem: list[float] | None = None
    # D4: alavancagem hᵢᵢ, resíduo studentizado (interno) e distância de Cook.
    # None num ensaio com hᵢᵢ = 1 (o modelo passa obrigatoriamente por ele).
    alavancagem: list[float] = Field(default_factory=list)
    residuos_studentizados: list[float | None] = Field(default_factory=list)
    distancia_cook: list[float | None] = Field(default_factory=list)
    # Ensaios (contando de 1) influentes (Cook > 1 e hᵢᵢ > 2p/n) e possíveis
    # outliers (|R-student| > 3). Regras em core/diagnostico.py.
    ensaios_influentes: list[int] = Field(default_factory=list)
    possiveis_outliers: list[int] = Field(default_factory=list)


class Efeito(_Congelado):
    """Efeito de um termo num fatorial de 2 níveis (spec §9, B1).

    Efeito = 2 × coeficiente codificado: a variação média da resposta quando o
    fator vai do nível −1 ao +1 (o coeficiente mede só do centro ao +1). O t e
    o p são os mesmos do coeficiente.
    """

    termo: str
    efeito: float
    erro_padrao: float
    valor_t: float
    valor_p: float
    significativo: bool
    ativo_lenth: bool | None = None


class AnaliseLenth(_Congelado):
    """Método de Lenth (1989) para fatoriais sem réplicas (spec §9, B3).

    PSE é o pseudo erro-padrão estimado dos próprios efeitos; ME e SME são as
    margens de erro individual e simultânea. Efeito com |e| > ME é ativo.
    """

    pse: float
    me: float
    sme: float
    graus_liberdade: float


class TesteCurvatura(_Congelado):
    """Curvatura no fatorial com pontos centrais (spec §9, B5).

    Compara a média dos vértices com a dos pontos centrais. Curvatura
    significativa diz que o modelo linear não basta e que vale ampliar o
    planejamento (por exemplo, para um composto central).
    """

    aplicavel: bool
    media_fatorial: float | None = None
    media_central: float | None = None
    soma_quadrados: float | None = None
    valor_f: float | None = None
    valor_p: float | None = None
    significativa: bool | None = None
    motivo_inaplicavel: str | None = None


class MediasNivel(_Congelado):
    """Médias da resposta em cada nível de um fator (gráfico de efeito, B4)."""

    fator: str
    niveis: list[float]
    medias: list[float]


class MediasInteracao(_Congelado):
    """Médias em cada combinação de níveis de dois fatores (gráfico de interação).

    `medias[j][i]` é a média com `fator_b` no nível `niveis_b[j]` e `fator_a`
    no nível `niveis_a[i]`.
    """

    fator_a: str
    fator_b: str
    niveis_a: list[float]
    niveis_b: list[float]
    medias: list[list[float]]


class EfeitosFatorial(_Congelado):
    """Tudo o que o grupo B da spec entrega para um fatorial de 2 níveis."""

    efeitos: list[Efeito]
    lenth: AnaliseLenth | None = None
    curvatura: TesteCurvatura
    medias_principais: list[MediasNivel] = Field(default_factory=list)
    medias_interacoes: list[MediasInteracao] = Field(default_factory=list)


class EstatisticaDescritiva(_Congelado):
    """Resumo de uma resposta (spec §9, A1)."""

    resposta: str
    n: int
    media: float
    desvio_padrao: float
    minimo: float
    maximo: float
    cv_percentual: float | None = None


class AjusteResposta(_Congelado):
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
    termos_descartados: list[str] = Field(default_factory=list)
    # Limiar de |t| no nível α (bilateral): a linha de corte do Pareto (spec B2).
    # None quando não sobra grau de liberdade para o resíduo.
    t_critico: float | None = None
    diagnostico: Diagnostico | None = None
    anova_regressao: AnovaRegressao | None = None
    r2_predicao: float | None = None
    equacao: Equacao | None = None
    # Termo de erro efetivamente usado nos testes desta resposta (o pedido pode
    # cair para o resíduo quando não há réplicas para o erro puro).
    termo_erro: TermoErro = "residuo"
    ponto_estacionario: PontoEstacionario | None = None
    efeitos_fatorial: EfeitosFatorial | None = None


class FatorCodificado(_Congelado):
    """Como um fator foi codificado: `x_cod = (x_real − centro) / passo`."""

    nome: str
    centro: float
    passo: float
    unidade: str = ""


class InfoPlanejamento(_Congelado):
    """A geometria do experimento (spec §10, seção `design`).

    `alfa_axial` só existe no composto central (distância codificada dos pontos
    axiais). `avisos` traz o que a identificação estranhou — níveis axiais
    assimétricos, α fora do rotacional, fração irregular.
    """

    k: int
    n_ensaios: int
    n_pontos_centrais: int
    alfa_axial: float | None = None
    fatores: list[FatorCodificado]
    avisos: list[str] = Field(default_factory=list)


class MetadadosExecucao(_Congelado):
    """Tudo que é preciso para reproduzir esta análise.

    Sem isto, um resultado guardado em resultados/ é um número órfão. Com
    isto, qualquer pessoa da banca consegue refazer a mesma execução.
    """

    versao_ensaia: str
    schema_version: str = SCHEMA_VERSION
    alfa: float = 0.05
    tipo_modelo: TipoModelo | None = None
    termo_erro: TermoErro = "residuo"
    reducao_backward: bool = False
    # Análises marcadas pelo usuário (IDs da spec §9, A1…E5). A tela, o PDF e
    # o texto mostram só estas (RF-07, RF-11); o núcleo calcula o que é barato.
    analises: list[str] = Field(default_factory=list)
    semente: int | None = None
    tempo_execucao_s: float | None = None
    # Preenchido pelo chamador, não por relógio interno, para que o resultado
    # continue reprodutível byte a byte em teste.
    executado_em: str | None = None


class AnalysisResult(_Congelado):
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
    avisos: list[str] = Field(default_factory=list)
    planejamento: InfoPlanejamento | None = None
    descritiva: list[EstatisticaDescritiva] = Field(default_factory=list)

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
        return self.model_dump()

    def to_json(self, *, indent: int = 2) -> str:
        # Via json.dumps(model_dump()) de propósito: mantém o mesmo formato
        # (indentação, ordem de campos, repr de float) dos resultados já
        # versionados, para o diff de evidência não mudar sem a conta mudar.
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
