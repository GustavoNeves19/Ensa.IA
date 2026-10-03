"""Testes da matriz de modelo e do ajuste OLS (issue #3, ADR 0005)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from ensaia.core.design import Fator, Planejamento, termos_do_modelo
from ensaia.core.model import RESIDUO, AjusteOLS, ajustar_ols, matriz_modelo

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


def _ccd_3_fatores() -> pd.DataFrame:
    """CCD de 3 fatores já em escala codificada: 8 fatoriais, 6 axiais, 3 centrais."""
    a = 1.68
    fatorial = [(i, j, k) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
    axiais = [(-a, 0, 0), (a, 0, 0), (0, -a, 0), (0, a, 0), (0, 0, -a), (0, 0, a)]
    centrais = [(0, 0, 0)] * 3
    return pd.DataFrame(
        fatorial + axiais + centrais, columns=["x1", "x2", "x3"], dtype=float
    )


@pytest.fixture
def ccd_com_resposta() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    dados = _ccd_3_fatores()
    termos = list(BETA_VERDADEIRO)
    matriz = matriz_modelo(dados, _planejamento(["x1", "x2", "x3"]), termos)
    ruido = np.random.default_rng(7).normal(0.0, 0.8, len(dados))
    y = pd.Series(
        matriz.to_numpy() @ np.array(list(BETA_VERDADEIRO.values())) + ruido,
        index=matriz.index,
    )
    return dados, matriz, y


class TestMatrizModelo:
    def test_colunas_seguem_a_ordem_e_a_notacao_canonica(self) -> None:
        dados = _ccd_3_fatores()
        termos = termos_do_modelo(["x1", "x2", "x3"])
        matriz = matriz_modelo(dados, _planejamento(["x1", "x2", "x3"]), termos)
        assert list(matriz.columns) == termos
        assert len(matriz) == len(dados)

    def test_intercepto_e_coluna_de_uns(self) -> None:
        matriz = matriz_modelo(
            _ccd_3_fatores(), _planejamento(["x1", "x2", "x3"]), ["Intercepto", "x1"]
        )
        assert (matriz["Intercepto"] == 1.0).all()

    def test_codifica_niveis_reais_e_calcula_quadrado_e_interacao(self) -> None:
        planejamento = Planejamento(
            tipo="fatorial_completo",
            fatores=[Fator("temperatura", 40.0, 80.0), Fator("ph", 3.0, 9.0)],
        )
        dados = pd.DataFrame({"temperatura": [40.0, 80.0, 60.0], "ph": [3.0, 9.0, 9.0]})
        matriz = matriz_modelo(
            dados,
            planejamento,
            ["Intercepto", "temperatura", "ph", "temperatura^2", "temperatura:ph"],
        )
        assert matriz["temperatura"].tolist() == pytest.approx([-1.0, 1.0, 0.0])
        assert matriz["ph"].tolist() == pytest.approx([-1.0, 1.0, 1.0])
        assert matriz["temperatura^2"].tolist() == pytest.approx([1.0, 1.0, 0.0])
        assert matriz["temperatura:ph"].tolist() == pytest.approx([1.0, 1.0, 0.0])

    def test_ponto_axial_fica_alem_de_um_na_escala_codificada(self) -> None:
        planejamento = Planejamento(
            tipo="composto_central", fatores=[Fator("t", 40.0, 80.0)]
        )
        matriz = matriz_modelo(
            pd.DataFrame({"t": [88.0]}), planejamento, ["Intercepto", "t", "t^2"]
        )
        assert matriz["t"].iloc[0] == pytest.approx(1.4)
        assert matriz["t^2"].iloc[0] == pytest.approx(1.96)

    def test_dados_ja_codificados_entram_como_estao(self) -> None:
        planejamento = Planejamento(
            tipo="composto_central", fatores=[Fator("t", 40.0, 80.0)]
        )
        matriz = matriz_modelo(
            pd.DataFrame({"t": [-1.68, 0.0]}), planejamento, ["t"], codificar=False
        )
        assert matriz["t"].tolist() == pytest.approx([-1.68, 0.0])

    def test_fator_ausente_nos_dados_lista_as_colunas_existentes(self) -> None:
        with pytest.raises(ValueError, match=r"\['x3'\] não estão nos dados"):
            matriz_modelo(
                _ccd_3_fatores()[["x1", "x2"]],
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
            matriz_modelo(pd.DataFrame({"a:b": [0.0]}), planejamento, ["Intercepto"])

    def test_valor_ausente_aponta_a_linha(self) -> None:
        dados = pd.DataFrame({"x1": [1.0, np.nan, -1.0]})
        with pytest.raises(ValueError, match=r"linhas \[1\]"):
            matriz_modelo(dados, _planejamento(["x1"]), ["Intercepto", "x1"])


class TestAjusteOLS:
    def test_bate_com_calculo_independente_em_numpy_e_scipy(
        self, ccd_com_resposta: tuple[pd.DataFrame, pd.DataFrame, pd.Series]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        ajuste = ajustar_ols(matriz, y)

        matriz_v, y_v = matriz.to_numpy(), y.to_numpy()
        n, p = matriz_v.shape
        beta, *_ = np.linalg.lstsq(matriz_v, y_v, rcond=None)
        residuo = y_v - matriz_v @ beta
        ssr = float(residuo @ residuo)
        sigma2 = ssr / (n - p)
        erro_padrao = np.sqrt(np.diag(sigma2 * np.linalg.inv(matriz_v.T @ matriz_v)))
        valor_t = beta / erro_padrao
        valor_p = 2 * stats.t.sf(np.abs(valor_t), df=n - p)
        sst = float(((y_v - y_v.mean()) ** 2).sum())
        t_critico = stats.t.ppf(0.975, df=n - p)

        assert ajuste.coeficientes.to_numpy() == pytest.approx(beta, rel=1e-9)
        assert ajuste.erros_padrao.to_numpy() == pytest.approx(erro_padrao, rel=1e-9)
        assert ajuste.valores_t.to_numpy() == pytest.approx(valor_t, rel=1e-9)
        assert ajuste.valores_p.to_numpy() == pytest.approx(valor_p, rel=1e-9)
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
        assert list(ic.columns) == ["inferior", "superior"]
        assert ic["inferior"].to_numpy() == pytest.approx(
            beta - t_critico * erro_padrao, rel=1e-9
        )
        assert ic["superior"].to_numpy() == pytest.approx(
            beta + t_critico * erro_padrao, rel=1e-9
        )

    def test_coeficientes_saem_com_os_nomes_canonicos(
        self, ccd_com_resposta: tuple[pd.DataFrame, pd.DataFrame, pd.Series]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        ajuste = ajustar_ols(matriz, y)
        assert list(ajuste.coeficientes.index) == list(BETA_VERDADEIRO)
        assert ajuste.termos == list(BETA_VERDADEIRO)

    def test_posto_deficiente_lista_os_termos_redundantes(self) -> None:
        """Fatorial 2² puro não tem curvatura: x1^2 e x2^2 são iguais ao
        intercepto. O ajuste "funcionaria" e devolveria lixo — tem que falhar."""
        dados = pd.DataFrame(
            {"x1": [-1.0, 1.0, -1.0, 1.0], "x2": [-1.0, -1.0, 1.0, 1.0]}
        )
        matriz = matriz_modelo(
            dados, _planejamento(["x1", "x2"]), termos_do_modelo(["x1", "x2"])
        )
        y = pd.Series([1.0, 2.0, 3.0, 5.0], index=matriz.index)
        with pytest.raises(ValueError, match="singular") as erro:
            ajustar_ols(matriz, y)
        assert "['x1^2', 'x2^2']" in str(erro.value)

    def test_sem_graus_de_liberdade_residuais_falha_alto(self) -> None:
        dados = pd.DataFrame(
            {"x1": [-1.0, 1.0, -1.0, 1.0], "x2": [-1.0, -1.0, 1.0, 1.0]}
        )
        matriz = matriz_modelo(
            dados,
            _planejamento(["x1", "x2"]),
            termos_do_modelo(["x1", "x2"], incluir_quadraticos=False),
        )
        with pytest.raises(ValueError, match="graus de liberdade"):
            ajustar_ols(matriz, pd.Series([1.0, 2.0, 3.0, 5.0], index=matriz.index))

    def test_exige_intercepto(self) -> None:
        matriz = pd.DataFrame({"x1": [-1.0, 0.0, 1.0, 2.0]})
        with pytest.raises(ValueError, match="intercepto"):
            ajustar_ols(matriz, pd.Series([1.0, 2.0, 3.0, 4.0]))

    def test_resposta_com_valor_ausente(
        self, ccd_com_resposta: tuple[pd.DataFrame, pd.DataFrame, pd.Series]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        y = y.copy()
        y.iloc[3] = np.nan
        with pytest.raises(ValueError, match="resposta"):
            ajustar_ols(matriz, y)

    def test_x_e_y_desalinhados(
        self, ccd_com_resposta: tuple[pd.DataFrame, pd.DataFrame, pd.Series]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        with pytest.raises(ValueError, match="alinham"):
            ajustar_ols(matriz, y.iloc[:-1])


class TestTabelaTipo2:
    def test_usa_nomes_canonicos_e_nao_vaza_nome_do_patsy(
        self, ccd_com_resposta: tuple[pd.DataFrame, pd.DataFrame, pd.Series]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        tabela = ajustar_ols(matriz, y).tabela_tipo2()
        esperados = [t for t in BETA_VERDADEIRO if t != "Intercepto"]
        assert set(tabela.index) == set(esperados) | {RESIDUO}
        assert not any("I(" in str(nome) for nome in tabela.index)
        assert list(tabela.columns) == [
            "soma_quadrados",
            "graus_liberdade",
            "valor_f",
            "valor_p",
        ]

    def test_linha_de_residuo_bate_com_o_ajuste_canonico(
        self, ccd_com_resposta: tuple[pd.DataFrame, pd.DataFrame, pd.Series]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        ajuste = ajustar_ols(matriz, y)
        residuo = ajuste.tabela_tipo2().loc[RESIDUO]
        assert residuo["soma_quadrados"] == pytest.approx(
            ajuste.soma_quadrados_residual, rel=1e-9
        )
        assert residuo["graus_liberdade"] == ajuste.gl_residuo

    def test_em_delineamento_simetrico_p_do_tipo_ii_igual_ao_teste_t(
        self, ccd_com_resposta: tuple[pd.DataFrame, pd.DataFrame, pd.Series]
    ) -> None:
        """Num CCD simétrico os efeitos principais são ortogonais às
        interações: Tipo II, Tipo III e o teste-t do coeficiente coincidem. É
        uma invariante barata para pegar tradução de nomes trocando termos."""
        _, matriz, y = ccd_com_resposta
        ajuste = ajustar_ols(matriz, y)
        tabela = ajuste.tabela_tipo2()
        for termo in tabela.index.drop(RESIDUO):
            assert tabela.loc[termo, "valor_p"] == pytest.approx(
                ajuste.valores_p[termo], rel=1e-8
            )

    def test_ordem_das_colunas_nao_muda_o_resultado_por_termo(
        self, ccd_com_resposta: tuple[pd.DataFrame, pd.DataFrame, pd.Series]
    ) -> None:
        """O patsy reordena termos por grau; a tradução tem que casar por nome,
        não por posição."""
        _, matriz, y = ccd_com_resposta
        embaralhado = matriz[
            [
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
            ]
        ]
        original = ajustar_ols(matriz, y).tabela_tipo2()
        outra = ajustar_ols(embaralhado, y).tabela_tipo2()
        for termo in original.index:
            assert outra.loc[termo, "soma_quadrados"] == pytest.approx(
                original.loc[termo, "soma_quadrados"], rel=1e-9
            )
            assert outra.loc[termo, "valor_p"] == pytest.approx(
                original.loc[termo, "valor_p"], rel=1e-8, abs=1e-12
            ) or (
                np.isnan(outra.loc[termo, "valor_p"])
                and np.isnan(original.loc[termo, "valor_p"])
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
        dados = pd.DataFrame(pontos, columns=nomes, dtype=float)
        termos = termos_do_modelo(nomes)
        matriz = matriz_modelo(dados, _planejamento(nomes), termos)
        y = pd.Series(
            np.random.default_rng(1).normal(10, 2, len(dados)), index=matriz.index
        )

        tabela = ajustar_ols(matriz, y).tabela_tipo2()

        assert set(tabela.index) == {t for t in termos if t != "Intercepto"} | {RESIDUO}
        assert "Tempo (min)^2" in tabela.index
        assert "Tempo (min):Razão S/L" in tabela.index

    def test_modelo_nao_hierarquico_ajusta_mas_nao_tem_tipo_ii(
        self, ccd_com_resposta: tuple[pd.DataFrame, pd.DataFrame, pd.Series]
    ) -> None:
        _, matriz, y = ccd_com_resposta
        sem_x1_linear = matriz.drop(columns=["x1"])
        ajuste: AjusteOLS = ajustar_ols(sem_x1_linear, y)
        assert "x1^2" in ajuste.coeficientes.index
        with pytest.raises(ValueError, match="não hierárquico"):
            ajuste.tabela_tipo2()
