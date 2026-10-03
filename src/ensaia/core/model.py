"""Construção da matriz de modelo e ajuste por mínimos quadrados (OLS).

Segundo objetivo específico do pré-projeto: "Apresentar um pipeline
estatístico determinístico que reproduza as etapas fundamentais de uma análise
de DOE, tais como: regressão OLS, ANOVA, cálculo de efeitos e otimização por
função de desejabilidade, utilizando programas em Python."

Este módulo cobre a parte de OLS e a ANOVA Tipo II. O ajuste é feito em numpy
puro (mínimos quadrados + `scipy.stats` para t e F); não há dependência de
statsmodels no cálculo. Pandas entra só como contêiner de dados na fronteira.
Ver docs/decisoes/0007-nucleo-em-numpy-sem-statsmodels.md.

Este módulo NÃO decide quais termos ficam no modelo final — isso é seleção por
significância e vive em `anova.py`, porque depende da tabela de ANOVA.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy import stats

from ensaia.core.design import INTERCEPTO, Planejamento, interpretar_termo
from ensaia.core.table import Table

RESIDUO = "Resíduo"


def matriz_modelo(
    dados: Table,
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

    ausentes = [nome for nome in nomes if not dados.tem(nome)]
    if ausentes:
        raise ValueError(
            f"Fatores {ausentes} não estão nos dados. "
            f"Colunas disponíveis: {list(dados.colunas)}."
        )

    repetidos = sorted({t for t in termos if termos.count(t) > 1})
    if repetidos:
        raise ValueError(f"Termos repetidos na lista de termos: {repetidos}.")

    niveis: dict[str, NDArray[np.float64]] = {}
    for fator in planejamento.fatores:
        valores = dados.coluna(fator.nome)
        if np.isnan(valores).any():
            linhas = [int(i) for i in np.flatnonzero(np.isnan(valores))]
            raise ValueError(
                f"Fator {fator.nome!r} tem valores ausentes ou não numéricos "
                f"nas linhas {linhas} (contagem a partir de 0)."
            )
        niveis[fator.nome] = (
            np.array([fator.codificar(float(v)) for v in valores])
            if codificar
            else valores
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

    return pd.DataFrame(colunas)


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
    """Ajuste OLS em numpy puro, com a ANOVA Tipo II calculada à mão.

    Existe para que o resto do EnsaIA não dependa de detalhes do ajuste: se um
    dia a implementação mudar, muda aqui e em nenhum outro lugar. Toda a
    estatística é computada com `numpy.linalg` (mínimos quadrados) e
    `scipy.stats` (distribuições t e F) — sem statsmodels, sem patsy.

    A matriz entra com os nomes de termo na notação canônica
    ("Intercepto", "x1", "x1^2", "x1:x2") e sai com exatamente esses nomes: a
    validação do §4.3(a) compara coeficientes por nome, então não pode haver
    tradução nenhuma no caminho. Ver ADR 0007 (que sucede a ADR 0005).
    """

    def __init__(self, X: pd.DataFrame, y: pd.Series) -> None:
        _validar_entrada(X, y)
        self._termos: list[str] = [str(coluna) for coluna in X.columns]
        self._indice = X.index
        self._X: NDArray[np.float64] = X.to_numpy(dtype=float)
        self._y: NDArray[np.float64] = y.to_numpy(dtype=float)
        self._n, self._p = self._X.shape
        self._gl_residuo = self._n - self._p

        beta, _, _, _ = np.linalg.lstsq(self._X, self._y, rcond=None)
        self._beta = beta
        self._ajustados = self._X @ beta
        self._residuos = self._y - self._ajustados
        self._ssr = float(self._residuos @ self._residuos)
        self._sigma2 = self._ssr / self._gl_residuo
        centrado = self._y - self._y.mean()
        self._sst = float(centrado @ centrado)

        # Var(β) = σ²·(XᵀX)⁻¹. O posto cheio já foi exigido em _validar_entrada,
        # então a inversa existe; é a mesma fórmula fechada que a literatura usa.
        self._cov_nao_escalada = np.linalg.inv(self._X.T @ self._X)
        self._erros = np.sqrt(np.diag(self._sigma2 * self._cov_nao_escalada))

        self._motivo_sem_tipo2: str | None = None
        self._tipo2: pd.DataFrame | None = None
        self._construir_tipo2()

    @property
    def termos(self) -> list[str]:
        return list(self._termos)

    def _serie(self, valores: NDArray[np.float64]) -> pd.Series:
        return pd.Series(valores, index=self._termos)

    @property
    def coeficientes(self) -> pd.Series:
        return self._serie(self._beta)

    @property
    def erros_padrao(self) -> pd.Series:
        return self._serie(self._erros)

    @property
    def valores_t(self) -> pd.Series:
        return self._serie(self._beta / self._erros)

    @property
    def valores_p(self) -> pd.Series:
        t = self._beta / self._erros
        return self._serie(2.0 * stats.t.sf(np.abs(t), df=self._gl_residuo))

    def intervalo_confianca(self, alfa: float = 0.05) -> pd.DataFrame:
        """IC de (1 − alfa) para cada coeficiente, colunas `inferior`/`superior`."""
        t_critico = float(stats.t.ppf(1.0 - alfa / 2.0, df=self._gl_residuo))
        margem = t_critico * self._erros
        return pd.DataFrame(
            {"inferior": self._beta - margem, "superior": self._beta + margem},
            index=self._termos,
        )

    @property
    def r2(self) -> float:
        return 1.0 - self._ssr / self._sst

    @property
    def r2_ajustado(self) -> float:
        return 1.0 - (self._ssr / self._gl_residuo) / (self._sst / (self._n - 1))

    @property
    def soma_quadrados_residual(self) -> float:
        return self._ssr

    @property
    def soma_quadrados_total(self) -> float:
        return self._sst

    @property
    def gl_residuo(self) -> int:
        return int(self._gl_residuo)

    @property
    def n_observacoes(self) -> int:
        return int(self._n)

    @property
    def n_parametros(self) -> int:
        return int(self._p)

    @property
    def residuos(self) -> pd.Series:
        return pd.Series(self._residuos, index=self._indice)

    @property
    def valores_ajustados(self) -> pd.Series:
        return pd.Series(self._ajustados, index=self._indice)

    def tabela_tipo2(self) -> pd.DataFrame:
        """ANOVA Tipo II, com nomes canônicos e a linha "Resíduo" no fim.

        Colunas: `soma_quadrados`, `graus_liberdade`, `valor_f`, `valor_p`.
        Só existe para modelos hierárquicos (todo fator com termo linear);
        num modelo sem o termo linear de algum fator, a soma de quadrados Tipo
        II perde o sentido e isto falha alto em vez de inventar a tabela.
        """
        if self._tipo2 is None:
            raise ValueError(self._motivo_sem_tipo2)
        return self._tipo2.copy()

    def _rss(self, termos: list[str]) -> float:
        """Soma de quadrados residual de um submodelo só com estes termos."""
        colunas = [self._termos.index(t) for t in termos]
        sub = self._X[:, colunas]
        beta, _, _, _ = np.linalg.lstsq(sub, self._y, rcond=None)
        residuo = self._y - sub @ beta
        return float(residuo @ residuo)

    def _construir_tipo2(self) -> None:
        termos = [t for t in self._termos if t != INTERCEPTO]

        # Hierarquia: um fator que aparece num termo de ordem superior (x^2, x:y)
        # sem o próprio termo linear torna a Tipo II sem sentido. É uma recusa
        # deliberada, não limitação de ferramenta (ADR 0007, herdada da 0005).
        lineares = {
            partes[0][0]
            for partes in (interpretar_termo(t) for t in termos)
            if len(partes) == 1 and partes[0][1] == 1
        }
        usados = {nome for t in termos for nome, _ in interpretar_termo(t)}
        sem_linear = sorted(usados - lineares)
        if sem_linear:
            self._motivo_sem_tipo2 = (
                f"ANOVA Tipo II indisponível: os fatores {sem_linear} aparecem em "
                "termos de ordem superior sem o termo linear correspondente "
                "(modelo não hierárquico)."
            )
            return

        # Tipo II: para cada termo t, SQ(t) = SQ_res(modelo sem t e sem os termos
        # que CONTÊM t) − SQ_res(o mesmo modelo com t de volta). "Conter" usa a
        # mesma noção de fatores atômicos do patsy: x1:x2 contém x1, mas x1^2 NÃO
        # contém x1 (é fator atômico distinto). Reproduz o anova_lm(typ=2) que a
        # ADR 0005 delegava ao statsmodels.
        assinatura = {t: _assinatura_fatores(t) for t in termos}
        linhas: dict[str, tuple[float, int, float, float]] = {}
        for t in termos:
            contem_t = {u for u in termos if u != t and assinatura[t] < assinatura[u]}
            completo = [u for u in self._termos if u not in contem_t]
            reduzido = [u for u in completo if u != t]
            sq = self._rss(reduzido) - self._rss(completo)
            f = (sq / 1) / self._sigma2
            p = float(stats.f.sf(f, 1, self._gl_residuo))
            linhas[t] = (sq, 1, f, p)

        linhas[RESIDUO] = (self._ssr, self._gl_residuo, float("nan"), float("nan"))
        self._tipo2 = pd.DataFrame.from_dict(
            linhas,
            orient="index",
            columns=["soma_quadrados", "graus_liberdade", "valor_f", "valor_p"],
        )


def _assinatura_fatores(termo: str) -> frozenset[str]:
    """Conjunto de fatores atômicos de um termo, para a regra de contenção.

    Reproduz a noção de "fator" do patsy, que é o que a Tipo II usa:
        "x1"     -> {"x1"}
        "x1^2"   -> {"x1^2"}   (átomo próprio — NÃO contém "x1")
        "x1:x2"  -> {"x1", "x2"}

    Assim `{x1} ⊂ {x1, x2}` (x1:x2 contém x1), mas `{x1} ⊄ {x1^2}`.
    """
    partes = interpretar_termo(termo)
    if len(partes) == 1 and partes[0][1] > 1:
        return frozenset({termo})
    return frozenset(nome for nome, _ in partes)


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
