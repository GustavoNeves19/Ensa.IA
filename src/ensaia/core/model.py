"""Matriz do modelo e ajuste por mínimos quadrados (OLS), em numpy puro.
Inclui erros-padrão, testes t, R², PRESS e ANOVA Tipo II.
"""

from __future__ import annotations

from collections.abc import Sequence

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
    """Monta a matriz X do modelo a partir dos termos."""
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


def ajustar_ols(
    X: Table, y: NDArray[np.float64], *, fixos: Sequence[str] = ()
) -> AjusteOLS:
    """Ajusta o modelo por mínimos quadrados e devolve o AjusteOLS."""
    return AjusteOLS(X, y, fixos=fixos)


class AjusteOLS:
    """Ajuste OLS com coeficientes, erros, ANOVA Tipo II e diagnósticos."""

    def __init__(
        self, X: Table, y: NDArray[np.float64], *, fixos: Sequence[str] = ()
    ) -> None:
        """Valida a entrada e calcula coeficientes, resíduos e erros."""
        self._y: NDArray[np.float64] = np.asarray(y, dtype=float)
        self._termos: list[str] = list(X.colunas)
        desconhecidos = sorted(set(fixos) - set(self._termos))
        if desconhecidos:
            raise ValueError(f"Colunas fixas ausentes da matriz: {desconhecidos}.")
        self._fixos: list[str] = [t for t in self._termos if t in set(fixos)]
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

        # Var(β) = σ²·(XᵀX)⁻¹; o posto cheio já foi conferido.
        self._cov_nao_escalada = np.linalg.inv(self._X.T @ self._X)
        self._erros = np.sqrt(np.diag(self._sigma2 * self._cov_nao_escalada))

        self._motivo_sem_tipo2: str | None = None
        self._sq_tipo2: list[tuple[str, float]] | None = None
        self._construir_tipo2()

    @property
    def termos(self) -> list[str]:
        """Todas as colunas da matriz, inclusive as de bloco."""
        return list(self._termos)

    @property
    def termos_modelo(self) -> list[str]:
        """Termos do estudo, sem as colunas de bloco."""
        return [t for t in self._termos if t not in self._fixos]

    @property
    def termos_fixos(self) -> list[str]:
        """Colunas fixas (blocos), na ordem da matriz."""
        return list(self._fixos)

    def _mapa(self, valores: NDArray[np.float64]) -> dict[str, float]:
        """Associa cada termo ao valor correspondente."""
        return {t: float(v) for t, v in zip(self._termos, valores, strict=True)}

    @property
    def coeficientes(self) -> dict[str, float]:
        """Coeficientes estimados por termo."""
        return self._mapa(self._beta)

    @property
    def erros_padrao(self) -> dict[str, float]:
        """Erros-padrão dos coeficientes (resíduo)."""
        return self._mapa(self._erros)

    @property
    def valores_t(self) -> dict[str, float]:
        """Estatística t de cada coeficiente (resíduo)."""
        return self._mapa(self._beta / self._erros)

    @property
    def valores_p(self) -> dict[str, float]:
        """p-valor de cada coeficiente (resíduo)."""
        t = self._beta / self._erros
        return self._mapa(2.0 * stats.t.sf(np.abs(t), df=self._gl_residuo))

    def _erro(
        self, qm_erro: float | None, gl_erro: int | None
    ) -> tuple[NDArray[np.float64], int]:
        """Erros-padrão e g.l. para o termo de erro escolhido."""
        if qm_erro is None or gl_erro is None:
            return self._erros, self._gl_residuo
        return np.sqrt(np.diag(qm_erro * self._cov_nao_escalada)), gl_erro

    def estatisticas_t(
        self, qm_erro: float | None = None, gl_erro: int | None = None
    ) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
        """Erros, t e p com o resíduo ou com o erro puro."""
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
        """Intervalo de confiança de cada coeficiente."""
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
        """Alavancagem hᵢᵢ de cada ensaio (diagonal da matriz chapéu)."""
        h: NDArray[np.float64] = np.einsum(
            "ij,jk,ik->i", self._X, self._cov_nao_escalada, self._X
        )
        return h

    @property
    def r2_predicao(self) -> float | None:
        """R² de predição: 1 − PRESS / SQ total."""
        folga = 1.0 - self.alavancagem
        if np.any(folga < 1e-10):
            return None
        press = float(np.sum((self._residuos / folga) ** 2))
        return 1.0 - press / self._sst

    def soma_quadrados_residual_de(self, termos: Sequence[str]) -> float:
        """SQ residual de um submodelo com estes termos."""
        return self._rss(list(termos))

    @property
    def r2(self) -> float:
        """Coeficiente de determinação R²."""
        return 1.0 - self._ssr / self._sst

    @property
    def r2_ajustado(self) -> float:
        """R² ajustado pelo número de termos."""
        return float(1.0 - (self._ssr / self._gl_residuo) / (self._sst / (self._n - 1)))

    @property
    def soma_quadrados_residual(self) -> float:
        """Soma de quadrados do resíduo."""
        return self._ssr

    @property
    def soma_quadrados_total(self) -> float:
        """Soma de quadrados total."""
        return self._sst

    @property
    def gl_residuo(self) -> int:
        """Graus de liberdade do resíduo."""
        return int(self._gl_residuo)

    @property
    def n_observacoes(self) -> int:
        """Número de ensaios."""
        return int(self._n)

    @property
    def n_parametros(self) -> int:
        """Número de parâmetros do modelo."""
        return int(self._p)

    @property
    def residuos(self) -> NDArray[np.float64]:
        """Resíduos (observado − previsto)."""
        return self._residuos

    @property
    def valores_ajustados(self) -> NDArray[np.float64]:
        """Valores previstos pelo modelo."""
        return self._ajustados

    def tabela_tipo2(
        self, qm_erro: float | None = None, gl_erro: int | None = None
    ) -> list[LinhaAnova]:
        """ANOVA Tipo II por termo, com a linha do resíduo no fim."""
        if self._sq_tipo2 is None:
            raise ValueError(self._motivo_sem_tipo2)
        qm = self._sigma2 if qm_erro is None else qm_erro
        gl = self._gl_residuo if gl_erro is None else gl_erro
        linhas = [self._linha_tipo2(t, sq, qm, gl) for t, sq in self._sq_tipo2]
        linhas.append(
            LinhaAnova(
                fonte=RESIDUO,
                soma_quadrados=self._ssr,
                graus_liberdade=self._gl_residuo,
                quadrado_medio=self._ssr / self._gl_residuo,
            )
        )
        return linhas

    def _linha_tipo2(self, termo: str, sq: float, qm: float, gl: int) -> LinhaAnova:
        """Uma linha da ANOVA Tipo II (sem F quando o erro é nulo)."""
        if qm <= 0.0:
            explica = sq > 1e-12 * max(self._sst, 1.0)
            return LinhaAnova(
                fonte=termo,
                soma_quadrados=sq,
                graus_liberdade=1,
                quadrado_medio=sq,
                valor_f=None,
                valor_p=0.0 if explica else 1.0,
            )
        f = sq / qm
        return LinhaAnova(
            fonte=termo,
            soma_quadrados=sq,
            graus_liberdade=1,
            quadrado_medio=sq,
            valor_f=f,
            valor_p=float(stats.f.sf(f, 1, gl)),
        )

    def _rss(self, termos: list[str]) -> float:
        """SQ residual de um submodelo, com cache."""
        colunas = [self._termos.index(t) for t in termos]
        sub = self._X[:, colunas]
        beta, _, _, _ = np.linalg.lstsq(sub, self._y, rcond=None)
        residuo = self._y - sub @ beta
        return float(residuo @ residuo)

    def _construir_tipo2(self) -> None:
        # As colunas fixas (blocos) ficam em todos os submodelos e fora da tabela.
        """Calcula a SQ Tipo II de cada termo (regra de contenção)."""
        termos = [t for t in self._termos if t != INTERCEPTO and t not in self._fixos]

        # Hierarquia: termo superior sem o linear torna a Tipo II sem sentido.
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

        # Tipo II: SQ do termo descontados os termos que não o contêm.
        assinatura = {t: _assinatura_fatores(t) for t in termos}
        somas: list[tuple[str, float]] = []
        for t in termos:
            contem_t = {u for u in termos if u != t and assinatura[t] < assinatura[u]}
            completo = [u for u in self._termos if u not in contem_t]
            reduzido = [u for u in completo if u != t]
            somas.append((t, self._rss(reduzido) - self._rss(completo)))
        self._sq_tipo2 = somas


def _assinatura_fatores(termo: str) -> frozenset[str]:
    """Fatores atômicos de um termo, para a regra de contenção."""
    partes = interpretar_termo(termo)
    if len(partes) == 1 and partes[0][1] > 1:
        return frozenset({termo})
    return frozenset(nome for nome, _ in partes)


def _validar_entrada(X: Table, y: NDArray[np.float64]) -> None:
    """Confere tamanhos, intercepto, valores e posto da matriz."""
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
    """Colunas que são combinação linear das anteriores."""
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
