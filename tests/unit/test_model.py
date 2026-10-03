"""Testes da matriz de modelo e do ajuste OLS (issue #3, ADRs 0007 e 0008)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from ensaia.core.design import Fator, Planejamento, termos_do_modelo
from ensaia.core.model import RESIDUO, AjusteOLS, ajustar_ols, matriz_modelo
from ensaia.core.table import Table

BETA_VERDADEIRO = {
    "Intercepto": 50.0,
    "x1": 3.0,
    "x2": -2.0,
    "x3": 5.0,
    "x1^2": -4.0,
    "x2^2": 1.5,
    "x3^2": -2.0,
    "x1:x2": 2.5,
    "x1:x3": -1.0,
    "x2:x3": 0.8,
}


def _planejamento(
    nomes: list[str], minimo: float = -1.0, maximo: float = 1.0
) -> Planejamento:
    return Planejamento(
        tipo="composto_central",
        fatores=[Fator(nome=n, minimo=minimo, maximo=maximo) for n in nomes],
        n_pontos_centrais=3,
        alfa_axial=1.68,
    )


def _ccd_3_fatores() -> Table:
    """CCD de 3 fatores já em escala codificada: 8 fatoriais, 6 axiais, 3 centrais."""
    a = 1.68
    fatorial = [(i, j, k) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
    axiais = [(-a, 0, 0), (a, 0, 0), (0, -a, 0), (0, a, 0), (0, 0, -a), (0, 0, a)]
    centrais = [(0, 0, 0)] * 3
    linhas = fatorial + axiais + centrais
    return Table.de_colunas(
        {
            "x1": [r[0] for r in linhas],
            "x2": [r[1] for r in linhas],
            "x3": [r[2] for r in linhas],
        }
    )


def _np(matriz: Table) -> np.ndarray:
    """Matriz de modelo (Table) como array 2D, na ordem dos termos."""
    return np.column_stack([matriz.coluna(t) for t in matriz.colunas])


def _vetor(mapa: dict[str, float], termos: list[str]) -> np.ndarray:
    return np.array([mapa[t] for t in termos])


@pytest.fixture
def ccd_com_resposta() -> tuple[Table, Table, np.ndarray]:
    dados = _ccd_3_fatores()
    termos = list(BETA_VERDADEIRO)
    matriz = matriz_modelo(dados, _planejamento(["x1", "x2", "x3"]), termos)
    ruido = np.random.default_rng(7).normal(0.0, 0.8, len(dados))
    y = _np(matriz) @ np.array(list(BETA_VERDADEIRO.values())) + ruido
    return dados, matriz, y


class TestMatrizModelo:
    def test_colunas_seguem_a_ordem_e_a_notacao_canonica(self) -> None:
        dados = _ccd_3_fatores()
        termos = termos_do_modelo(["x1", "x2", "x3"])
        matriz = matriz_modelo(dados, _planejamento(["x1", "x2", "x3"]), termos)
        assert list(matriz.colunas) == termos
        assert len(matriz) == len(dados)

    def test_intercepto_e_coluna_de_uns(self) -> None:
        matriz = matriz_modelo(
            _ccd_3_fatores(), _planejamento(["x1", "x2", "x3"]), ["Intercepto", "x1"]
        )
        assert (matriz.coluna("Intercepto") == 1.0).all()

    def test_codifica_niveis_reais_e_calcula_quadrado_e_interacao(self) -> None:
        planejamento = Planejamento(
            tipo="fatorial_completo",
            fatores=[Fator("temperatura", 40.0, 80.0), Fator("ph", 3.0, 9.0)],
        )
        dados = Table.de_colunas(
            {"temperatura": [40.0, 80.0, 60.0], "ph": [3.0, 9.0, 9.0]}
        )
        matriz = matriz_modelo(
            dados,
            planejamento,
            ["Intercepto", "temperatura", "ph", "temperatura^2", "temperatura:ph"],
        )
        assert matriz.coluna("temperatura").tolist() == pytest.approx([-1.0, 1.0, 0.0])
        assert matriz.coluna("ph").tolist() == pytest.approx([-1.0, 1.0, 1.0])
        assert matriz.coluna("temperatura^2").tolist() == pytest.approx([1.0, 1.0, 0.0])
        interacao = matriz.coluna("temperatura:ph").tolist()
        assert interacao == pytest.approx([1.0, 1.0, 0.0])

    def test_ponto_axial_fica_alem_de_um_na_escala_codificada(self) -> None:
        planejamento = Planejamento(
            tipo="composto_central", fatores=[Fator("t", 40.0, 80.0)]
        )
        matriz = matriz_modelo(
            Table.de_colunas({"t": [88.0]}), planejamento, ["Intercepto", "t", "t^2"]
        )
        assert matriz.coluna("t")[0] == pytest.approx(1.4)
        assert matriz.coluna("t^2")[0] == pytest.approx(1.96)

    def test_dados_ja_codificados_entram_como_estao(self) -> None:
        planejamento = Planejamento(
            tipo="composto_central", fatores=[Fator("t", 40.0, 80.0)]
        )
        matriz = matriz_modelo(
            Table.de_colunas({"t": [-1.68, 0.0]}), planejamento, ["t"], codificar=False
        )
        assert matriz.coluna("t").tolist() == pytest.approx([-1.68, 0.0])

    def test_fator_ausente_nos_dados_lista_as_colunas_existentes(self) -> None:
        with pytest.raises(ValueError, match=r"\['x3'\] não estão nos dados"):
            matriz_modelo(
                Table.de_colunas({"x1": [-1.0, 1.0], "x2": [-1.0, 1.0]}),
                _planejamento(["x1", "x2", "x3"]),
                ["Intercepto"],
            )

    def test_termo_com_fator_inexistente(self) -> None:
        with pytest.raises(ValueError, match="'z', que não existe"):
            matriz_modelo(
                _ccd_3_fatores(),
                _planejamento(["x1", "x2", "x3"]),
                ["Intercepto", "z^2"],
            )

    def test_termos_repetidos(self) -> None:
        with pytest.raises(ValueError, match="repetidos"):
            matriz_modelo(
                _ccd_3_fatores(), _planejamento(["x1", "x2", "x3"]), ["x1", "x1"]
            )

    def test_nome_de_fator_com_caractere_reservado(self) -> None:
        planejamento = _planejamento(["a:b"])
        with pytest.raises(ValueError, match="reservados"):
            matriz_modelo(
                Table.de_colunas({"a:b": [0.0]}), planejamento, ["Intercepto"]
            )

    def test_valor_ausente_aponta_a_linha(self) -> None:
        dados = Table.de_colunas({"x1": [1.0, np.nan, -1.0]})
        with pytest.raises(ValueError, match=r"linhas \[1\]"):
            matriz_modelo(dados, _planejamento(["x1"]), ["Intercepto", "x1"])


class TestAjusteOLS:
    def test_bate_com_calculo_independente_em_numpy_e_scipy(
        self, ccd_com_resposta: tuple[Table, Table, np.ndarray]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        ajuste = ajustar_ols(matriz, y)

        matriz_v = _np(matriz)
        n, p = matriz_v.shape
        beta, *_ = np.linalg.lstsq(matriz_v, y, rcond=None)
        residuo = y - matriz_v @ beta
        ssr = float(residuo @ residuo)
        sigma2 = ssr / (n - p)
        erro_padrao = np.sqrt(np.diag(sigma2 * np.linalg.inv(matriz_v.T @ matriz_v)))
        valor_t = beta / erro_padrao
        valor_p = 2 * stats.t.sf(np.abs(valor_t), df=n - p)
        sst = float(((y - y.mean()) ** 2).sum())
        t_critico = stats.t.ppf(0.975, df=n - p)
        termos = ajuste.termos

        assert _vetor(ajuste.coeficientes, termos) == pytest.approx(beta, rel=1e-9)
        assert _vetor(ajuste.erros_padrao, termos) == pytest.approx(
            erro_padrao, rel=1e-9
        )
        assert _vetor(ajuste.valores_t, termos) == pytest.approx(valor_t, rel=1e-9)
        assert _vetor(ajuste.valores_p, termos) == pytest.approx(valor_p, rel=1e-9)
        assert ajuste.soma_quadrados_residual == pytest.approx(ssr, rel=1e-9)
        assert ajuste.soma_quadrados_total == pytest.approx(sst, rel=1e-9)
        assert ajuste.r2 == pytest.approx(1 - ssr / sst, rel=1e-9)
        assert ajuste.r2_ajustado == pytest.approx(
            1 - (ssr / (n - p)) / (sst / (n - 1)), rel=1e-9
        )
        assert ajuste.gl_residuo == n - p
        assert ajuste.n_observacoes == n
        assert ajuste.n_parametros == p

        ic = ajuste.intervalo_confianca(0.05)
        inferior = np.array([ic[t][0] for t in termos])
        superior = np.array([ic[t][1] for t in termos])
        assert inferior == pytest.approx(beta - t_critico * erro_padrao, rel=1e-9)
        assert superior == pytest.approx(beta + t_critico * erro_padrao, rel=1e-9)

    def test_coeficientes_saem_com_os_nomes_canonicos(
        self, ccd_com_resposta: tuple[Table, Table, np.ndarray]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        ajuste = ajustar_ols(matriz, y)
        assert list(ajuste.coeficientes.keys()) == list(BETA_VERDADEIRO)
        assert ajuste.termos == list(BETA_VERDADEIRO)

    def test_posto_deficiente_lista_os_termos_redundantes(self) -> None:
        """Fatorial 2² puro não tem curvatura: x1^2 e x2^2 são iguais ao
        intercepto. O ajuste "funcionaria" e devolveria lixo — tem que falhar."""
        dados = Table.de_colunas(
            {"x1": [-1.0, 1.0, -1.0, 1.0], "x2": [-1.0, -1.0, 1.0, 1.0]}
        )
        matriz = matriz_modelo(
            dados, _planejamento(["x1", "x2"]), termos_do_modelo(["x1", "x2"])
        )
        y = np.array([1.0, 2.0, 3.0, 5.0])
        with pytest.raises(ValueError, match="singular") as erro:
            ajustar_ols(matriz, y)
        assert "['x1^2', 'x2^2']" in str(erro.value)

    def test_sem_graus_de_liberdade_residuais_falha_alto(self) -> None:
        dados = Table.de_colunas(
            {"x1": [-1.0, 1.0, -1.0, 1.0], "x2": [-1.0, -1.0, 1.0, 1.0]}
        )
        matriz = matriz_modelo(
            dados,
            _planejamento(["x1", "x2"]),
            termos_do_modelo(["x1", "x2"], incluir_quadraticos=False),
        )
        with pytest.raises(ValueError, match="graus de liberdade"):
            ajustar_ols(matriz, np.array([1.0, 2.0, 3.0, 5.0]))

    def test_exige_intercepto(self) -> None:
        matriz = Table.de_colunas({"x1": [-1.0, 0.0, 1.0, 2.0]})
        with pytest.raises(ValueError, match="intercepto"):
            ajustar_ols(matriz, np.array([1.0, 2.0, 3.0, 4.0]))

    def test_resposta_com_valor_ausente(
        self, ccd_com_resposta: tuple[Table, Table, np.ndarray]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        y = y.copy()
        y[3] = np.nan
        with pytest.raises(ValueError, match="resposta"):
            ajustar_ols(matriz, y)

    def test_x_e_y_desalinhados(
        self, ccd_com_resposta: tuple[Table, Table, np.ndarray]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        with pytest.raises(ValueError, match="alinham"):
            ajustar_ols(matriz, y[:-1])


class TestTabelaTipo2:
    @staticmethod
    def _por_fonte(tabela: list) -> dict:
        return {linha.fonte: linha for linha in tabela}

    def test_usa_nomes_canonicos_e_nao_vaza_nome_do_patsy(
        self, ccd_com_resposta: tuple[Table, Table, np.ndarray]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        tabela = ajustar_ols(matriz, y).tabela_tipo2()
        fontes = {linha.fonte for linha in tabela}
        esperados = [t for t in BETA_VERDADEIRO if t != "Intercepto"]
        assert fontes == set(esperados) | {RESIDUO}
        assert not any("I(" in linha.fonte for linha in tabela)

    def test_linha_de_residuo_bate_com_o_ajuste_canonico(
        self, ccd_com_resposta: tuple[Table, Table, np.ndarray]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        ajuste = ajustar_ols(matriz, y)
        residuo = self._por_fonte(ajuste.tabela_tipo2())[RESIDUO]
        assert residuo.soma_quadrados == pytest.approx(
            ajuste.soma_quadrados_residual, rel=1e-9
        )
        assert residuo.graus_liberdade == ajuste.gl_residuo
        assert residuo.valor_f is None and residuo.valor_p is None

    def test_em_delineamento_simetrico_p_do_tipo_ii_igual_ao_teste_t(
        self, ccd_com_resposta: tuple[Table, Table, np.ndarray]
    ) -> None:
        """Num CCD simétrico os efeitos principais são ortogonais às
        interações: Tipo II, Tipo III e o teste-t do coeficiente coincidem."""
        _, matriz, y = ccd_com_resposta
        ajuste = ajustar_ols(matriz, y)
        for linha in ajuste.tabela_tipo2():
            if linha.fonte == RESIDUO:
                continue
            assert linha.valor_p == pytest.approx(
                ajuste.valores_p[linha.fonte], rel=1e-8
            )

    def test_ordem_das_colunas_nao_muda_o_resultado_por_termo(
        self, ccd_com_resposta: tuple[Table, Table, np.ndarray]
    ) -> None:
        """A tradução casa por nome, não por posição: reordenar os termos da
        matriz não muda o resultado por termo."""
        _, matriz, y = ccd_com_resposta
        nova_ordem = (
            "Intercepto",
            "x1:x2",
            "x3^2",
            "x2",
            "x1",
            "x2:x3",
            "x1^2",
            "x3",
            "x2^2",
            "x1:x3",
        )
        embaralhado = Table(
            colunas=nova_ordem,
            valores={t: matriz.coluna(t) for t in nova_ordem},
        )
        original = self._por_fonte(ajustar_ols(matriz, y).tabela_tipo2())
        outra = self._por_fonte(ajustar_ols(embaralhado, y).tabela_tipo2())
        for termo in original:
            assert outra[termo].soma_quadrados == pytest.approx(
                original[termo].soma_quadrados, rel=1e-9
            )
            assert outra[termo].valor_p == pytest.approx(
                original[termo].valor_p, rel=1e-8, abs=1e-12
            )

    def test_nomes_reais_de_fator_com_espaco_e_acento(self) -> None:
        nomes = ["Tempo (min)", "Razão S/L"]
        a = 1.41
        pontos = [
            (-1, -1),
            (1, -1),
            (-1, 1),
            (1, 1),
            (-a, 0),
            (a, 0),
            (0, -a),
            (0, a),
            (0, 0),
            (0, 0),
            (0, 0),
        ]
        dados = Table.de_colunas(
            {nomes[0]: [p[0] for p in pontos], nomes[1]: [p[1] for p in pontos]}
        )
        termos = termos_do_modelo(nomes)
        matriz = matriz_modelo(dados, _planejamento(nomes), termos)
        y = np.random.default_rng(1).normal(10, 2, len(dados))

        fontes = {linha.fonte for linha in ajustar_ols(matriz, y).tabela_tipo2()}

        assert fontes == {t for t in termos if t != "Intercepto"} | {RESIDUO}
        assert "Tempo (min)^2" in fontes
        assert "Tempo (min):Razão S/L" in fontes

    def test_modelo_nao_hierarquico_ajusta_mas_nao_tem_tipo_ii(
        self, ccd_com_resposta: tuple[Table, Table, np.ndarray]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        sem_x1 = tuple(c for c in matriz.colunas if c != "x1")
        sem_x1_linear = Table(
            colunas=sem_x1, valores={c: matriz.coluna(c) for c in sem_x1}
        )
        ajuste: AjusteOLS = ajustar_ols(sem_x1_linear, y)
        assert "x1^2" in ajuste.coeficientes
        with pytest.raises(ValueError, match="não hierárquico"):
            ajuste.tabela_tipo2()
