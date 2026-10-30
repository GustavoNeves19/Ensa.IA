"""Identidade visual da interface: cores da UFRA, fontes IBM Plex e todo o CSS.
Trocar a marca da tela é mexer só aqui.
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

# Cores dos gráficos (validadas para daltonismo e contraste).
SERIE = "#2E8540"  # marca principal: termo significativo, ensaios
SERIE_APAGADA = "#968F7A"  # cinza quente de ênfase: termo não significativo
REFERENCIA = CINZA  # linhas de referência (y = x, zero, t crítico, reta do Q-Q)
GRADE = "#E7E4D8"  # linhas de grade: um passo fora da superfície, recessivas
# Rampa sequencial (claro → escuro) da superfície e do contorno: maior = mais escuro.
RAMPA = ["#8FBD7D", "#6FA96A", "#529257", "#3B7B47", "#28643A", "#1A4E2D", "#0E3A26"]

_STATIC = Path(__file__).parent / "static"
# Rota das fontes, servida uma vez e sem CDN.
with contextlib.suppress(Exception):
    app.add_static_files("/ensaia-static", str(_STATIC))

# Grão leve no fundo, atrás do conteúdo.
_GRAO = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/></svg>"  # noqa: E501


# Recortes do IBM Plex e seus intervalos Unicode.
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
    """Regras @font-face das fontes servidas pelo pacote."""
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
    """Folha de estilo da interface."""
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
    .ea-page {{ position: relative; width: 100%; min-height: 100vh; }}
    .ea-col {{
      position: relative; z-index: 1; max-width: 1080px; margin: 0 auto;
      padding: clamp(2.6rem, 6vw, 5.5rem) clamp(1.25rem, 5vw, 2.25rem) 3.25rem;
    }}
    /* O conteúdo ocupa a coluna centralizada inteira (até 1080px), alinhado à
       abertura: no computador, a página fica no meio, com margens iguais. Os
       textos corridos têm largura própria limitada, para a leitura não cansar. */
    .ea-main {{
      width: 100%; display: flex; flex-direction: column;
      gap: clamp(1.9rem, 4vw, 2.7rem);
    }}

    /* Marca e títulos. */
    .ea-marca {{ font-family: var(--fonte-titulo); font-weight: 600;
      font-size: clamp(3.6rem, 12vw, 5.4rem); line-height: .95;
      letter-spacing: -0.015em; }}

    /* Seletor de dicas, depois do subtítulo: três degraus com os nomes embaixo.
       A folga lateral evita que o primeiro e o último nome saiam da caixa. */
    .ea-seletor-dicas {{ width: min(100%, 380px); }}
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

    /* Abertura em duas colunas: o texto (marca, título, subtítulo e o seletor
       de dicas) à esquerda e a linha do tempo dos passos à direita. Em tela
       estreita, os passos descem para baixo do texto. */
    .ea-abertura {{ display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 22rem);
      align-items: center; column-gap: clamp(2rem, 5vw, 4rem);
      row-gap: clamp(2.3rem, 5vw, 3.4rem);
      margin-bottom: clamp(2.3rem, 5vw, 3.4rem); }}
    @media (max-width: 860px) {{
      .ea-abertura {{ grid-template-columns: minmax(0, 1fr); }}
    }}
    .ea-hero {{ display: flex; flex-direction: column;
      gap: clamp(1.9rem, 4vw, 2.7rem); max-width: 42rem; }}

    /* Linha do tempo dos três passos, um embaixo do outro, sem trilho ligando
       os círculos — só o número gigante e esmaecido atrás do texto marca a
       ordem. Cada passo tem sua própria cor (`--cor`, inline de `_cor_passo`
       em home.py), interpolando verde-escuro → oliva-escuro. */
    .ea-passos {{ position: relative; list-style: none; margin: 0;
      padding: .5rem 0; display: flex; flex-direction: column; gap: 1.8rem; }}
    .ea-passo {{ position: relative; display: flex; align-items: center;
      gap: 1.3rem; }}

    .ea-passo-circulo {{ position: relative; z-index: 1; flex-shrink: 0;
      width: 4.2rem; height: 4.2rem; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      background: var(--cor);
      box-shadow: 0 10px 18px -8px rgba(29,29,27,.4),
        0 0 0 5px var(--papel); }}
    .ea-passo-circulo .material-icons {{ color: var(--papel);
      font-size: 1.9rem; }}

    .ea-passo-corpo {{ position: relative; z-index: 1; min-width: 0; flex: 1; }}
    .ea-passo .t {{ display: block; color: var(--tinta); font-weight: 700;
      font-size: 1.05rem; }}
    .ea-passo .d {{ color: var(--cinza); font-size: .9rem; line-height: 1.4; }}

    /* O número gigante e esmaecido atrás do texto — a assinatura visual da
       página, ligada a cada passo. */
    .ea-passo-num {{ position: absolute; z-index: 0; top: 50%; right: .3rem;
      transform: translateY(-50%); font-size: 3.8rem; font-weight: 800;
      color: var(--cor); opacity: .14; line-height: 1;
      font-variant-numeric: tabular-nums; pointer-events: none; }}

    @media (max-width: 480px) {{
      .ea-passo-num {{ font-size: 2.8rem; }}
      .ea-passo-circulo {{ width: 3.6rem; height: 3.6rem; }}
      .ea-passo-circulo .material-icons {{ font-size: 1.6rem; }}
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

    /* Mapear colunas por arrastar e soltar: os três grupos (resposta, fator,
       não usar) lado a lado, na mesma fileira. A ordem de execução não tem
       grupo nem tela: só entra quando detectada de uma coluna da planilha
       (informá-la é problema de quem roda o experimento, não do EnsaIA). */
    /* Quatro zonas (respostas, fatores, blocos, não usar): 2 × 2. */
    .ea-quadro {{ display: grid; gap: .8rem 1rem;
      grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    @media (max-width: 760px) {{
      .ea-quadro {{ grid-template-columns: minmax(0, 1fr); }}
    }}
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
    body.ea-dicas-nenhuma .ea-dica {{ display: none !important; }}
    .ea-dica-form {{ display: none; }}
    body.ea-dicas-formula .ea-dica-com-formula .ea-dica-txt {{ display: none; }}
    body.ea-dicas-formula .ea-dica-com-formula .ea-dica-form {{ display: block; }}
    .ea-dica-form {{ white-space: pre-line; font-size: .86rem; line-height: 1.6;
      font-family: var(--fonte-corpo); font-variant-numeric: tabular-nums; }}
    body.ea-dicas-formula .ea-dica-pop.ea-dica-com-formula {{ max-width: 380px; }}
    .ea-zona-alvo {{ background: rgba(64,165,81,.10); border-color: var(--verde); }}
    .ea-zona-topo {{ display: flex; align-items: center; gap: .4rem; }}
    .ea-zona-titulo {{ font-weight: 600; font-size: .92rem; color: var(--tinta); }}
    .ea-zona-lista {{ display: flex; flex-direction: column; gap: .45rem;
      flex: 1; }}
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
    .ea-analise-topo {{ display: flex; align-items: flex-start; gap: .4rem; }}
    .ea-analise-nome {{ font-weight: 600; font-size: .9rem; color: var(--tinta); }}
    /* A lâmpada vai para o canto superior direito do cartão. */
    .ea-analise-topo .ea-dica {{ margin-left: auto; flex-shrink: 0;
      align-self: flex-start; margin-top: .1rem; }}
    /* Opções do modelo: o mesmo card recolhível das etapas, com um ícone no
       lugar do número e a escolha atual no subtítulo. Os cartões de opção não
       são clicáveis: o controle fica dentro deles. */
    .ea-etapa-icone {{ font-size: 1rem; }}
    .ea-opcao-cartao {{ display: flex; flex-direction: column; gap: .45rem;
      padding: .7rem .8rem; border-radius: 11px;
      border: 1px solid rgba(29,29,27,.16); background: var(--papel-alto); }}
    .ea-opcao-larga {{ grid-column: 1 / -1; }}
    .ea-opcao-cartao .ea-forma {{ align-self: flex-start; flex-wrap: wrap; }}
    .ea-opcao-cartao .q-toggle__label {{ font-size: .88rem; color: var(--tinta); }}
    /* Embaixo dos cartões, à esquerda: incluir ou tirar todas da etapa. */
    .ea-etapa-todas.q-btn {{ align-self: flex-start; border-radius: 9px;
      color: var(--verde-escuro); font-size: .8rem; font-weight: 600;
      padding: .15rem .7rem; }}
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
    /* Os blocos da análise ocupam a coluna inteira. Sem isso, o contêiner de
       coluna da NiceGUI encolhe cada bloco até o tamanho do conteúdo: ao trocar
       de aba (ANOVA, Diagnóstico) o quadro estreitava e saía do centro. */
    .ea-resultado, .ea-otimizacao, .ea-relatorio, .ea-baixar {{ width: 100%; }}
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
    /* Legendas de gráficos e tabelas acompanham a largura do que descrevem. */
    .ea-resultado .ea-ler, .ea-card .ea-ler, .ea-otimo-resultado .ea-ler {{
      max-width: none; }}
    .ea-controles {{ display: flex; flex-wrap: wrap; gap: .6rem 1rem;
      align-items: flex-end; }}
    .ea-controles .q-field {{ min-width: 150px; }}
    .ea-painel .ea-controles .q-field {{ min-width: 13rem; }}
    .ea-forma {{ border: 1px solid var(--linha); border-radius: 10px; }}
    /* Opções do modelo: recolhidas, sem caixa; o cabeçalho fala baixo. */
    .ea-opcoes {{ color: var(--cinza); }}
    .ea-opcoes .q-focus-helper {{ display: none; }}
    .ea-opcoes .q-item {{ padding-left: 0; min-height: 36px; }}
    .ea-opcoes .q-item__label {{ font-weight: 600; font-size: .9rem; }}
    .ea-opcoes .q-expansion-item__content {{ display: flex; flex-direction: column;
      gap: .55rem; padding: .35rem 0 .6rem; }}
    /* Exemplos e planilha-modelo abaixo da dropzone: rótulo e ações lado a lado. */
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
    .ea-formato-texto {{ margin-left: auto; text-align: right; }}
    .ea-formato-trocar.q-btn {{ border-radius: 9px;
      color: var(--verde-escuro); font-size: .8rem; font-weight: 600;
      padding: .15rem .7rem; }}
    .ea-formato-atual {{ font-weight: 700; color: var(--verde-escuro); }}
    .ea-formato-dica {{ color: var(--cinza); font-size: .78rem; }}
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
    /* Equação do modelo: um termo por peça (sinal, coeficiente, variável), que
       quebra de linha entre termos e nunca no meio de um; as formas em botões,
       as variáveis como etiquetas e o copiar ao lado. */
    .ea-eq-bloco {{ display: flex; flex-direction: column; gap: .55rem;
      width: 100%; }}
    .ea-eq-barra {{ display: flex; flex-wrap: wrap; align-items: center;
      gap: .5rem .8rem; }}
    .ea-eq-forma {{ display: flex; flex-direction: column; gap: .45rem; }}
    .ea-eq-barra .ea-forma {{ flex-wrap: wrap; }}
    .ea-eq-barra .ea-forma .q-btn {{ white-space: nowrap; }}
    .ea-eq {{ display: flex; flex-wrap: wrap; align-items: baseline;
      gap: .4rem .45rem; padding: .8rem .9rem; border-radius: 11px;
      background: rgba(29,29,27,.035); border: 1px solid var(--linha);
      font-variant-numeric: tabular-nums; }}
    .ea-eq-y {{ font-family: var(--fonte-titulo); font-size: 1.15rem;
      font-weight: 600; color: var(--tinta); margin-right: .15rem; }}
    .ea-eq-termo {{ display: inline-flex; align-items: baseline; gap: .3rem;
      padding: .15rem .5rem; border-radius: 7px; background: var(--papel-alto);
      border: 1px solid rgba(29,29,27,.1); font-size: .92rem; }}
    .ea-eq-sinal {{ color: var(--cinza); font-weight: 600; }}
    .ea-eq-coef {{ color: var(--tinta); font-weight: 600; white-space: nowrap; }}
    .ea-eq-var {{ color: var(--verde-escuro); overflow-wrap: anywhere; }}
    .ea-eq-vars {{ display: flex; flex-wrap: wrap; gap: .35rem; }}
    .ea-eq-varchip {{ font-size: .78rem; color: var(--tinta); padding: .1rem .55rem;
      border-radius: 999px; border: 1px solid rgba(29,29,27,.18); }}
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
    /* Título com lâmpada de dica ao lado (US-16). */
    .ea-titulo-linha {{ display: flex; flex-wrap: wrap; align-items: baseline;
      gap: .1rem .6rem; }}
    .ea-titulo-dica {{ align-items: center; gap: .1rem .45rem; }}
    /* Indicativos (US-06): só leitura, como um quadro de relatório. Sem caixa,
       sem clique: cada métrica fica numa célula separada por uma linha fina em
       cima. O sinal é um ícone ao lado do valor; a lâmpada explica a métrica. */
    .ea-indicativos {{ display: grid; gap: 0 1.6rem; margin: .3rem 0 .9rem;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }}
    .ea-ind {{ display: flex; flex-direction: column; gap: .1rem; min-width: 0;
      padding: .6rem 0 .7rem; border-top: 1px solid rgba(29,29,27,.12); }}
    .ea-ind-topo {{ display: flex; align-items: center; gap: .35rem; }}
    .ea-ind-rotulo {{ font-size: .8rem; color: var(--cinza); }}
    .ea-ind-valor-linha {{ display: flex; align-items: center; gap: .35rem; }}
    .ea-ind-valor {{ font-family: var(--fonte-titulo); font-size: 1.45rem;
      color: var(--tinta); font-variant-numeric: tabular-nums; line-height: 1.2; }}
    .ea-ind-sinal {{ font-size: 1.1rem; }}
    .ea-ind-ok .ea-ind-sinal {{ color: var(--verde); }}
    .ea-ind-atencao .ea-ind-sinal {{ color: var(--oliva-escuro); }}
    .ea-ind-atencao .ea-ind-valor {{ color: var(--oliva-escuro); }}
    .ea-ind-leitura {{ font-size: .78rem; color: var(--cinza); line-height: 1.4; }}
    /* Melhor condição, Prever e Próximos passos: blocos em coluna, espaçados. O
       resultado da busca fica num quadro como o dos resultados; a unidade vai
       ao lado do nível do fator e a resposta prevista se destaca em verde-mata. */
    .ea-otimizacao {{ display: flex; flex-direction: column; gap: .7rem; }}
    .ea-otimo-resultado {{ width: 100%; display: flex; flex-direction: column;
      gap: .45rem; padding: 1rem 1.15rem; background: var(--papel-alto);
      border: 1px solid var(--linha); border-radius: 14px; }}
    .ea-ind-unidade {{ font-size: .85rem; color: var(--cinza); }}
    .ea-ind-previsto .ea-ind-valor {{ color: var(--verde-escuro); }}
    .ea-meta-alvo {{ max-width: 12rem; }}
    .ea-botao-acao.q-btn {{ align-self: flex-start; }}

    /* Termos do modelo: pílulas que entram (verde) ou saem (neutras, riscadas). */
    .ea-termos {{ display: flex; flex-wrap: wrap; gap: .4rem; width: 100%; }}
    .ea-termo {{ padding: .3rem .75rem; border-radius: 999px; cursor: pointer;
      user-select: none; font-size: .85rem; border: 1px solid rgba(29,29,27,.2);
      transition: background .12s, border-color .12s; }}
    .ea-termo:focus-visible {{ outline: 2px solid var(--verde); outline-offset: 2px; }}
    .ea-termo-on {{ color: var(--tinta); border-color: rgba(46,133,64,.55);
      background: rgba(64,165,81,.10); }}
    .ea-termo-off {{ color: var(--cinza); text-decoration: line-through;
      background: transparent; border-style: dashed; }}
    .ea-termo-off:hover {{ background: rgba(29,29,27,.04); }}
    /* Próximos passos (US-17): lista numerada, um passo por linha. */
    .ea-passos-sugeridos {{ list-style: none; margin: 0; padding: 0; width: 100%;
      display: flex; flex-direction: column; }}
    .ea-passo-sugerido {{ display: flex; align-items: flex-start; gap: .75rem;
      padding: .65rem 0; border-top: 1px solid rgba(29,29,27,.12);
      color: var(--tinta); font-size: .95rem; line-height: 1.5; }}
    .ea-passo-sugerido:last-child {{ border-bottom: 1px solid rgba(29,29,27,.12); }}
    .ea-passo-sugerido .ea-etapa-num {{ width: 1.45rem; height: 1.45rem;
      font-size: .74rem; margin-top: .05rem; }}
    /* Alerta (extrapolação): oliva, com ícone, sem gritar. */
    .ea-alerta {{ display: flex; align-items: flex-start; gap: .5rem;
      padding: .6rem .75rem; border-radius: 10px; font-size: .85rem;
      line-height: 1.45; color: var(--oliva-escuro);
      background: rgba(155,146,28,.10); border: 1px solid rgba(155,146,28,.35); }}
    .ea-alerta .q-icon {{ font-size: 1.1rem; margin-top: .05rem; flex-shrink: 0; }}
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
    /* Relatório com IA: botões da mesma altura dos campos, a espera escrita no
       próprio botão e o progresso num quadro, seção por seção. */
    .ea-botao-alto.q-btn {{ min-height: 40px; min-width: 9.5rem; }}
    .ea-botao-espera {{ display: inline-flex; align-items: center; gap: .5rem;
      font-weight: 600; white-space: nowrap; }}
    .ea-dica-chave {{ display: flex; flex-wrap: wrap; align-items: baseline;
      gap: .1rem .4rem; margin-top: -.2rem; }}
    .ea-conexao {{ display: flex; flex-wrap: wrap; align-items: center;
      gap: .2rem .5rem; font-size: .88rem; color: var(--tinta); }}
    .ea-conexao-icone {{ color: var(--verde); font-size: 1.2rem; }}
    .ea-conexao .ea-botao-sec.q-btn {{ min-height: 0; padding: 0 .25rem; }}
    .ea-progresso {{ width: 100%; display: flex; flex-direction: column;
      gap: .55rem; padding: 1rem 1.15rem; background: var(--papel-alto);
      border: 1px solid var(--linha); border-radius: 14px; }}
    .ea-progresso-topo {{ display: flex; align-items: center; gap: .6rem; }}
    .ea-progresso-titulo {{ font-weight: 600; color: var(--tinta); }}
    .ea-progresso-etapa {{ font-size: .88rem; color: var(--cinza);
      font-variant-numeric: tabular-nums; }}
    </style>
    """


def aplicar_tema() -> None:
    """Aplica as cores ao Quasar e injeta o CSS na página."""
    ui.colors(
        primary=VERDE_ESCURO,
        secondary=TINTA,
        accent=VERDE,
        positive=VERDE,
    )
    ui.add_head_html(_css())
