"""Construção da matriz de modelo e ajuste por mínimos quadrados (OLS).

Segundo objetivo específico do pré-projeto: "Apresentar um pipeline
estatístico determinístico que reproduza as etapas fundamentais de uma análise
de DOE, tais como: regressão OLS, ANOVA, cálculo de efeitos e otimização por
função de desejabilidade, utilizando programas em Python."

Este módulo cobre a parte de OLS. Ele NÃO decide quais termos ficam no modelo
final — isso é seleção por significância e vive em `anova.py`, porque depende
da tabela de ANOVA.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from numpy.typing import NDArray
from statsmodels.stats.anova import anova_lm

from lyra.core.design import INTERCEPTO, Planejamento, interpretar_termo

RESIDUO = "Resíduo"

# statsmodels só monta ANOVA Tipo II a partir de um ajuste por fórmula; o
# ajuste "sombra" tem que ser numericamente o mesmo modelo do canônico.
_RTOL_SOMBRA = 1e-6
_ATOL_SOMBRA = 1e-8


def matriz_modelo(
    dados: pd.DataFrame,
    planejamento: Planejamento,
    termos: list[str],
    *,
    codificar: bool = True,
) -> pd.DataFrame:
    """Monta a matriz X do modelo a partir dos termos em notação canônica.

    Trabalhar em variáveis codificadas [-1, +1] não é preciosismo: em unidades
    reais, os termos quadráticos e de interação ficam fortemente
    correlacionados com os lineares, o que infla os erros-padrão e faz
    coeficientes verdadeiros parecerem não significativos. Praticamente toda a
    literatura de DOE reporta coeficientes codificados — e é contra esses
    valores que a validação do §4.3(a) vai comparar.

    Com `codificar=False`, `dados` já está na escala codificada (caso de
    planilhas que trazem a matriz codificada) e os valores entram como estão.

    Cada termo vira uma coluna, na ordem recebida:
        "Intercepto"  -> coluna de 1s
        "x"           -> coluna codificada do fator x
        "x^2"         -> quadrado da coluna codificada
        "x:y"         -> produto das colunas codificadas
    """
    nomes = planejamento.nomes_fatores
    for nome in nomes:
        if ":" in nome or "^" in nome:
            raise ValueError(
                f"Fator {nome!r}: ':' e '^' são reservados da notação de termos "
                "('x1:x2', 'x1^2'). Renomeie o fator."
            )

    ausentes = [nome for nome in nomes if nome not in dados.columns]
    if ausentes:
        raise ValueError(
            f"Fatores {ausentes} não estão nos dados. "
            f"Colunas disponíveis: {list(dados.columns)}."
        )

    repetidos = sorted({t for t in termos if termos.count(t) > 1})
    if repetidos:
        raise ValueError(f"Termos repetidos na lista de termos: {repetidos}.")

    niveis: dict[str, NDArray[np.float64]] = {}
    for fator in planejamento.fatores:
        coluna = pd.to_numeric(dados[fator.nome], errors="coerce")
        if coluna.isna().any():
            linhas = [int(i) for i in np.flatnonzero(coluna.isna().to_numpy())]
            raise ValueError(
                f"Fator {fator.nome!r} tem valores ausentes ou não numéricos "
                f"nas linhas {linhas} (contagem a partir de 0)."
            )
        valores = coluna.astype(float)
        niveis[fator.nome] = (
            valores.map(fator.codificar).to_numpy() if codificar else valores.to_numpy()
        )

    colunas: dict[str, NDArray[np.float64]] = {}
    for termo in termos:
        coluna_termo = np.ones(len(dados))
        for nome, potencia in interpretar_termo(termo):
            if nome not in niveis:
                raise ValueError(
                    f"Termo {termo!r} usa o fator {nome!r}, que não existe no "
                    f"planejamento. Fatores: {nomes}."
                )
            coluna_termo = coluna_termo * niveis[nome] ** potencia
        colunas[termo] = coluna_termo

    return pd.DataFrame(colunas, index=dados.index)


def ajustar_ols(X: pd.DataFrame, y: pd.Series) -> AjusteOLS:
    """Ajusta y = Xβ + ε por mínimos quadrados ordinários.

    Guarda o objeto de resultado inteiro — a ANOVA e o teste de falta de ajuste
    precisam dos resíduos e da matriz de covariância, não só dos coeficientes.

    Antes de ajustar, verifica o posto de X: se X for posto-deficiente, o
    ajuste "funciona" e devolve coeficientes sem sentido. Falhar alto aqui
    com mensagem clara é melhor que produzir um relatório bonito e errado —
    e um relatório bonito e errado é exatamente o risco que este TCC precisa
    demonstrar que sabe evitar.
    """
    return AjusteOLS(X, y)


class AjusteOLS:
    """Envelope fino sobre o resultado do statsmodels.

    Existe para que o resto do LYRA não importe statsmodels diretamente: se um
    dia a implementação mudar, muda aqui e em nenhum outro lugar.

    Por dentro há dois ajustes do mesmo modelo (ADR 0005). O canônico, sobre a
    matriz montada à mão, dá coeficientes, erros e intervalos com os nomes de
    termo exatos que a validação usa. O "sombra", por fórmula, só existe porque
    `anova_lm(typ=2)` do statsmodels exige um modelo ajustado por fórmula. Fora
    deste módulo ninguém enxerga o segundo: a tabela sai com nomes canônicos.

    A consistência entre os dois é checada a cada construção, não só em teste:
    SSR, R² e cada coeficiente (pelo nome traduzido) têm que bater, e o
    conjunto de nomes traduzidos tem que ser exatamente o conjunto de termos.
    """

    def __init__(self, X: pd.DataFrame, y: pd.Series) -> None:
        _validar_entrada(X, y)
        self._X = X.astype(float)
        self._y = y.astype(float)
        self._resultado: Any = sm.OLS(self._y, self._X).fit()

        self._motivo_sem_tipo2: str | None = None
        self._tipo2: pd.DataFrame | None = None
        self._construir_tipo2()

    @property
    def termos(self) -> list[str]:
        return [str(t) for t in self._X.columns]

    @property
    def coeficientes(self) -> pd.Series:
        return pd.Series(self._resultado.params)

    @property
    def erros_padrao(self) -> pd.Series:
        return pd.Series(self._resultado.bse)

    @property
    def valores_t(self) -> pd.Series:
        return pd.Series(self._resultado.tvalues)

    @property
    def valores_p(self) -> pd.Series:
        return pd.Series(self._resultado.pvalues)

    def intervalo_confianca(self, alfa: float = 0.05) -> pd.DataFrame:
        """IC de (1 − alfa) para cada coeficiente, colunas `inferior`/`superior`."""
        intervalo = pd.DataFrame(self._resultado.conf_int(alpha=alfa))
        intervalo.columns = ["inferior", "superior"]
        return intervalo

    @property
    def r2(self) -> float:
        return float(self._resultado.rsquared)

    @property
    def r2_ajustado(self) -> float:
        return float(self._resultado.rsquared_adj)

    @property
    def soma_quadrados_residual(self) -> float:
        return float(self._resultado.ssr)

    @property
    def soma_quadrados_total(self) -> float:
        return float(self._resultado.centered_tss)

    @property
    def gl_residuo(self) -> int:
        return int(self._resultado.df_resid)

    @property
    def n_observacoes(self) -> int:
        return int(self._resultado.nobs)

    @property
    def n_parametros(self) -> int:
        return int(self._X.shape[1])

    @property
    def residuos(self) -> pd.Series:
        return pd.Series(self._resultado.resid)

    @property
    def valores_ajustados(self) -> pd.Series:
        return pd.Series(self._resultado.fittedvalues)

    def tabela_tipo2(self) -> pd.DataFrame:
        """ANOVA Tipo II, com nomes canônicos e a linha "Resíduo" no fim.

        Colunas: `soma_quadrados`, `graus_liberdade`, `valor_f`, `valor_p`.
        Só existe para modelos hierárquicos (todo fator com termo linear);
        num modelo sem o termo linear de algum fator, a fórmula sombra não
        consegue ser montada e isto falha alto em vez de inventar a tabela.
        """
        if self._tipo2 is None:
            raise ValueError(self._motivo_sem_tipo2)
        return self._tipo2.copy()

    def _construir_tipo2(self) -> None:
        termos = [t for t in self.termos if t != INTERCEPTO]
        lineares = [
            partes[0][0]
            for partes in (interpretar_termo(t) for t in termos)
            if len(partes) == 1 and partes[0][1] == 1
        ]
        usados = {nome for t in termos for nome, _ in interpretar_termo(t)}
        sem_linear = sorted(usados - set(lineares))
        if sem_linear:
            self._motivo_sem_tipo2 = (
                f"ANOVA Tipo II indisponível: os fatores {sem_linear} aparecem em "
                "termos de ordem superior sem o termo linear correspondente "
                "(modelo não hierárquico)."
            )
            return

        aliases = {nome: f"f{i}" for i, nome in enumerate(lineares)}
        dados_sombra = pd.DataFrame(
            {aliases[nome]: self._X[nome].to_numpy() for nome in lineares}
        )
        dados_sombra["y"] = self._y.to_numpy()

        traducao = {t: _termo_patsy(t, aliases) for t in termos}
        mapa = {_chave(patsy): termo for termo, patsy in traducao.items()}
        if len(mapa) != len(termos):
            raise ValueError(
                "Há termos que, escritos em outra ordem de fatores, são o mesmo "
                "termo (ex.: 'x1:x2' e 'x2:x1')."
            )

        formula = "y ~ " + (" + ".join(traducao.values()) if termos else "1")
        sombra = smf.ols(formula, data=dados_sombra).fit()

        self._checar_sombra(sombra, mapa, termos)

        tabela = anova_lm(sombra, typ=2)
        novos = []
        for nome in tabela.index:
            if nome == "Residual":
                novos.append(RESIDUO)
                continue
            canonico = mapa.get(_chave(str(nome)))
            if canonico is None:
                raise RuntimeError(
                    f"A tabela ANOVA trouxe o termo {nome!r}, que não corresponde a "
                    "nenhum termo do modelo. Ver ADR 0005."
                )
            novos.append(canonico)
        tabela.index = novos
        if set(novos) != set(termos) | {RESIDUO}:
            raise RuntimeError(
                "Os nomes traduzidos da tabela ANOVA não coincidem com os termos "
                f"do modelo: faltam {sorted((set(termos) | {RESIDUO}) - set(novos))}. "
                "Ver ADR 0005."
            )
        self._tipo2 = tabela.rename(
            columns={
                "sum_sq": "soma_quadrados",
                "df": "graus_liberdade",
                "F": "valor_f",
                "PR(>F)": "valor_p",
            }
        )

    def _checar_sombra(
        self, sombra: Any, mapa: dict[str, str], termos: list[str]
    ) -> None:
        canonico = self._resultado
        ssr_igual = np.isclose(
            canonico.ssr, sombra.ssr, rtol=_RTOL_SOMBRA, atol=_ATOL_SOMBRA
        )
        r2_igual = np.isclose(
            canonico.rsquared, sombra.rsquared, rtol=_RTOL_SOMBRA, atol=_ATOL_SOMBRA
        )
        if not (ssr_igual and r2_igual):
            raise RuntimeError(
                "O ajuste por fórmula (usado só para a ANOVA Tipo II) divergiu do "
                f"ajuste canônico: SSR {sombra.ssr!r} contra {canonico.ssr!r}. "
                "Ver ADR 0005."
            )

        coef_sombra = sombra.params
        traduzidos: dict[str, float] = {INTERCEPTO: float(coef_sombra["Intercept"])}
        for nome, valor in coef_sombra.items():
            if nome == "Intercept":
                continue
            termo = mapa.get(_chave(str(nome)))
            if termo is None:
                raise RuntimeError(
                    f"O ajuste por fórmula trouxe o coeficiente {nome!r}, que não "
                    "corresponde a nenhum termo do modelo. Ver ADR 0005."
                )
            traduzidos[termo] = float(valor)

        esperados = {INTERCEPTO, *termos}
        if set(traduzidos) != esperados:
            raise RuntimeError(
                "Os coeficientes do ajuste por fórmula não cobrem exatamente os "
                f"termos do modelo: faltam {sorted(esperados - set(traduzidos))}. "
                "Ver ADR 0005."
            )
        for termo, valor in traduzidos.items():
            if not np.isclose(
                valor,
                canonico.params[termo],
                rtol=_RTOL_SOMBRA,
                atol=_ATOL_SOMBRA,
            ):
                raise RuntimeError(
                    f"O coeficiente de {termo!r} difere entre o ajuste canônico "
                    f"({canonico.params[termo]!r}) e o por fórmula ({valor!r}): a "
                    "tradução de nomes trocou termos. Ver ADR 0005."
                )


def _termo_patsy(termo: str, aliases: dict[str, str]) -> str:
    """Termo canônico → sintaxe patsy, com fatores trocados por aliases seguros.

    Nomes reais de fator ('Tempo (min)', 'Razão S/L') não são identificadores
    válidos numa fórmula; os aliases f0, f1, ... são.
    """
    partes = []
    for nome, potencia in interpretar_termo(termo):
        alias = aliases[nome]
        partes.append(alias if potencia == 1 else f"I({alias}**{potencia})")
    return ":".join(partes)


def _chave(nome_patsy: str) -> str:
    """Forma normalizada de um nome patsy, para casar com a tradução.

    O patsy devolve `I(f0**2)` como `I(f0 ** 2)` (com espaços) e não garante a
    ordem dos fatores dentro de uma interação — daí tirar espaços e ordenar.
    """
    limpo = nome_patsy.replace(" ", "")
    return ":".join(sorted(limpo.split(":")))


def _validar_entrada(X: pd.DataFrame, y: pd.Series) -> None:
    if len(X) != len(y):
        raise ValueError(
            f"X tem {len(X)} linhas e y tem {len(y)}: os ensaios não se alinham."
        )
    if not X.index.equals(y.index):
        raise ValueError("X e y têm índices diferentes: os ensaios não se alinham.")
    if INTERCEPTO not in X.columns:
        raise ValueError(
            f"A matriz do modelo precisa da coluna {INTERCEPTO!r}: sem intercepto, "
            "R² e ANOVA mudam de definição e deixam de ser comparáveis com a "
            "literatura."
        )
    if X.columns.duplicated().any():
        repetidas = sorted(X.columns[X.columns.duplicated()].unique())
        raise ValueError(f"Colunas repetidas na matriz do modelo: {repetidas}.")

    valores = X.to_numpy(dtype=float)
    resposta = y.to_numpy(dtype=float)
    if not np.isfinite(valores).all():
        raise ValueError("A matriz do modelo tem valores ausentes ou infinitos.")
    if not np.isfinite(resposta).all():
        raise ValueError("A resposta tem valores ausentes ou infinitos.")

    n_termos = X.shape[1]
    posto = int(np.linalg.matrix_rank(valores))
    if posto < n_termos:
        raise ValueError(
            f"A matriz do modelo é singular: posto {posto} para {n_termos} termos. "
            f"Termos que não acrescentam informação (combinação linear dos "
            f"anteriores): {_termos_redundantes(X)}. Causas comuns: termo "
            "quadrático num fatorial 2^k sem pontos centrais ou axiais, ou menos "
            "ensaios do que termos no modelo."
        )
    if len(X) - n_termos < 1:
        raise ValueError(
            f"{len(X)} ensaios para {n_termos} termos não deixam graus de "
            "liberdade para o resíduo: sem ele não há erro-padrão nem p-valor. "
            "Reduza o modelo ou acrescente ensaios."
        )


def _termos_redundantes(X: pd.DataFrame) -> list[str]:
    redundantes: list[str] = []
    posto_atual = 0
    for j in range(X.shape[1]):
        posto = int(np.linalg.matrix_rank(X.iloc[:, : j + 1].to_numpy(dtype=float)))
        if posto == posto_atual:
            redundantes.append(str(X.columns[j]))
        else:
            posto_atual = posto
    return redundantes
