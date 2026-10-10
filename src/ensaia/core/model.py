"""Construção da matriz de modelo e ajuste por mínimos quadrados (OLS).

Segundo objetivo específico do pré-projeto: "Apresentar um pipeline
estatístico determinístico que reproduza as etapas fundamentais de uma análise
de DOE, tais como: regressão OLS, ANOVA, cálculo de efeitos e otimização por
função de desejabilidade, utilizando programas em Python."

Tudo aqui é numpy puro: a matriz de modelo é uma `Table`, o ajuste usa
`numpy.linalg`, e as distribuições t e F vêm do `scipy.stats`. Não há pandas nem
statsmodels no núcleo. Ver ADR 0007 (numpy, sem statsmodels) e 0008 (Table, sem
pandas).

Este módulo NÃO decide quais termos ficam no modelo final — isso é seleção por
significância e vive em `anova.py`, porque depende da tabela de ANOVA.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from ensaia.core.design import INTERCEPTO, Planejamento, interpretar_termo
from ensaia.core.results import LinhaAnova
from ensaia.core.table import Table

RESIDUO = "Resíduo"


def matriz_modelo(
    dados: Table,
    planejamento: Planejamento,
    termos: list[str],
    *,
    codificar: bool = True,
) -> Table:
    """Monta a matriz X do modelo a partir dos termos em notação canônica.

    Trabalhar em variáveis codificadas [-1, +1] não é preciosismo: em unidades
    reais, os termos quadráticos e de interação ficam fortemente
    correlacionados com os lineares, o que infla os erros-padrão e faz
    coeficientes verdadeiros parecerem não significativos. Praticamente toda a
    literatura de DOE reporta coeficientes codificados — e é contra esses
    valores que a validação do §4.3(a) vai comparar.

    Com `codificar=False`, `dados` já está na escala codificada (caso de
    planilhas que trazem a matriz codificada) e os valores entram como estão.

    Devolve uma `Table` com uma coluna por termo, na ordem recebida:
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

    colunas: dict[str, NDArray[np.float64] | tuple[str, ...]] = {}
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

    return Table(colunas=tuple(termos), valores=colunas)


