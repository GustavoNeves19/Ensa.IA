"""Identidade visual da interface — o ponto único de troca de marca da UI.

A paleta é a **oficial da Universidade Federal Rural da Amazônia** (Manual de
Uso da Marca da Ufra, ASCOM/Ufra, 2022, p. 10): o logotipo é composto por dois
verdes — verde (#40A551) e verde oliva (#9B921C) — mais o preto (#1D1D1B).
Trabalhamos sobre esses três, acrescidos de um verde-mata profundo derivado
(para profundidade e ações) e de um papel quente levemente oliva como fundo —
nada do cinza neutro dos UI kits nem do creme genérico.

As fontes são da família **IBM Plex** (IBM, licença SIL OFL 1.1), desenhada
para contexto técnico: a **Plex Serif** carrega a marca e os títulos, a **Plex
Sans** o corpo, as tabelas e as fórmulas. Entram os recortes oficiais da IBM
por alfabeto (`unicode-range`): o português cabe no Latin1, e o grego e os
símbolos só são baixados quando aparecem (nas fórmulas). Os subscritos das
fórmulas (eᵢ, hᵢᵢ, Xᵀ) não existem no Plex; vêm de um recorte mínimo da Noto
Sans (OFL), o "EnsaIA Simbolos". Arquivos e licenças em `ui/static/fonts/`.

Trocar a marca inteira é mexer só neste arquivo: as cores entram no tema do
Quasar via `ui.colors` e todo o resto (fonte, fundo, atmosfera) via o CSS
injetado em `aplicar_tema`.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from nicegui import app, ui

# --- Paleta oficial da Ufra + tons de apoio derivados --------------------------
TINTA = "#1D1D1B"  # Ufra preto — texto e títulos
VERDE = "#40A551"  # Ufra verde — acento vivo (a "IA", o ótimo, links, foco)
OLIVA = "#9B921C"  # Ufra verde oliva — secundária (curvas de nível, detalhes)
OLIVA_ESCURO = "#6E6713"  # oliva escurecido — texto pequeno legível (AA)
VERDE_ESCURO = "#0E3A26"  # verde-mata profundo (derivado) — ações, superfícies escuras
CINZA = "#5E5A4E"  # cinza quente/oliva — texto secundário (contraste ≥ 5:1 no papel)
PAPEL = "#F3F2EA"  # papel quente, levemente oliva — fundo da página
PAPEL_ALTO = "#FCFBF6"  # superfície elevada (painéis) — um tom acima do papel
LINHA = "rgba(29,29,27,0.08)"  # borda auto-colorida, sentida mais que vista

# Compat: `report/theme.py` e trechos antigos ainda falam em "acento".
ACENTO = VERDE

# --- Cores dos gráficos (validadas: daltonismo, visão normal e contraste ≥ 3:1
# sobre PAPEL_ALTO; a rampa passa o teste ordinal de tom único e passo visível).
SERIE = "#2E8540"  # marca principal: termo significativo, ensaios
SERIE_APAGADA = "#968F7A"  # cinza quente de ênfase: termo não significativo
REFERENCIA = CINZA  # linhas de referência (y = x, zero, t crítico, reta do Q-Q)
GRADE = "#E7E4D8"  # linhas de grade: um passo fora da superfície, recessivas
# Rampa sequencial (claro → escuro) da superfície e do contorno: maior = mais escuro.
RAMPA = ["#8FBD7D", "#6FA96A", "#529257", "#3B7B47", "#28643A", "#1A4E2D", "#0E3A26"]

_STATIC = Path(__file__).parent / "static"
# Rota estática servida uma única vez (nível de módulo roda no import). Serve as
# fontes self-hosted sem depender de CDN — a interface roda offline (princípio
# do núcleo), então a marca também não pode pedir rede. `suppress` cobre o
# reimport em testes/reload, quando a rota já existe.
with contextlib.suppress(Exception):
    app.add_static_files("/ensaia-static", str(_STATIC))

# Grão finíssimo (feTurbulence, dessaturado) em data-uri: quebra o achatado dos
# fundos e remove banding. Fica ATRÁS do conteúdo, a 3,5% — sente-se, não se vê.
_GRAO = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/></svg>"  # noqa: E501


# Recortes oficiais do IBM Plex (fonts/split da IBM) e os intervalos Unicode de
# cada um, copiados do CSS que a própria IBM publica junto dos arquivos.
_LATIN1 = (
    "U+0000, U+000D, U+0020-007E, U+00A0-00FF, U+0131, U+0152-0153, U+02C6, "
    "U+02DA, U+02DC, U+2013-2014, U+2018-201A, U+201C-201E, U+2020-2022, U+2026, "
    "U+2030, U+2039-203A, U+2044, U+20AC, U+2122, U+2212, U+FB01-FB02"
)
_GREGO = "U+037E, U+0386-038A, U+038C, U+038E-03A1, U+03A3-03CE"
_PI = (
    "U+0E3F, U+2000-200D, U+2015, U+2028-2029, U+202F, U+2032-2033, U+2070, "
    "U+2074-2079, U+2080-2089, U+2113, U+2116, U+2126, U+212E, U+2150-2151, "
    "U+2153-215E, U+2190-2199, U+21A9-21AA, U+21B0-21B3, U+21B6-21B7, "
    "U+21BA-21BB, U+21C4, U+21C6, U+2202, U+2206, U+220F, U+2211, U+2215, "
    "U+221A, U+221E, U+222B, U+2248, U+2260, U+2264-2265, U+25CA, U+2713, "
    "U+274C, U+2B0E-2B11, U+FEFF, U+FFFD"
)
# (família, arquivo, peso, estilo, intervalo)
_ARQUIVOS_FONTE: tuple[tuple[str, str, int, str, str], ...] = (
    ("IBM Plex Serif", "IBMPlexSerif-Medium-Latin1", 500, "normal", _LATIN1),
    ("IBM Plex Serif", "IBMPlexSerif-SemiBold-Latin1", 600, "normal", _LATIN1),
    ("IBM Plex Serif", "IBMPlexSerif-MediumItalic-Latin1", 500, "italic", _LATIN1),
    ("IBM Plex Sans", "IBMPlexSans-Regular-Latin1", 400, "normal", _LATIN1),
    ("IBM Plex Sans", "IBMPlexSans-Regular-Greek", 400, "normal", _GREGO),
    ("IBM Plex Sans", "IBMPlexSans-Regular-Pi", 400, "normal", _PI),
    ("IBM Plex Sans", "IBMPlexSans-SemiBold-Latin1", 600, "normal", _LATIN1),
    (
        "EnsaIA Simbolos",
        "EnsaIA-Simbolos",
        400,
        "normal",
        "U+0233, U+0304, U+1D2C-1D6A, U+2070-209F, U+2C7C",
    ),
)


def _fontes() -> str:
    """Os @font-face de cada recorte, servidos da pasta estática do pacote."""
    return "\n".join(
        f"""    @font-face {{
      font-family: '{familia}';
      src: url('/ensaia-static/fonts/{arquivo}.woff2') format('woff2');
      font-weight: {peso}; font-style: {estilo}; font-display: swap;
      unicode-range: {intervalo};
    }}"""
        for familia, arquivo, peso, estilo, intervalo in _ARQUIVOS_FONTE
    )


def _css() -> str:
    """Folha de estilo da marca: fontes, atmosfera, grão e o uploader."""
    return f"""
    <style>
{_fontes()}

    :root {{
      --tinta: {TINTA};
      --verde: {VERDE};
      --oliva: {OLIVA};
      --oliva-escuro: {OLIVA_ESCURO};
      --verde-escuro: {VERDE_ESCURO};
      --cinza: {CINZA};
      --papel: {PAPEL};
      --papel-alto: {PAPEL_ALTO};
      --linha: {LINHA};
      --fonte-titulo: 'IBM Plex Serif', Georgia, 'Times New Roman', serif;
      --fonte-corpo: 'IBM Plex Sans', 'EnsaIA Simbolos', system-ui, -apple-system,
        'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}

    /* O corpo fala o neutro de sistema; o fundo é papel quente com um grão
       finíssimo (feTurbulence em data-uri) — sente-se, não se vê, e fica ATRÁS
       de todo o conteúdo. Sem scroll horizontal, nunca. */
    html, body {{ overflow-x: hidden; }}
    body {{
      background-color: var(--papel);
      background-image:
        radial-gradient(1100px 680px at 86% -8%,
          rgba(64,165,81,0.10), transparent 60%),
        url("{_GRAO}");
      color: var(--tinta);
      font-family: var(--fonte-corpo);
      -webkit-font-smoothing: antialiased;
    }}
    .nicegui-content {{ padding: 0; }}

    /* Tipografia de assinatura e utilitários da marca. */
    .ea-serif {{ font-family: var(--fonte-titulo); }}
    .ea-ital  {{ font-family: var(--fonte-titulo); font-style: italic; }}

    /* --- Dropzone (Quasar QUploader) vestida com a marca --------------------- */
    .ensaia-upload {{
      width: 100%;
      border: 1px dashed rgba(155,146,28,0.45);
      border-radius: 14px;
      background: var(--papel-alto);
      box-shadow: none;
      transition: border-color .18s ease, background-color .18s ease;
    }}
    .ensaia-upload:hover {{
      border-color: var(--verde);
      background: #F6FBF5;
    }}
    .ensaia-upload .q-uploader__header {{
      background: var(--verde-escuro);
      color: var(--papel);
    }}
    .ensaia-upload .q-uploader__title {{ font-weight: 600; line-height: 1.3; }}
    /* Em repouso o Quasar mostra "0.0B / 0.00%" (progresso) — sem sentido aqui. */
    .ensaia-upload .q-uploader__subtitle {{ display: none; }}
    .ensaia-upload .q-uploader__dnd {{
      background: rgba(64,165,81,0.06);
      outline: none;
    }}
    .ensaia-upload .q-btn {{ color: var(--papel); }}

    /* Tabela de prévia: linhas quietas, cabeçalho em tinta. */
    .ensaia-previa thead th {{
      background: #EFEEE4;
      color: var(--tinta);
      font-weight: 600;
    }}
    .ensaia-previa td, .ensaia-previa th {{ border-color: var(--linha) !important; }}

    /* --- Composição da página ----------------------------------------------- */
    .ea-page {{ position: relative; width: 100%; min-height: 100vh; overflow: hidden; }}
    /* A superfície de resposta (assinatura) sangra pelo canto superior direito e
       se dissolve no papel por uma máscara radial — sem emenda dura. */
    .ea-atmosfera {{
      position: absolute; top: -64px; right: -118px;
      width: min(680px, 90vw); pointer-events: none; z-index: 0;
      -webkit-mask-image:
        radial-gradient(72% 70% at 60% 32%, #000 52%, transparent 100%);
      mask-image:
        radial-gradient(72% 70% at 60% 32%, #000 52%, transparent 100%);
    }}
    .ea-atmosfera svg {{ width: 100%; height: auto; display: block; }}
    .ea-col {{
      position: relative; z-index: 1; max-width: 1080px; margin: 0 auto;
      padding: clamp(2.6rem, 6vw, 5.5rem) clamp(1.25rem, 5vw, 2.25rem) 3.25rem;
    }}
    .ea-main {{
      max-width: 620px; display: flex; flex-direction: column;
      gap: clamp(1.9rem, 4vw, 2.7rem);
    }}

    /* Marca e títulos. */
    .ea-marca {{ font-family: var(--fonte-titulo); font-weight: 600;
      font-size: clamp(3.6rem, 12vw, 5.4rem); line-height: .95;
      letter-spacing: -0.015em; }}

    /* Seletor de dicas, logo abaixo da marca: três degraus com os nomes embaixo.
       A folga lateral evita que o primeiro e o último nome saiam da caixa. */
    .ea-seletor-dicas {{ margin-top: 1.1rem; width: min(100%, 380px); }}
    .ea-seletor-titulo {{ color: var(--cinza); font-size: .78rem; font-weight: 600;
      letter-spacing: .02em; }}
    .ea-seletor-slider {{ padding: 0 2.6rem; margin-top: .2rem; }}
    .ea-seletor-slider .q-slider__marker-labels {{ font-size: .78rem;
      color: var(--tinta); white-space: nowrap; }}
    .ea-headline {{ font-family: var(--fonte-titulo); font-weight: 500;
      font-size: clamp(1.9rem, 5vw, 2.85rem); line-height: 1.14;
      color: var(--tinta); max-width: 23ch; }}
    .ea-sub {{ color: var(--cinza); font-size: 1.02rem; line-height: 1.55;
      max-width: 36rem; }}

    /* Abertura: texto à esquerda, os sete passos à direita. No celular, a
       lista desce para baixo do texto. */
    .ea-hero {{ display: grid; align-items: start;
      grid-template-columns: minmax(0, 620px) minmax(220px, 270px);
      justify-content: space-between; gap: 2rem 3rem;
      margin-bottom: clamp(1.9rem, 4vw, 2.7rem); }}
    .ea-hero-texto {{ display: flex; flex-direction: column; min-width: 0;
      gap: clamp(1.9rem, 4vw, 2.7rem); }}
    @media (max-width: 860px) {{
      .ea-hero {{ grid-template-columns: minmax(0, 1fr); }}
    }}

    /* Trilha dos sete passos — sem trilho nem seta; a ordem é a numeração. */
    .ea-passos {{ list-style: none; margin: 0; padding: .45rem 0 0;
      display: flex; flex-direction: column; gap: .95rem;
      /* As curvas de nível do canto passam por trás da lista: um véu do papel,
         de borda esfumada, apaga as linhas sob o texto sem desenhar caixa. */
      background: rgba(243,242,234,.88); border-radius: 18px;
      box-shadow: 0 0 22px 20px rgba(243,242,234,.88); }}
    .ea-passo {{ display: flex; align-items: baseline; gap: .75rem; }}
    .ea-passo .n {{ color: var(--oliva-escuro); font-weight: 600; font-size: 1.1rem;
      font-variant-numeric: tabular-nums; min-width: .8rem; }}
    .ea-passo .t {{ color: var(--tinta); font-weight: 600; font-size: .95rem; }}
    .ea-passo .d {{ color: var(--tinta); font-size: .92rem; }}
    @media (max-width: 860px) {{
      .ea-passos {{ padding: 0; gap: .6rem; background: none; box-shadow: none; }}
      .ea-passo .n {{ font-size: 1rem; }}
    }}

    /* Painel do envio: superfície elevada por tom (não por contraste de linha),
       sombra curta e direcional tingida de verde, e UM canto chanfrado (geometria
       própria). O conteúdo tem folga para não encostar no corte. */
    .ea-painel {{
      background: var(--papel-alto);
      border: 1px solid var(--linha);
      border-radius: 16px;
      clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%);
      padding: clamp(1.5rem, 4vw, 1.9rem);
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,.75),
        0 14px 30px -22px rgba(14,58,38,.6);
      display: flex; flex-direction: column; gap: .8rem;
    }}

    /* Aviso de privacidade: ilha recuada, com folga em todos os lados — objeto
       deliberado, não uma barra de acento colada na borda. */
    .ea-privacidade {{
      background: var(--papel-alto);
      border: 1px solid var(--linha);
      border-radius: 13px;
      padding: 1rem 1.15rem;
      display: flex; flex-direction: column; gap: .3rem;
    }}
    .ea-priv-titulo {{ color: var(--tinta); font-weight: 600; font-size: .95rem; }}
    .ea-priv-texto {{ color: var(--cinza); font-size: .85rem; line-height: 1.5; }}

    .ea-rodape {{ margin-top: 2.6rem; padding-top: 1.1rem;
      border-top: 1px solid var(--linha); color: var(--cinza);
      font-size: .8rem; line-height: 1.5; max-width: 620px; }}
    .ea-rodape b {{ color: var(--tinta); font-weight: 600; }}
    .ea-rodape-direitos {{ margin-top: .45rem; font-size: .75rem; }}

    /* --- Fluxo de análise: mapear → analisar → resultados → relatório -------- */
    /* Itens flexíveis crescem até o conteúdo por padrão (min-width: auto): uma
       tabela larga empurrava a coluna inteira para fora da tela no celular.
       Com min-width: 0 a coluna fica na largura da tela e a tabela rola por
       dentro. */
    .ea-main > *, .ea-analise > *, .ea-slot > *, .ea-resultado > *,
    .ea-paineis, .ea-paineis .q-tab-panel, .ea-painel-aba > * {{
      min-width: 0; max-width: 100%; }}
    .ensaia-previa {{ max-width: 100%; }}
    .ensaia-previa .q-table__middle {{ overflow-x: auto; }}
    .ea-analise {{ display: flex; flex-direction: column; gap: 1.6rem; }}
    .ea-analise:empty {{ display: none; }}
    .ea-slot:empty {{ display: none; }}
    .ea-secao-titulo {{ font-family: var(--fonte-titulo); font-weight: 600;
      font-size: 1.5rem; color: var(--tinta); }}
    .ea-secao-sub {{ color: var(--cinza); font-size: .9rem; line-height: 1.5; }}
    .ea-secao-sub b {{ color: var(--tinta); font-weight: 600; }}

    .ea-mapear {{ display: flex; flex-direction: column; gap: .7rem;
      width: 100%; }}
    .ea-mapa-grade {{ display: grid; gap: .7rem 1rem;
      grid-template-columns: repeat(auto-fit, minmax(205px, 1fr)); }}
    .ea-mapa-item {{ display: flex; flex-direction: column; gap: .25rem; }}
    .ea-col-nome {{ font-weight: 600; font-size: .85rem; color: var(--tinta);
      overflow-wrap: anywhere; }}

    /* Mapear colunas por arrastar e soltar: dois grupos principais (resposta e
       fator) e, abaixo, dois menores (ordem e não usar). */
    .ea-quadro {{ display: grid; gap: .8rem 1rem;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }}
    .ea-zona {{ display: flex; flex-direction: column; gap: .55rem;
      padding: .8rem .85rem; min-height: 9.5rem;
      background: rgba(29,29,27,.035);
      border: 1px solid rgba(29,29,27,.16); border-radius: 13px;
      transition: background .12s, border-color .12s; }}
    /* Lâmpada de dica: discreta até o mouse (ou o foco) chegar nela. */
    .ea-dica {{ color: var(--oliva); opacity: .55; font-size: 1.05rem;
      cursor: help; align-self: center; transition: opacity .12s; }}
    .ea-dica:hover, .ea-dica:focus-visible {{ opacity: 1; outline: none; }}
    .ea-dica-pop {{ background: var(--tinta); color: var(--papel);
      font-size: .8rem; line-height: 1.45; max-width: 260px;
      padding: .5rem .7rem; border-radius: 8px; }}
    /* Modos de dica (classe no body, escolhida no seletor da abertura). */
    body.ea-dicas-nenhuma .ea-dica,
    body.ea-dicas-nenhuma .ea-ajuda {{ display: none !important; }}
    .ea-dica-form {{ display: none; }}
    body.ea-dicas-formula .ea-dica-com-formula .ea-dica-txt {{ display: none; }}
    body.ea-dicas-formula .ea-dica-com-formula .ea-dica-form {{ display: block; }}
    .ea-dica-form {{ white-space: pre-line; font-size: .86rem; line-height: 1.6;
      font-family: var(--fonte-corpo); font-variant-numeric: tabular-nums; }}
    .ea-ajuda-pop .ea-dica-form {{ color: var(--tinta); }}
    body.ea-dicas-formula .ea-dica-pop.ea-dica-com-formula {{ max-width: 380px; }}
    .ea-zona-menor {{ min-height: 0; padding: .6rem .85rem; }}
    .ea-zona-alvo {{ background: rgba(64,165,81,.10); border-color: var(--verde); }}
    .ea-zona-topo {{ display: flex; justify-content: space-between;
      align-items: flex-start; gap: .5rem; }}
    .ea-zona-titulo {{ font-weight: 600; font-size: .92rem; color: var(--tinta); }}
    .ea-zona-menor .ea-zona-titulo {{ font-size: .84rem; color: var(--cinza); }}
    .ea-zona-soltar {{ display: flex; flex-direction: column; align-items: center;
      color: var(--cinza); font-size: .62rem; line-height: 1.1; flex-shrink: 0; }}
    .ea-zona-soltar .q-icon {{ font-size: 1.25rem; }}
    .ea-zona-menor .ea-zona-soltar {{ display: none; }}
    .ea-zona-lista {{ display: flex; flex-direction: column; gap: .45rem;
      flex: 1; }}
    .ea-zona-menor .ea-zona-lista {{ flex-direction: row; flex-wrap: wrap; }}
    /* Grupo vazio: um espaço tracejado onde a coluna cabe, com o aviso no meio. */
    .ea-zona-vazia {{ flex: 1; width: 100%; display: flex; align-items: center;
      justify-content: center; min-height: 2.6rem; padding: .5rem;
      border: 1.5px dashed rgba(29,29,27,.22); border-radius: 9px;
      color: var(--cinza); font-size: .85rem; text-align: center; }}
    .ea-cartao {{ display: flex; align-items: center; gap: .45rem;
      padding: .45rem .7rem .45rem .45rem; min-width: 0;
      background: rgba(29,29,27,.06); border: 1px solid rgba(29,29,27,.22);
      border-radius: 9px; cursor: grab; user-select: none;
      color: var(--tinta); font-size: .9rem; }}
    .ea-cartao:hover {{ background: rgba(29,29,27,.09); }}
    .ea-cartao:focus-visible {{ outline: 2px solid var(--verde);
      outline-offset: 2px; }}
    .ea-cartao:active {{ cursor: grabbing; }}
    .ea-arrastando {{ opacity: .45; }}
    .ea-cartao-alca {{ color: var(--cinza); font-size: 1.15rem; flex-shrink: 0; }}
    .ea-cartao-nome {{ overflow-wrap: anywhere; min-width: 0; }}
    .ea-cartao-fixo {{ cursor: default; opacity: .7; background: transparent; }}
    .ea-cartao-fixo:hover {{ background: transparent; }}
    /* Análises: título de seção e uma etapa por dropdown, com os cartões. */
    .ea-analises {{ display: flex; flex-direction: column; gap: .55rem;
      width: 100%; }}
    .ea-etapa {{ border: 1px solid rgba(29,29,27,.14); border-radius: 12px;
      background: transparent; }}
    .ea-etapa .q-expansion-item__container > .q-item {{ padding: .55rem .8rem;
      border-radius: 12px; min-height: 0; }}
    .ea-etapa .q-focus-helper {{ display: none; }}
    .ea-etapa .q-expansion-item__content {{ display: flex; flex-direction: column;
      gap: .75rem; padding: .2rem .85rem .85rem; }}
    .ea-etapa-cabeca {{ display: flex; align-items: center; gap: .7rem;
      flex: 1; min-width: 0; }}
    .ea-etapa-num {{ width: 1.6rem; height: 1.6rem; border-radius: 50%;
      flex-shrink: 0; display: flex; align-items: center; justify-content: center;
      font-size: .78rem; font-weight: 700; color: var(--papel);
      background: var(--verde-escuro); }}
    .ea-etapa-textos {{ display: flex; flex-direction: column; min-width: 0;
      flex: 1; }}
    .ea-etapa-nome {{ font-weight: 600; font-size: .95rem; color: var(--tinta); }}
    .ea-etapa-pergunta {{ font-size: .82rem; color: var(--cinza); }}
    .ea-etapa-conta {{ flex-shrink: 0; font-size: .75rem; color: var(--cinza);
      font-variant-numeric: tabular-nums; }}
    .ea-analise-grade {{ display: grid; gap: .6rem; width: 100%;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); }}
    .ea-analise-cartao {{ display: flex; flex-direction: column; gap: .3rem;
      padding: .7rem .8rem; border-radius: 11px; cursor: pointer;
      border: 1px solid rgba(29,29,27,.16); background: transparent;
      user-select: none; transition: background .12s, border-color .12s; }}
    .ea-analise-cartao:focus-visible {{ outline: 2px solid var(--verde);
      outline-offset: 2px; }}
    .ea-analise-on {{ border-color: rgba(46,133,64,.55);
      background: rgba(64,165,81,.08); }}
    .ea-analise-off:hover {{ background: rgba(29,29,27,.04); }}
    .ea-analise-na {{ cursor: default; opacity: .62; background: transparent;
      border-style: dashed; }}
    .ea-analise-topo {{ display: flex; align-items: center; gap: .4rem; }}
    .ea-analise-nome {{ font-weight: 600; font-size: .9rem; color: var(--tinta); }}
    .ea-analise-selo {{ margin-left: auto; flex-shrink: 0; font-size: .7rem;
      font-weight: 600; padding: .1rem .5rem; border-radius: 999px;
      border: 1px solid rgba(29,29,27,.22); color: var(--cinza); }}
    .ea-analise-on .ea-analise-selo {{ background: var(--verde-escuro);
      border-color: var(--verde-escuro); color: var(--papel); }}
    .ea-analise-texto {{ font-size: .82rem; color: var(--cinza); line-height: 1.45; }}
    .ea-analise-motivo {{ font-size: .78rem; color: var(--oliva-escuro);
      line-height: 1.4; }}
    .ea-cartao-menu-titulo {{ font-size: .75rem; font-weight: 600;
      color: var(--cinza); padding: .5rem 1rem .2rem; }}

    /* Um primário cheio (verde-mata) e uma ação secundária discreta em texto —
       nunca o par cheio+contorno. Sem salto no hover, só mudança de tom. */
    .ea-botao.q-btn {{ background: var(--verde-escuro) !important;
      color: var(--papel); border-radius: 11px; font-weight: 600;
      text-transform: none; letter-spacing: 0; padding: .5rem 1.15rem; }}
    .ea-botao.q-btn:hover {{ filter: brightness(1.14); }}
    .ea-botao-sec.q-btn {{ color: var(--verde-escuro); text-transform: none;
      letter-spacing: 0; font-weight: 600; }}
    /* Sem a caixa cinza do Quasar no foco/clique; o retorno é só de tom. */
    .ea-botao-sec .q-focus-helper {{ display: none; }}
    .ea-botao-sec.q-btn:hover {{ color: var(--tinta); }}
    .ea-acoes {{ display: flex; flex-wrap: wrap; gap: .3rem 1rem;
      align-items: center; }}
    /* Passo final do fluxo: separado das ações de texto por espaço, não por
       linha nem caixa. */
    .ea-baixar {{ display: flex; flex-direction: column; gap: .5rem;
      margin-top: .9rem; }}

    .ea-resultado {{ display: flex; flex-direction: column; gap: .7rem;
      padding: 1.1rem 1.15rem; background: var(--papel-alto);
      border: 1px solid var(--linha); border-radius: 14px; }}
    .ea-resp-nome {{ font-family: var(--fonte-titulo); font-weight: 600;
      font-size: 1.15rem; color: var(--tinta); }}
    .ea-r2 {{ font-size: 1rem; color: var(--cinza); }}
    .ea-r2 b {{ color: var(--verde-escuro); font-variant-numeric: tabular-nums; }}
    .ea-falta {{ font-size: .88rem; color: var(--cinza); line-height: 1.5; }}
    .ea-aviso {{ font-size: .82rem; color: var(--oliva-escuro); line-height: 1.45; }}
    .ea-tabela-rotulo {{ font-size: .8rem; font-weight: 600; color: var(--cinza);
      margin-top: .15rem; }}

    /* Abas por resposta: rótulo em caixa normal (sem o caps do Quasar), o
       indicador deslizante do próprio Quasar marca a aba ativa. */
    .ea-abas {{ color: var(--cinza); border-bottom: 1px solid var(--linha); }}
    .ea-abas .q-tabs__content {{ justify-content: flex-start; }}
    .ea-abas .q-tab {{ flex: 0 0 auto; }}
    /* O realce cinza do Quasar no clique vira caixa atrás do rótulo: fora. */
    .ea-abas .q-focus-helper {{ display: none; }}
    .ea-abas .q-tab:hover .q-tab__label {{ color: var(--tinta); }}
    .ea-abas .q-tab {{ padding: 0 .9rem 0 0; min-height: 40px; }}
    .ea-abas .q-tab__label {{ font-weight: 600; font-size: .9rem;
      letter-spacing: 0; }}
    .ea-paineis {{ background: transparent; }}
    .ea-paineis .q-tab-panel {{ padding: 1rem 0 0 0; }}
    .ea-painel-aba {{ gap: .55rem; }}

    /* Gráfico + uma linha de "como ler" logo abaixo (US-16): curta, nunca um
       parágrafo. */
    .ea-grafico {{ width: 100%; }}
    .ea-grafico-titulo {{ font-weight: 600; font-size: .92rem; color: var(--tinta);
      margin-top: .35rem; }}
    .ea-ler {{ font-size: .82rem; color: var(--cinza); line-height: 1.5;
      max-width: 34rem; }}
    .ea-ler b {{ color: var(--tinta); font-weight: 600; }}
    .ea-controles {{ display: flex; flex-wrap: wrap; gap: .6rem 1rem;
      align-items: flex-end; }}
    .ea-controles .q-field {{ min-width: 150px; }}
    .ea-painel .ea-controles .q-field {{ min-width: 13rem; }}
    .ea-forma {{ border: 1px solid var(--linha); border-radius: 10px; }}
    /* Opções do modelo: recolhidas, sem caixa; o cabeçalho fala baixo. */
    .ea-opcoes {{ color: var(--cinza); }}
    .ea-opcoes .q-focus-helper {{ display: none; }}
    .ea-opcoes .q-item {{ padding-left: 0; min-height: 36px; }}
    /* Prévia dos dados: 5 linhas por página, sem o seletor de linhas por página;
       embaixo, o arquivo e o tamanho e, discreta, a linha de como foi lido. */
    .ea-previa-dados .q-table__bottom .q-table__select {{ display: none; }}
    .ea-previa-info {{ display: flex; flex-wrap: wrap; align-items: baseline;
      gap: .1rem .7rem; margin-top: .1rem; }}
    .ea-previa-nome {{ color: var(--tinta); font-weight: 600; font-size: .95rem;
      overflow-wrap: anywhere; }}
    .ea-previa-tamanho {{ color: var(--verde-escuro); font-weight: 600;
      font-size: .85rem; }}
    .ea-formato {{ display: flex; flex-wrap: wrap; align-items: center;
      justify-content: space-between; gap: .4rem .8rem; width: 100%;
      color: var(--cinza); font-size: .8rem; }}
    .ea-formato b {{ color: var(--tinta); font-weight: 600; }}
    .ea-formato-trocar.q-btn {{ margin-left: auto; border-radius: 9px;
      color: var(--verde-escuro); font-size: .8rem; font-weight: 600;
      padding: .15rem .7rem; }}
    .ea-formato-atual {{ font-weight: 700; color: var(--verde-escuro); }}
    .ea-formato-dica {{ color: var(--cinza); font-size: .78rem; }}
    .ea-opcoes .q-item__label {{ font-weight: 600; font-size: .9rem; }}
    .ea-opcoes .q-expansion-item__content {{ display: flex; flex-direction: column;
      gap: .55rem; padding: .35rem 0 .6rem; }}
    .ea-ajustar {{ margin: .2rem 0 .4rem; }}
    /* Exemplos e planilha-modelo abaixo da dropzone: rótulo e ações lado a lado. */
    .ea-alternativas {{ display: grid; grid-template-columns: auto 1fr;
      gap: .15rem 1.1rem; align-items: baseline; margin-top: .3rem; }}
    .ea-alternativas .ea-acoes {{ gap: 0 1.1rem; }}
    /* Ações como texto: a primeira letra alinha com a coluna, sem recuo. */
    .ea-alternativas .ea-botao-sec.q-btn {{ padding: 0; min-height: 1.9rem; }}
    .ea-alternativas .ea-botao-sec .q-btn__content {{ justify-content: flex-start;
      text-align: left; }}
    @media (max-width: 560px) {{
      .ea-alternativas {{ grid-template-columns: 1fr; }}
      .ea-alternativas > .ea-ler:not(:first-child) {{ margin-top: .5rem; }}
    }}
    /* Catálogo de análises: um bloco por grupo da spec, lado a lado. */
    .ea-grupos {{ display: grid; gap: .9rem 1.4rem; width: 100%;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); }}
    .ea-grupo {{ display: flex; flex-direction: column; gap: .1rem; }}
    .ea-grupo-titulo {{ font-weight: 600; font-size: .85rem; color: var(--tinta);
      margin-bottom: .15rem; }}
    .ea-grupo .q-checkbox__label {{ font-size: .85rem; color: var(--tinta); }}
    .ea-grupo .q-checkbox.disabled .q-checkbox__label {{ color: var(--cinza); }}
    /* Pequenos múltiplos (efeitos principais): mesma escala, lado a lado. */
    .ea-multiplos {{ display: grid; gap: .25rem .75rem; width: 100%;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }}
    .ea-multiplos > * {{ min-width: 0; }}
    .ea-fora {{ min-width: 260px; flex: 1; max-width: 520px; }}
    /* Equação: texto de dado, em tinta, quebrando onde precisar. */
    .ea-equacao {{ font-size: .95rem; line-height: 1.65; color: var(--tinta);
      overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }}
    .ea-forma .q-btn {{ border-radius: 9px; font-weight: 600; letter-spacing: 0;
      padding: .25rem .8rem; }}
    .ea-fixo {{ display: flex; flex-direction: column; gap: .1rem;
      min-width: 210px; flex: 1; }}
    .ea-fixo-rotulo {{ font-size: .8rem; color: var(--cinza); }}
    .ea-fixo-rotulo b {{ color: var(--tinta); font-variant-numeric: tabular-nums; }}

    .ea-relatorio {{ display: flex; flex-direction: column; gap: 1rem; }}
    .ea-rel-secao {{ display: flex; flex-direction: column; gap: .3rem; }}
    .ea-rel-titulo {{ font-family: var(--fonte-titulo); font-weight: 600;
      font-size: 1.1rem; color: var(--tinta); }}
    .ea-rel-texto {{ color: var(--tinta); font-size: .98rem; line-height: 1.6;
      white-space: pre-line; overflow-wrap: anywhere; }}
    /* Conferência dos números (spec §12.5): o que não bate fica em amarelo,
       um tom claro do oliva da Ufra, com a tinta por cima (contraste alto). */
    .ea-destaque-fid {{ background: #F1E7A3; color: var(--tinta); border-radius: 3px;
      padding: 0 .15em; }}
    .ea-conferido {{ font-size: .9rem; font-weight: 600; color: var(--verde-escuro); }}
    .ea-nao-conferido {{ font-size: .9rem; font-weight: 600;
      color: var(--oliva-escuro); }}
    /* Pedido do modo M1: texto para copiar, rolável, na fonte do corpo. */
    .ea-pedido {{ white-space: pre-wrap; font-size: .82rem; line-height: 1.5;
      color: var(--cinza); max-height: 18rem; overflow-y: auto; width: 100%;
      background: var(--papel); border-radius: 10px; padding: .7rem .9rem; }}
    .ea-colar {{ width: 100%; }}
    .ea-campo-longo {{ min-width: 16rem; max-width: 100%; }}
    .ea-link {{ color: var(--verde-escuro); font-weight: 600; font-size: .85rem; }}
    /* "o que é?" (US-16): ajuda como texto pontilhado, não ícone em caixa. */
    .ea-titulo-linha {{ display: flex; flex-wrap: wrap; align-items: baseline;
      gap: .1rem .6rem; }}
    .ea-ajuda.q-btn {{ color: var(--cinza); font-size: .75rem; font-weight: 500;
      padding: 0 .1rem; min-height: 1.2rem; text-transform: none; letter-spacing: 0;
      text-decoration: underline dotted; text-underline-offset: 3px; }}
    .ea-ajuda .q-focus-helper {{ display: none; }}
    .ea-ajuda.q-btn:hover {{ color: var(--tinta); }}
    .ea-ajuda-pop {{ max-width: 22rem; padding: .75rem .95rem;
      background: var(--papel-alto); border-radius: 10px; }}
    .ea-ajuda-titulo {{ font-family: var(--fonte-titulo); font-weight: 600;
      color: var(--tinta); font-size: .98rem; margin-bottom: .2rem; }}
    .ea-ajuda-texto {{ color: var(--tinta); font-size: .85rem; line-height: 1.5; }}
    /* Indicativos (US-06): o valor em destaque e o sinal como palavra colorida. */
    .ea-indicativos {{ display: grid; gap: .9rem 1.6rem; margin: .5rem 0 .9rem;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }}
    .ea-ind {{ display: flex; flex-direction: column; gap: .1rem; min-width: 0; }}
    .ea-ind-rotulo {{ display: flex; flex-wrap: wrap; align-items: baseline;
      gap: 0 .4rem; font-size: .8rem; color: var(--cinza); }}
    .ea-ind-valor {{ font-family: var(--fonte-titulo); font-size: 1.45rem;
      color: var(--tinta); font-variant-numeric: tabular-nums; line-height: 1.2; }}
    .ea-ind-sit {{ font-size: .78rem; font-weight: 700; }}
    .ea-ind-ok .ea-ind-sit {{ color: var(--verde-escuro); }}
    .ea-ind-atencao .ea-ind-sit {{ color: var(--oliva-escuro); }}
    .ea-ind-atencao .ea-ind-valor {{ color: var(--oliva-escuro); }}
    .ea-ind-leitura {{ font-size: .78rem; color: var(--cinza); line-height: 1.4; }}
    /* Próximos passos (US-17): frases curtas, uma por linha. */
    .ea-passos-sugeridos {{ display: flex; flex-direction: column; gap: .45rem;
      max-width: 44rem; }}
    .ea-passo-sugerido {{ color: var(--tinta); font-size: .95rem; line-height: 1.5; }}
    /* Glossário (US-18): janela de leitura, largura de texto. */
    .ea-glossario {{ width: min(44rem, 94vw); max-height: 86vh;
      background: var(--papel-alto); border-radius: 14px; }}
    .ea-glossario-texto {{ max-height: 62vh; overflow-y: auto;
      background: transparent; }}
    .ea-glossario-texto h1 {{ font-family: var(--fonte-titulo); font-size: 1.3rem;
      margin: 0 0 .6rem; }}
    .ea-glossario-texto h2 {{ font-family: var(--fonte-titulo); font-size: 1.05rem;
      margin: .9rem 0 .3rem; }}
    .ea-glossario-texto p {{ font-size: .9rem; line-height: 1.55; margin: 0 0 .55rem; }}
    .ea-glossario-link.q-btn {{ align-self: flex-start; padding-left: 0; }}
    .ea-link:hover {{ color: var(--tinta); }}
    /* Tag como texto, não chip: evita o pill e a caixa-atrás-do-rótulo. */
    .ea-tag-ia {{ font-size: .7rem; font-weight: 700; color: var(--verde-escuro); }}
    .ea-tag-m0 {{ font-size: .7rem; font-weight: 700; color: var(--cinza); }}
    .ea-spinner {{ color: var(--verde-escuro) !important; }}

    /* O ponto ótimo da superfície respira — decorativo, nunca esconde conteúdo. */
    @keyframes ea-respira {{
      0%, 100% {{ transform: scale(1); opacity: .9; }}
      50%      {{ transform: scale(1.14); opacity: .55; }}
    }}
    .ea-otimo-halo {{ transform-box: fill-box; transform-origin: center;
                      animation: ea-respira 4.8s ease-in-out infinite; }}
    .ea-superficie {{ animation: ea-deriva 26s ease-in-out infinite; }}
    @keyframes ea-deriva {{
      0%, 100% {{ transform: translate3d(0,0,0); }}
      50%      {{ transform: translate3d(-10px,8px,0); }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .ea-otimo-halo, .ea-superficie {{ animation: none; }}
    }}
    </style>
    """


def aplicar_tema() -> None:
    """Aplica a paleta da marca ao Quasar e injeta o CSS da identidade.

    Chamada no início de cada página, antes de montar os elementos.
    """
    ui.colors(
        primary=VERDE_ESCURO,
        secondary=TINTA,
        accent=VERDE,
        positive=VERDE,
    )
    ui.add_head_html(_css())
