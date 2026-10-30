"""Relatório em texto: sem IA, copiado para outra IA, IA local ou em nuvem.
Com IA, cada número do texto é conferido e o que não bate fica destacado.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from html import escape

from nicegui import run, ui
from nicegui.events import GenericEventArguments

from ensaia.ai.client import (
    ClienteModelo,
    ConfiguracaoModelo,
    ErroDeConexao,
    ErroDeIA,
    ErroDeResposta,
)
from ensaia.ai.fidelity import (
    RelatorioFidelidade,
    valores_do_resultado,
    verificar_texto,
)
from ensaia.ai.prompts import montar_prompt_completo
from ensaia.ai.provedores import (
    OLLAMA,
    PROVEDORES,
    Provedor,
    config_do_servidor,
    modelo_sugerido,
    modelos_de_texto,
    url_ollama,
)
from ensaia.ai.report import Modo, RelatorioTextual, gerar_relatorio, relatorio_colado
from ensaia.core.results import AnalysisResult
from ensaia.ui.sessao import Sessao

_PROPS_TOGGLE = (
    "no-caps unelevated dense color=white text-color=primary "
    "toggle-color=primary toggle-text-color=white"
)
_SERVIDOR = "servidor"
# Classe do destaque amarelo dos números sem correspondência (§12.5).
_DESTAQUE = "ea-destaque-fid"


def construir_narracao(sessao: Sessao) -> None:
    """Bloco para escolher quem escreve o texto e vê-lo."""
    modos = {
        "m0": "Sem IA",
        "m1": "Copiar para a sua IA",
        "m2": "IA local",
        "m3": "IA em nuvem",
    }

    with ui.element("div").classes("ea-otimizacao ea-narrar"):
        ui.html('<div class="ea-secao-titulo">Relatório em texto</div>')
        ui.html(
            '<div class="ea-secao-sub">Os números vêm sempre da análise. Escolha '
            "quem escreve o texto: com IA, o EnsaIA confere cada número citado e "
            "marca o que não bate.</div>"
        )
        escolha = ui.toggle(modos, value="m0").props(_PROPS_TOGGLE).classes("ea-forma")
        painel = ui.column().classes("w-full gap-2")
    saida = ui.column().classes("w-full ea-slot")

    montadores: dict[str, Callable[[Sessao, ui.column], None]] = {
        "m0": _painel_m0,
        "m1": _painel_m1,
        "m2": _painel_m2,
        "m3": _painel_m3,
    }

    def trocar(modo: str) -> None:
        """Troca o painel pelo do modo escolhido."""
        sessao.ouvintes.pop("narracao", None)
        painel.clear()
        saida.clear()
        with painel:
            montadores[modo](sessao, saida)

    escolha.on_value_change(lambda e: trocar(str(e.value)))
    trocar("m0")


# --- Os quatro modos ---------------------------------------------------------


def _painel_m0(sessao: Sessao, saida: ui.column) -> None:
    """Modo sem IA: o texto montado dos fatos."""
    def mostrar() -> None:
        """Gera e mostra o texto sem IA."""
        relatorio = gerar_relatorio(sessao.analise, modo="m0")
        sessao.texto = relatorio
        saida.clear()
        with saida:
            mostrar_relatorio(relatorio, sessao.analise)

    # Refaz o texto quando a análise ganha o ponto ótimo depois.
    sessao.ouvintes["narracao"] = mostrar
    mostrar()


# A cópia roda no navegador, no próprio clique (exigência dos navegadores).
_JS_COPIAR = """async () => {
  const fonte = document.getElementById(%s);
  const texto = fonte ? fonte.textContent : '';
  let ok = false;
  try { await navigator.clipboard.writeText(texto); ok = true; } catch (e) {
    const area = document.createElement('textarea');
    area.value = texto; area.setAttribute('readonly', '');
    area.style.position = 'fixed'; area.style.opacity = '0';
    document.body.appendChild(area); area.select();
    try { ok = document.execCommand('copy'); } catch (e2) { ok = false; }
    area.remove();
  }
  emit(ok);
}"""


def _painel_m1(sessao: Sessao, saida: ui.column) -> None:
    """Modo copiar: o pedido para outra IA e a conferência da resposta."""
    def copiado(evento: GenericEventArguments) -> None:
        """Avisa se o pedido foi copiado."""
        if evento.args:
            ui.notify("Pedido copiado. Cole na IA que você usa.", position="top")
        else:
            ui.notify(
                "Não consegui copiar sozinho. Abra \"Ver o pedido\", selecione o "
                "texto e copie.",
                type="warning",
                position="top",
                timeout=9000,
            )

    def conferir() -> None:
        """Confere o texto colado da IA."""
        try:
            relatorio = relatorio_colado(sessao.analise, str(colado.value or ""))
        except ValueError as erro:
            ui.notify(str(erro), type="warning", position="top")
            return
        sessao.texto = relatorio
        saida.clear()
        with saida:
            mostrar_relatorio(relatorio, sessao.analise)

    ui.html(
        '<div class="ea-ler">O EnsaIA monta o pedido com os resultados já '
        "verificados. Copie, cole no ChatGPT, Gemini, Copilot ou outra IA de sua "
        "escolha e traga a resposta de volta: cada número dela será conferido."
        "</div>"
    )
    fonte = ui.html("").classes("hidden")
    with ui.element("div").classes("ea-acoes"):
        ui.button("Copiar o pedido").props("unelevated").classes("ea-botao").on(
            "click", copiado, js_handler=_JS_COPIAR % json.dumps(fonte.html_id)
        )
    with ui.expansion("Ver o pedido").classes("ea-opcoes w-full"):
        pedido = ui.html("").classes("ea-pedido")

    def atualizar() -> None:
        """Atualiza o pedido quando a análise muda."""
        texto = escape(montar_prompt_completo(sessao.analise))
        fonte.set_content(texto)
        pedido.set_content(texto)

    sessao.ouvintes["narracao"] = atualizar  # o ótimo pode entrar depois
    atualizar()
    colado = (
        ui.textarea(
            "Cole aqui a resposta da IA",
            placeholder="O texto que a IA escreveu, do jeito que veio.",
        )
        .props("outlined autogrow")
        .classes("w-full ea-colar")
    )
    ui.button("Conferir os números", on_click=conferir).props("unelevated").classes(
        "ea-botao"
    )


def _painel_m2(sessao: Sessao, saida: ui.column) -> None:
    """Modo IA local: Ollama no computador onde o EnsaIA roda."""
    ui.html(
        '<div class="ea-ler">Usa o <b>Ollama</b> aberto no computador onde o EnsaIA '
        "está rodando: nada sai dessa máquina. Modelos de 4B a 8B (Qwen 3, Llama 3, "
        "Gemma 3) dão conta, porque a IA só reescreve os resultados.</div>"
    )
    endereco = ui.input("Endereço do Ollama", value=url_ollama() or OLLAMA.url_base)
    endereco.props("dense outlined").classes("ea-campo-longo")

    def config(modelo: str) -> ConfiguracaoModelo:
        """Configuração do Ollama com o modelo escolhido."""
        # O Ollama pode levar mais tempo para carregar o modelo na 1ª chamada.
        return ConfiguracaoModelo(
            url_base=str(endereco.value), modelo=modelo, timeout_s=60.0
        )

    _conectar_e_narrar(sessao, saida, OLLAMA, config, modo="m2")


def _painel_m3(sessao: Sessao, saida: ui.column) -> None:
    """Modo IA em nuvem: escolha do provedor."""
    servidor = config_do_servidor()
    opcoes = {p.id: p.nome for p in PROVEDORES.values()}
    if servidor is not None:
        opcoes = {_SERVIDOR: "IA do EnsaIA (sem chave)", **opcoes}
    provedor = ui.select(opcoes, value=next(iter(opcoes)), label="Provedor")
    provedor.props("dense outlined").classes("ea-campo-longo")
    detalhe = ui.column().classes("w-full gap-2")

    def montar(id_: str) -> None:
        """Monta o painel do provedor escolhido."""
        detalhe.clear()
        saida.clear()
        with detalhe:
            if id_ == _SERVIDOR and servidor is not None:
                _painel_servidor(sessao, saida, servidor)
            else:
                _painel_chave(sessao, saida, PROVEDORES[id_])

    provedor.on_value_change(lambda e: montar(str(e.value)))
    montar(next(iter(opcoes)))


def _painel_servidor(
    sessao: Sessao, saida: ui.column, config: ConfiguracaoModelo
) -> None:
    """Painel da IA oferecida pelo servidor."""
    ui.html(
        '<div class="ea-ler">Quem hospeda este EnsaIA oferece uma IA pronta '
        f"(modelo <b>{escape(config.modelo)}</b>). Só os resultados verificados "
        "são enviados, nunca a sua planilha.</div>"
    )
    botao = ui.button("Escrever com IA").props("unelevated").classes("ea-botao")
    botao.on_click(lambda: _narrar(sessao, saida, config, "m3", botao))


def _painel_chave(sessao: Sessao, saida: ui.column, provedor: Provedor) -> None:
    """Painel de provedor com a chave do usuário."""
    estado: dict[str, str] = {}
    ui.html(
        '<div class="ea-ler">A chave fica só na memória desta aba: não é gravada '
        "nem volta ao navegador. Só os resultados verificados são enviados ao "
        "provedor, nunca a sua planilha.</div>"
    )
    with ui.element("div").classes("ea-controles"):
        campo = (
            ui.input(
                "Sua chave de API",
                password=True,
                password_toggle_button=True,
            )
            .props("dense outlined autocomplete=off")
            .classes("ea-campo-longo")
        )
        if provedor.onde_criar_chave:
            ui.link("Criar uma chave", provedor.onde_criar_chave, new_tab=True).classes(
                "ea-link"
            )

    def config(modelo: str) -> ConfiguracaoModelo:
        """Configuração do provedor com a chave guardada."""
        return ConfiguracaoModelo(
            url_base=provedor.url_base, modelo=modelo, chave_api=estado.get("chave")
        )

    def guardar_chave() -> bool:
        """Guarda a chave na memória e limpa o campo."""
        chave = str(campo.value or "").strip()
        if chave:
            estado["chave"] = chave
            campo.value = ""  # a chave não volta ao navegador
        if not estado.get("chave"):
            ui.notify("Cole a sua chave de API.", type="warning", position="top")
            return False
        return True

    def esquecer() -> None:
        """Esquece a chave guardada."""
        estado.clear()

    _conectar_e_narrar(
        sessao,
        saida,
        provedor,
        config,
        modo="m3",
        antes=guardar_chave,
        ao_recusar=esquecer,
    )


# --- Conectar, escolher o modelo e narrar ------------------------------------


def _conectar_e_narrar(
    sessao: Sessao,
    saida: ui.column,
    provedor: Provedor,
    config: Callable[[str], ConfiguracaoModelo],
    *,
    modo: Modo,
    antes: Callable[[], bool] = lambda: True,
    ao_recusar: Callable[[], None] = lambda: None,
) -> None:
    """Botão Conectar, lista de modelos e botão Escrever."""
    escolha = ui.column().classes("w-full gap-2")

    async def conectar() -> None:
        """Lista os modelos do provedor e libera o Escrever."""
        if not antes():
            return
        botao.props("loading")
        try:
            nomes = await run.io_bound(_listar, config("-"))
        except ErroDeIA as erro:
            if _chave_recusada(erro):
                ao_recusar()
            ui.notify(
                _mensagem_erro(erro, provedor),
                type="negative",
                position="top",
                timeout=9000,
            )
            return
        finally:
            botao.props(remove="loading")
        if nomes is None:  # o servidor encerrou no meio
            return
        modelos = modelos_de_texto(provedor, nomes)
        if not modelos:
            ui.notify(
                "O provedor não listou nenhum modelo de texto.",
                type="warning",
                position="top",
            )
            return
        escolha.clear()
        with escolha, ui.element("div").classes("ea-controles"):
            modelo = (
                ui.select(
                    modelos,
                    value=modelo_sugerido(provedor, modelos),
                    label="Modelo",
                    with_input=True,
                )
                .props("dense outlined")
                .classes("ea-campo-longo")
            )
            narrar = (
                ui.button("Escrever com IA").props("unelevated").classes("ea-botao")
            )
            narrar.on_click(
                lambda: _narrar(sessao, saida, config(str(modelo.value)), modo, narrar)
            )

    botao = (
        ui.button("Conectar", on_click=conectar).props("unelevated").classes("ea-botao")
    )


def _listar(config: ConfiguracaoModelo) -> list[str]:
    """Lista os modelos do provedor."""
    with ClienteModelo(config) as cliente:
        return cliente.listar_modelos()


async def _narrar(
    sessao: Sessao,
    saida: ui.column,
    config: ConfiguracaoModelo,
    modo: Modo,
    botao: ui.button,
) -> None:
    """Gera o texto com a IA e mostra o resultado."""
    analise = sessao.analise
    saida.clear()
    with saida:
        ui.spinner(size="lg").classes("ea-spinner")
        ui.html(
            '<div class="ea-secao-sub">Escrevendo uma seção por vez e conferindo '
            "cada número…</div>"
        )

    def trabalho() -> RelatorioTextual:
        """Gera o relatório com o cliente da IA."""
        with ClienteModelo(config) as cliente:
            return gerar_relatorio(analise, modo=modo, cliente=cliente)

    botao.props("loading")
    try:
        relatorio = await run.io_bound(trabalho)
    finally:
        botao.props(remove="loading")
    if relatorio is None:  # o servidor encerrou no meio da chamada
        return
    sessao.texto = relatorio
    saida.clear()
    with saida:
        mostrar_relatorio(relatorio, analise)


def _mensagem_erro(erro: ErroDeIA, provedor: Provedor) -> str:
    """Mensagem de erro da IA em português claro."""
    if isinstance(erro, ErroDeResposta):
        if _chave_recusada(erro):
            return (
                f"O {provedor.nome} recusou a chave. Confira se ela foi colada inteira."
            )
        if erro.status == 429:
            return f"O {provedor.nome} atingiu o limite de uso. Tente daqui a pouco."
        return f"O {provedor.nome} respondeu com erro ({erro.status})."
    if isinstance(erro, ErroDeConexao) and provedor is OLLAMA:
        return (
            "Não encontrei o Ollama nesse endereço. Ele está aberto no computador "
            "onde o EnsaIA está rodando?"
        )
    return f"Não consegui falar com o {provedor.nome}. Verifique a conexão."


def _chave_recusada(erro: ErroDeIA) -> bool:
    """Diz se o erro foi de chave recusada."""
    if not isinstance(erro, ErroDeResposta):
        return False
    return erro.status in (401, 403) or (
        erro.status == 400 and "key" in str(erro).lower()
    )


# --- O texto na tela ---------------------------------------------------------


def mostrar_relatorio(relatorio: RelatorioTextual, analise: AnalysisResult) -> None:
    """Mostra o texto, quem o escreveu e a conferência dos números."""
    valores = valores_do_resultado(analise)
    with ui.element("div").classes("ea-relatorio"):
        ui.html(
            f'<div class="ea-secao-sub">Escrito por: {escape(relatorio.origem)}</div>'
        )
        if relatorio.fidelidade is not None and relatorio.modo != "m0":
            _conferencia(relatorio)
        for secao in relatorio.secoes:
            fid = verificar_texto(secao.texto, analise, valores=valores)
            tag_classe = "ea-tag-ia" if secao.com_ia else "ea-tag-m0"
            tag_texto = "IA" if secao.com_ia else "texto fiel"
            ui.html(
                '<div class="ea-rel-secao">'
                f'<div class="ea-rel-titulo">{escape(secao.titulo)} '
                f'<span class="{tag_classe}">· {tag_texto}</span></div>'
                f'<div class="ea-rel-texto">{_com_destaques(secao.texto, fid)}</div>'
                "</div>"
            )
        for aviso in relatorio.avisos:
            ui.html(f'<div class="ea-aviso">{escape(aviso)}</div>')


def _conferencia(relatorio: RelatorioTextual) -> None:
    """Resumo da conferência e os números que não batem."""
    fid = relatorio.fidelidade
    if fid is None:
        return
    classe = "ea-conferido" if fid.fiel else "ea-nao-conferido"
    ui.html(f'<div class="{classe}">Conferência: {escape(fid.resumo())}</div>')
    if fid.nao_rastreaveis:
        ui.html(
            f'<div class="ea-ler">Os números <mark class="{_DESTAQUE}">em destaque'
            "</mark> não aparecem nos resultados da análise: confira antes de usar "
            "o texto.</div>"
        )
    for contradicao in fid.contradicoes:
        ui.html(f'<div class="ea-aviso">{escape(contradicao.descricao())}</div>')


def _com_destaques(texto: str, fid: RelatorioFidelidade) -> str:
    """HTML do texto com os números sem correspondência marcados."""
    partes: list[str] = []
    cursor = 0
    for numero in fid.nao_rastreaveis:
        partes.append(escape(texto[cursor : numero.inicio]))
        trecho = escape(texto[numero.inicio : numero.fim])
        partes.append(f'<mark class="{_DESTAQUE}">{trecho}</mark>')
        cursor = numero.fim
    partes.append(escape(texto[cursor:]))
    return "".join(partes)