def ajustar_ols(X: Table, y: NDArray[np.float64]) -> AjusteOLS:
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

    Entra uma `Table` (matriz de modelo, uma coluna por termo em notação
    canônica) e um vetor-resposta numpy; saem coeficientes, erros, ANOVA e
    diagnósticos como `dict`/`numpy`, sem pandas. Os nomes de termo saem
    exatamente como entraram — a validação do §4.3(a) compara por nome, então
    não pode haver tradução no caminho. Ver ADR 0007 e 0008.
    """

    def __init__(self, X: Table, y: NDArray[np.float64]) -> None:
        self._y: NDArray[np.float64] = np.asarray(y, dtype=float)
        self._termos: list[str] = list(X.colunas)
        _validar_entrada(X, self._y)
        self._X: NDArray[np.float64] = np.column_stack(
            [X.coluna(t) for t in self._termos]
        )
        self._n, self._p = self._X.shape
        self._gl_residuo = self._n - self._p

        beta, _, _, _ = np.linalg.lstsq(self._X, self._y, rcond=None)
        self._beta: NDArray[np.float64] = beta
        self._ajustados: NDArray[np.float64] = self._X @ beta
        self._residuos: NDArray[np.float64] = self._y - self._ajustados
        self._ssr = float(self._residuos @ self._residuos)
        self._sigma2 = self._ssr / self._gl_residuo
        centrado = self._y - self._y.mean()
        self._sst = float(centrado @ centrado)

        # Var(β) = σ²·(XᵀX)⁻¹. O posto cheio já foi exigido em _validar_entrada,
        # então a inversa existe; é a mesma fórmula fechada que a literatura usa.
        self._cov_nao_escalada = np.linalg.inv(self._X.T @ self._X)
        self._erros = np.sqrt(np.diag(self._sigma2 * self._cov_nao_escalada))

        self._motivo_sem_tipo2: str | None = None
        self._sq_tipo2: list[tuple[str, float]] | None = None
        self._construir_tipo2()

    @property
    def termos(self) -> list[str]:
        return list(self._termos)

    def _mapa(self, valores: NDArray[np.float64]) -> dict[str, float]:
        return {t: float(v) for t, v in zip(self._termos, valores, strict=True)}

    @property
    def coeficientes(self) -> dict[str, float]:
        return self._mapa(self._beta)

    @property
    def erros_padrao(self) -> dict[str, float]:
        return self._mapa(self._erros)

    @property
    def valores_t(self) -> dict[str, float]:
        return self._mapa(self._beta / self._erros)

    @property
    def valores_p(self) -> dict[str, float]:
        t = self._beta / self._erros
        return self._mapa(2.0 * stats.t.sf(np.abs(t), df=self._gl_residuo))

    def _erro(
        self, qm_erro: float | None, gl_erro: int | None
    ) -> tuple[NDArray[np.float64], int]:
        """Erros-padrão e gl para o termo de erro escolhido (resíduo por padrão)."""
        if qm_erro is None or gl_erro is None:
            return self._erros, self._gl_residuo
        return np.sqrt(np.diag(qm_erro * self._cov_nao_escalada)), gl_erro

    def estatisticas_t(
        self, qm_erro: float | None = None, gl_erro: int | None = None
    ) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
        """(erros-padrão, t, p) de cada coeficiente com o termo de erro dado.

        Sem argumentos usa o quadrado médio do resíduo (comportamento tipo
        Minitab). Com `qm_erro`/`gl_erro` do erro puro, reproduz a opção comum no
        Statistica e em artigos brasileiros (spec §9, grupo C). A estimativa dos
        coeficientes não muda; mudam o erro-padrão, o t e o p.
        """
        erros, gl = self._erro(qm_erro, gl_erro)
        t = self._beta / erros
        p = 2.0 * stats.t.sf(np.abs(t), df=gl)
        return self._mapa(erros), self._mapa(t), self._mapa(p)

    def intervalo_confianca(
        self,
        alfa: float = 0.05,
        qm_erro: float | None = None,
        gl_erro: int | None = None,
    ) -> dict[str, tuple[float, float]]:
        """IC de (1 − alfa) por coeficiente: termo -> (inferior, superior)."""
        erros, gl = self._erro(qm_erro, gl_erro)
        t_critico = float(stats.t.ppf(1.0 - alfa / 2.0, df=gl))
        margem = t_critico * erros
        inferior = self._beta - margem
        superior = self._beta + margem
        return {
            t: (float(inferior[i]), float(superior[i]))
            for i, t in enumerate(self._termos)
        }

    @property
    def alavancagem(self) -> NDArray[np.float64]:
        """hᵢᵢ: diagonal da matriz chapéu X(XᵀX)⁻¹Xᵀ (o peso de cada ensaio)."""
        h: NDArray[np.float64] = np.einsum(
            "ij,jk,ik->i", self._X, self._cov_nao_escalada, self._X
        )
        return h

    @property
    def r2_predicao(self) -> float | None:
        """R² de predição: 1 − PRESS / SQ_total (spec §9, C3).

        PRESS soma o erro de prever cada ensaio com o modelo ajustado SEM ele,
        `(eᵢ / (1 − hᵢᵢ))²`. Mede o poder de prever pontos novos, que um R² alto
        com termos demais não garante. Quando algum ensaio tem hᵢᵢ = 1 (o modelo
        passa obrigatoriamente por ele), a previsão sem ele não existe e o valor
        fica indefinido (None).
        """
        folga = 1.0 - self.alavancagem
        if np.any(folga < 1e-10):
            return None
        press = float(np.sum((self._residuos / folga) ** 2))
        return 1.0 - press / self._sst

    @property
    def r2(self) -> float:
        return 1.0 - self._ssr / self._sst

    @property
    def r2_ajustado(self) -> float:
        return float(1.0 - (self._ssr / self._gl_residuo) / (self._sst / (self._n - 1)))

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
    def residuos(self) -> NDArray[np.float64]:
        return self._residuos

    @property
    def valores_ajustados(self) -> NDArray[np.float64]:
        return self._ajustados

    def tabela_tipo2(
        self, qm_erro: float | None = None, gl_erro: int | None = None
    ) -> list[LinhaAnova]:
        """ANOVA Tipo II como lista de `LinhaAnova`, com a linha "Resíduo" no fim.

        O F de cada termo divide a soma de quadrados dele pelo quadrado médio do
        termo de erro: o do resíduo por padrão, ou o do erro puro quando
        `qm_erro`/`gl_erro` são dados (a linha "Resíduo" continua a mesma).

        Só existe para modelos hierárquicos (todo fator com termo linear); num
        modelo sem o termo linear de algum fator, a soma de quadrados Tipo II
        perde o sentido e isto falha alto em vez de inventar a tabela.
        """
        if self._sq_tipo2 is None:
            raise ValueError(self._motivo_sem_tipo2)
        qm = self._sigma2 if qm_erro is None else qm_erro
        gl = self._gl_residuo if gl_erro is None else gl_erro
        linhas = [
            LinhaAnova(
                fonte=t,
                soma_quadrados=sq,
                graus_liberdade=1,
                quadrado_medio=sq,
                valor_f=sq / qm,
                valor_p=float(stats.f.sf(sq / qm, 1, gl)),
            )
            for t, sq in self._sq_tipo2
        ]
        linhas.append(
            LinhaAnova(
                fonte=RESIDUO,
                soma_quadrados=self._ssr,
                graus_liberdade=self._gl_residuo,
                quadrado_medio=self._ssr / self._gl_residuo,
            )
        )
        return linhas

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
        # contém x1 (é fator atômico distinto). Reproduz o anova_lm(typ=2).
        assinatura = {t: _assinatura_fatores(t) for t in termos}
        somas: list[tuple[str, float]] = []
        for t in termos:
            contem_t = {u for u in termos if u != t and assinatura[t] < assinatura[u]}
            completo = [u for u in self._termos if u not in contem_t]
            reduzido = [u for u in completo if u != t]
            somas.append((t, self._rss(reduzido) - self._rss(completo)))
        self._sq_tipo2 = somas


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


def _validar_entrada(X: Table, y: NDArray[np.float64]) -> None:
    if len(X) != len(y):
        raise ValueError(
            f"X tem {len(X)} linhas e y tem {len(y)}: os ensaios não se alinham."
        )
    termos = list(X.colunas)
    if INTERCEPTO not in termos:
        raise ValueError(
            f"A matriz do modelo precisa da coluna {INTERCEPTO!r}: sem intercepto, "
            "R² e ANOVA mudam de definição e deixam de ser comparáveis com a "
            "literatura."
        )
    if len(set(termos)) != len(termos):
        repetidas = sorted({t for t in termos if termos.count(t) > 1})
        raise ValueError(f"Colunas repetidas na matriz do modelo: {repetidas}.")

    valores = np.column_stack([X.coluna(t) for t in termos])
    if not np.isfinite(valores).all():
        raise ValueError("A matriz do modelo tem valores ausentes ou infinitos.")
    if not np.isfinite(y).all():
        raise ValueError("A resposta tem valores ausentes ou infinitos.")

    n_termos = len(termos)
    posto = int(np.linalg.matrix_rank(valores))
    if posto < n_termos:
        raise ValueError(
            f"A matriz do modelo é singular: posto {posto} para {n_termos} termos. "
            f"Termos que não acrescentam informação (combinação linear dos "
            f"anteriores): {termos_redundantes(X)}. Causas comuns: termo "
            "quadrático num fatorial 2^k sem pontos centrais ou axiais, ou menos "
            "ensaios do que termos no modelo."
        )
    if len(X) - n_termos < 1:
        raise ValueError(
            f"{len(X)} ensaios para {n_termos} termos não deixam graus de "
            "liberdade para o resíduo: sem ele não há erro-padrão nem p-valor. "
            "Reduza o modelo ou acrescente ensaios."
        )


def termos_redundantes(X: Table) -> list[str]:
    """Colunas da matriz que são combinação linear das anteriores (na ordem)."""
    redundantes: list[str] = []
    posto_atual = 0
    acumulado: list[NDArray[np.float64]] = []
    for nome in X.colunas:
        acumulado.append(X.coluna(nome))
        posto = int(np.linalg.matrix_rank(np.column_stack(acumulado)))
        if posto == posto_atual:
            redundantes.append(nome)
        else:
            posto_atual = posto
    return redundantes
