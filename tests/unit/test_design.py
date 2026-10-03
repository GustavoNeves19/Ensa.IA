"""Testes de codificação de fatores e geração de termos do modelo."""

from __future__ import annotations

import pytest

from lyra.core.design import Fator, interpretar_termo, termos_do_modelo


class TestFator:
    def test_codifica_extremos_e_centro(self) -> None:
        f = Fator(nome="temperatura", minimo=40.0, maximo=80.0, unidade="°C")
        assert f.codificar(40.0) == pytest.approx(-1.0)
        assert f.codificar(80.0) == pytest.approx(1.0)
        assert f.codificar(60.0) == pytest.approx(0.0)

    def test_decodificar_desfaz_codificar(self) -> None:
        f = Fator(nome="ph", minimo=3.0, maximo=9.0)
        for valor in (3.0, 4.5, 6.0, 9.0):
            assert f.decodificar(f.codificar(valor)) == pytest.approx(valor)

    def test_amplitude_zero_falha_alto(self) -> None:
        """Um "fator" que não varia costuma ser erro de planilha. Melhor
        estourar aqui do que produzir matriz singular lá na frente."""
        f = Fator(nome="constante", minimo=5.0, maximo=5.0)
        with pytest.raises(ValueError, match="amplitude zero"):
            f.codificar(5.0)

    def test_ponto_axial_sai_fora_de_menos_um_e_um(self) -> None:
        """Composto central tem pontos axiais além dos vértices — codificar
        precisa extrapolar, não saturar."""
        f = Fator(nome="temperatura", minimo=40.0, maximo=80.0)
        assert f.codificar(88.0) == pytest.approx(1.4)


class TestTermosDoModelo:
    def test_modelo_quadratico_completo_de_dois_fatores(self) -> None:
        assert termos_do_modelo(["x1", "x2"]) == [
            "Intercepto",
            "x1",
            "x2",
            "x1^2",
            "x2^2",
            "x1:x2",
        ]

    def test_fatorial_puro_nao_tem_quadraticos(self) -> None:
        assert termos_do_modelo(["x1", "x2"], incluir_quadraticos=False) == [
            "Intercepto",
            "x1",
            "x2",
            "x1:x2",
        ]

    def test_generaliza_para_k_fatores(self) -> None:
        """O protótipo original era fixo em 3 fatores; o pré-projeto exige
        cobrir planejamentos de tamanhos diferentes."""
        for k in (2, 3, 4, 5):
            nomes = [f"x{i}" for i in range(1, k + 1)]
            termos = termos_do_modelo(nomes)
            # 1 intercepto + k lineares + k quadráticos + C(k,2) interações
            esperado = 1 + k + k + k * (k - 1) // 2
            assert len(termos) == esperado
            assert len(set(termos)) == len(termos), "termos duplicados"

    def test_interacao_de_terceira_ordem(self) -> None:
        termos = termos_do_modelo(["a", "b", "c"], grau_interacao=3)
        assert "a:b:c" in termos

    def test_notacao_de_interacao_e_estavel(self) -> None:
        """A comparação do §4.3(a) casa coeficientes por nome. Se a ordem dos
        fatores numa interação variar, o termo vira "ausente" e a métrica
        quebra em silêncio."""
        assert termos_do_modelo(["b", "a"])[-1] == "b:a"
        assert termos_do_modelo(["a", "b"])[-1] == "a:b"


class TestInterpretarTermo:
    def test_decompoe_cada_forma_da_notacao_canonica(self) -> None:
        assert interpretar_termo("Intercepto") == []
        assert interpretar_termo("x1") == [("x1", 1)]
        assert interpretar_termo("x1^2") == [("x1", 2)]
        assert interpretar_termo("x1:x2") == [("x1", 1), ("x2", 1)]

    def test_e_o_inverso_de_termos_do_modelo(self) -> None:
        """Todo termo gerado tem que ser lido de volta sem sobra nem perda."""
        for termo in termos_do_modelo(["a", "b", "c"], grau_interacao=3)[1:]:
            fatores = "".join(
                f"{n}" if p == 1 else f"{n}^{p}" for n, p in interpretar_termo(termo)
            )
            assert fatores == termo.replace(":", "")

    def test_nome_de_fator_com_espaco_e_acento(self) -> None:
        assert interpretar_termo("Razão S/L^2") == [("Razão S/L", 2)]

    @pytest.mark.parametrize("termo", ["x^1", "x^", "^2", "x^a", "x:", ":x"])
    def test_termo_malformado_falha_alto(self, termo: str) -> None:
        with pytest.raises(ValueError):
            interpretar_termo(termo)
