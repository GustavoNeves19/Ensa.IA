"""Testes da orquestração do relatório textual (ai/report).

O "modelo" é o ClienteModelo real sobre httpx.MockTransport: devolve o texto que
o teste escolher (fiel, com número inventado, ou erro de conexão), sem rede.
"""

from __future__ import annotations

import httpx
import pytest

from ensaia.ai.client import (
    ClienteModelo,
    ConfiguracaoModelo,
    ErroDeConexao,
    ErroDeResposta,
    ErroDeTempo,
)
from ensaia.ai.report import gerar_relatorio
from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    Coeficiente,
    FaltaDeAjuste,
    MetadadosExecucao,
    PontoOtimo,
)


def _resultado(*, ponto_otimo: PontoOtimo | None = None) -> AnalysisResult:
    ajuste = AjusteResposta(
        resposta="rendimento",
        coeficientes=[
            Coeficiente(
                termo="temperatura",
                estimativa=3.2,
                erro_padrao=0.4,
                valor_t=8.0,
                valor_p=0.0005,
                significativo=True,
            )
        ],
        anova=[],
        r2=0.950,
        r2_ajustado=0.930,
        falta_de_ajuste=FaltaDeAjuste(
            aplicavel=False, motivo_inaplicavel="sem réplicas"
        ),
        n_observacoes=17,
        graus_liberdade_residuo=7,
        termos_incluidos=["temperatura"],
    )
    return AnalysisResult(
        tipo_planejamento="composto_central",
        fatores=["temperatura", "ph"],
        respostas=["rendimento"],
        ajustes=[ajuste],
        metadados=MetadadosExecucao(versao_ensaia="0.1.0"),
        ponto_otimo=ponto_otimo,
    )


def _cliente(handler) -> ClienteModelo:
    config = ConfiguracaoModelo(
        url_base="http://local/v1", modelo="modelo-teste", max_tentativas=1
    )
    return ClienteModelo(
        config, transporte=httpx.MockTransport(handler), dormir=lambda _s: None
    )


def _responder(texto: str):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": texto}}]}
        )

    return handler


# --- M0 (sem IA) ----------------------------------------------------------


def test_m0_usa_os_fatos_sem_ia() -> None:
    rel = gerar_relatorio(_resultado(), modo="m0")

    assert rel.modo == "m0"
    assert rel.modelo_usado is None
    assert rel.avisos == []
    assert all(not s.com_ia for s in rel.secoes)
    # As seções com fato entram; otimização (sem ponto ótimo) fica de fora.
    secoes = {s.secao for s in rel.secoes}
    assert secoes == {"planejamento", "modelo", "anova", "diagnostico"}
    # O texto M0 é feito dos próprios fatos verificados.
    modelo = next(s for s in rel.secoes if s.secao == "modelo")
    assert "'temperatura' é significativo" in modelo.texto


def test_otimizacao_entra_quando_ha_ponto_otimo() -> None:
    otimo = PontoOtimo(
        coordenadas={"temperatura": 1.0, "ph": -0.5},
        resposta_prevista={"rendimento": 92.5},
        desejabilidade_global=0.87,
    )
    rel = gerar_relatorio(_resultado(ponto_otimo=otimo), modo="m0")
    assert any(s.secao == "otimizacao" for s in rel.secoes)


def test_modo_com_ia_exige_cliente() -> None:
    with pytest.raises(ValueError):
        gerar_relatorio(_resultado(), modo="m2", cliente=None)


# --- M2/M3 (com IA) -------------------------------------------------------


def test_texto_fiel_do_modelo_e_aceito() -> None:
    # Sem números citados → fiel para toda seção.
    cliente = _cliente(_responder("Parágrafo fiel, escrito sem citar números."))
    rel = gerar_relatorio(_resultado(), modo="m2", cliente=cliente)

    assert rel.modo == "m2"
    assert rel.modelo_usado == "modelo-teste"
    assert rel.avisos == []
    assert all(s.com_ia for s in rel.secoes)
    assert all("Parágrafo fiel" in s.texto for s in rel.secoes)


def test_numero_inventado_fica_com_a_ia_e_avisa() -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "O valor foi 123456,0."}}]},
        )

    cliente = _cliente(handler)
    rel = gerar_relatorio(
        _resultado(), modo="m2", cliente=cliente, tentativas_fidelidade=2
    )

    # O texto continua sendo o da IA; o número solto fica marcado na conferência.
    assert all(s.com_ia and "123456,0" in s.texto for s in rel.secoes)
    assert len(rel.avisos) == len(rel.secoes)
    assert all("em destaque" in a for a in rel.avisos)
    assert rel.fidelidade is not None and not rel.fidelidade.fiel
    # Retentou 2 vezes por seção (4 seções com fato × 2).
    assert chamadas["n"] == len(rel.secoes) * 2


def test_fica_a_tentativa_com_menos_numeros_soltos() -> None:
    respostas = iter(["Valores 111,1 e 222,2.", "Valor 333,3."] * 4)

    def handler(request: httpx.Request) -> httpx.Response:
        texto = next(respostas)
        return httpx.Response(200, json={"choices": [{"message": {"content": texto}}]})

    rel = gerar_relatorio(_resultado(), modo="m2", cliente=_cliente(handler))
    assert all(s.texto == "Valor 333,3." for s in rel.secoes)


def test_erro_de_conexao_sobe_sem_texto_do_sistema() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sem rota", request=request)

    with pytest.raises(ErroDeConexao):
        gerar_relatorio(_resultado(), modo="m3", cliente=_cliente(handler))


def test_tempo_esgotado_sobe_como_erro_de_tempo() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("demorou", request=request)

    with pytest.raises(ErroDeTempo) as info:
        gerar_relatorio(_resultado(), modo="m3", cliente=_cliente(handler))
    assert info.value.segundos == 30.0


def test_chave_recusada_para_na_primeira_chamada() -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        return httpx.Response(401, json={"error": "chave recusada"})

    with pytest.raises(ErroDeResposta) as info:
        gerar_relatorio(_resultado(), modo="m3", cliente=_cliente(handler))
    assert info.value.status == 401
    assert chamadas["n"] == 1


def test_texto_completo_junta_titulos_e_secoes() -> None:
    rel = gerar_relatorio(_resultado(), modo="m0")
    completo = rel.texto_completo()
    assert completo.startswith("## ")
    assert rel.secoes[0].titulo in completo


def test_ao_avancar_segue_as_secoes_pedidas_a_ia() -> None:
    passos: list[tuple[int, int, str]] = []
    rel = gerar_relatorio(
        _resultado(),
        modo="m3",
        cliente=_cliente(_responder("Parágrafo sem números.")),
        ao_avancar=lambda n, total, titulo: passos.append((n, total, titulo)),
    )

    assert [(n, total) for n, total, _ in passos] == [(1, 4), (2, 4), (3, 4), (4, 4)]
    assert [t for _, _, t in passos] == [s.titulo for s in rel.secoes]
