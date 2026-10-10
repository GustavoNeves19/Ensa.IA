"""Checagem do texto inteiro (§12.5), texto colado (M1) e lista de modelos."""

from __future__ import annotations

import httpx
import pytest

from ensaia.ai.client import ClienteModelo, ConfiguracaoModelo, ErroDeResposta
from ensaia.ai.fidelity import verificar_texto
from ensaia.ai.prompts import montar_prompt_completo
from ensaia.ai.report import gerar_relatorio, relatorio_colado
from ensaia.core.numeros import ocorrencias_numeros
from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    Coeficiente,
    FaltaDeAjuste,
    MetadadosExecucao,
)


def _coef(termo: str, p: float) -> Coeficiente:
    return Coeficiente(
        termo=termo,
        estimativa=3.2,
        erro_padrao=0.4,
        valor_t=8.0,
        valor_p=p,
        significativo=p < 0.05,
    )


def _resultado() -> AnalysisResult:
    ajuste = AjusteResposta(
        resposta="rendimento",
        coeficientes=[_coef("temperatura", 0.0005), _coef("tempo_reacao", 0.21)],
        anova=[],
        r2=0.950,
        r2_ajustado=0.930,
        falta_de_ajuste=FaltaDeAjuste(
            aplicavel=False, motivo_inaplicavel="sem réplicas"
        ),
        n_observacoes=17,
        graus_liberdade_residuo=7,
        termos_incluidos=["temperatura", "tempo_reacao"],
    )
    return AnalysisResult(
        tipo_planejamento="box_behnken",
        fatores=["temperatura", "tempo_reacao"],
        respostas=["rendimento"],
        ajustes=[ajuste],
        metadados=MetadadosExecucao(versao_ensaia="0.1.0"),
    )


def test_ocorrencias_trazem_a_posicao_do_numero() -> None:
    texto = "R² = 0,950 com 17 ensaios"
    r2, n = ocorrencias_numeros(texto)
    assert texto[r2.inicio : r2.fim] == "0,950" and r2.valor == pytest.approx(0.95)
    assert r2.casas == 3 and not r2.porcentagem
    assert texto[n.inicio : n.fim] == "17" and n.valor == 17 and n.casas == 0


def test_arredondamento_do_texto_decide_se_o_numero_confere() -> None:
    from ensaia.core.numeros import numero_confere

    (a,) = ocorrencias_numeros("0,95")
    (b,) = ocorrencias_numeros("99,2%")
    assert numero_confere(a, [0.9504])  # 0,9504 arredonda para 0,95
    assert not numero_confere(b, [1.0])  # 100,0% não vira 99,2%
    # Resposta medida em %: "remoção de 99,2%" é o próprio valor 99,2.
    assert numero_confere(b, [99.24])


def test_texto_fiel_confere_todos_os_numeros() -> None:
    texto = (
        "A temperatura foi significativa (p = 0,0005), e o modelo explicou "
        "95,0% da variação nos 17 ensaios."
    )
    fid = verificar_texto(texto, _resultado())
    assert fid.total == 3 and fid.rastreaveis == 3
    assert fid.fiel and fid.percentual == 1.0
    assert fid.resumo() == "3 de 3 números conferem com os resultados (100%)."


def test_numero_inventado_e_marcado_com_a_posicao() -> None:
    texto = "O modelo explicou 99,2% da variação, com R² = 0,950."
    fid = verificar_texto(texto, _resultado())
    (falso,) = fid.nao_rastreaveis
    assert texto[falso.inicio : falso.fim] == "99,2"
    assert not fid.fiel
    assert fid.resumo().startswith("1 de 2 números")


@pytest.mark.parametrize(
    ("texto", "termo", "afirma"),
    [
        ("O termo tempo_reacao foi significativo.", "tempo_reacao", True),
        ("A temperatura não foi significativa ao nível de 5%.", "temperatura", False),
    ],
)
def test_contradicao_de_significancia(texto: str, termo: str, afirma: bool) -> None:
    (c,) = verificar_texto(texto, _resultado()).contradicoes
    assert (c.termo, c.afirma_significativo) == (termo, afirma)
    assert "mas p =" in c.descricao()


@pytest.mark.parametrize(
    "texto",
    [
        "A temperatura foi significativa.",
        "O tempo reacao não foi significativo.",
        # Contraste interno ou termo composto: a leitura é conservadora.
        "Só a temperatura foi significativa, e o tempo_reacao não.",
        "O termo quadrático da temperatura não foi significativo.",
    ],
)
def test_afirmacoes_corretas_ou_ambiguas_nao_geram_alarme(texto: str) -> None:
    assert verificar_texto(texto, _resultado()).contradicoes == []


def test_relatorio_m0_e_fiel_por_construcao() -> None:
    rel = gerar_relatorio(_resultado(), modo="m0")
    assert rel.fidelidade is not None and rel.fidelidade.fiel
    assert rel.origem == "sem IA (M0)"


def test_texto_colado_vira_relatorio_m1_conferido() -> None:
    rel = relatorio_colado(_resultado(), "  O modelo explicou 99,2% da variação.  ")
    assert rel.modo == "m1" and rel.secoes[0].secao is None
    assert rel.secoes[0].texto == "O modelo explicou 99,2% da variação."
    assert rel.fidelidade is not None and not rel.fidelidade.fiel
    with pytest.raises(ValueError, match="Cole"):
        relatorio_colado(_resultado(), "   ")


def test_m1_nao_passa_pelo_gerador() -> None:
    with pytest.raises(ValueError, match="relatorio_colado"):
        gerar_relatorio(_resultado(), modo="m1")


def test_prompt_completo_leva_as_regras_e_os_fatos_de_cada_secao() -> None:
    prompt = montar_prompt_completo(_resultado())
    assert "Use SOMENTE os números" in prompt
    assert "Modelo ajustado" in prompt
    assert "O termo 'temperatura' é significativo (p = 0,0005 < 0,05)." in prompt
    assert "{{" not in prompt and "{%" not in prompt


def _cliente(handler) -> ClienteModelo:
    config = ConfiguracaoModelo(url_base="http://local/v1/", modelo="m", chave_api="k")
    return ClienteModelo(config, transporte=httpx.MockTransport(handler))


def test_listar_modelos_ordena_e_tira_o_prefixo_do_gemini() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        assert request.headers["Authorization"] == "Bearer k"
        return httpx.Response(
            200, json={"data": [{"id": "models/gemini-b"}, {"id": "a"}, {"x": 1}]}
        )

    with _cliente(handler) as c:
        assert c.listar_modelos() == ["a", "gemini-b"]


def test_listar_modelos_com_chave_recusada_vira_erro_tipado() -> None:
    with (
        _cliente(lambda r: httpx.Response(401, json={"error": "chave"})) as c,
        pytest.raises(ErroDeResposta) as erro,
    ):
        c.listar_modelos()
    assert erro.value.status == 401


def test_posicoes_da_conferencia_apontam_para_o_corpo_do_relatorio() -> None:
    rel = relatorio_colado(_resultado(), "Explicou 99,2% da variação (R² = 0,950).")
    assert rel.fidelidade is not None
    (falso,) = rel.fidelidade.nao_rastreaveis
    assert rel.corpo()[falso.inicio : falso.fim] == "99,2"


def test_provedor_sugere_modelo_de_texto_estavel_e_mais_novo() -> None:
    from ensaia.ai.provedores import PROVEDORES, modelo_sugerido, modelos_de_texto

    gemini = PROVEDORES["gemini"]
    nomes = [
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3-flash-preview",
        "gemini-2.5-flash-preview-tts",
        "text-embedding-004",
    ]
    assert "text-embedding-004" not in modelos_de_texto(gemini, nomes)
    assert modelo_sugerido(gemini, nomes) == "gemini-2.5-flash"
    openai = PROVEDORES["openai"]
    nomes_openai = ["gpt-4o", "gpt-4o-mini", "gpt-4o-mini-tts", "whisper-1"]
    assert modelo_sugerido(openai, nomes_openai) == "gpt-4o-mini"


def test_ia_do_servidor_vem_do_ambiente(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from ensaia.ai.provedores import config_do_servidor

    for var in (
        "ENSAIA_IA_CHAVE",
        "OPENAI_API_KEY",
        "ENSAIA_IA_URL",
        "ENSAIA_IA_MODELO",
        "ENSAIA_MODELO_OPENAI",
    ):
        monkeypatch.delenv(var, raising=False)
    sem_env = tmp_path / "nao-existe.env"
    assert config_do_servidor(sem_env) is None
    monkeypatch.setenv("ENSAIA_IA_CHAVE", "k")
    monkeypatch.setenv("ENSAIA_IA_MODELO", "modelo-x")
    cfg = config_do_servidor(sem_env)
    assert cfg is not None and cfg.modelo == "modelo-x" and cfg.chave_api == "k"
