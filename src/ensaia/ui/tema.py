"""Identidade visual da interface — o ponto único de troca de marca da UI.

A paleta é a **oficial da Universidade Federal Rural da Amazônia** (Manual de
Uso da Marca da Ufra, ASCOM/Ufra, 2022, p. 10): o logotipo é composto por dois
verdes — verde (#40A551) e verde oliva (#9B921C) — mais o preto (#1D1D1B).
Trabalhamos sobre esses três, acrescidos de um verde-mata profundo derivado
(para profundidade e ações) e de um papel quente levemente oliva como fundo —
nada do cinza neutro dos UI kits nem do creme genérico.

A fonte de assinatura é a **Sentient** (Indian Type Foundry, licença livre
Fontshare), uma serifada editorial com caráter — carrega a marca e os títulos.
O corpo fica num neutro de sistema, que sabe se calar. Os arquivos da fonte e a
licença vivem em `ui/static/fonts/`.

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


def _css() -> str:
    """Folha de estilo da marca: fontes, atmosfera, grão e o uploader."""
    return f"""
    <style>
    /* Sentient — serifada de assinatura, variável (peso 200–800), self-hosted. */
    @font-face {{
      font-family: 'Sentient';
      src: url('/ensaia-static/fonts/Sentient-Variable.woff2') format('woff2');
      font-weight: 200 800; font-style: normal; font-display: swap;
    }}
    @font-face {{
      font-family: 'Sentient';
      src: url('/ensaia-static/fonts/Sentient-VariableItalic.woff2') format('woff2');
      font-weight: 200 800; font-style: italic; font-display: swap;
    }}

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
      --fonte-titulo: 'Sentient', Georgia, 'Times New Roman', serif;
      --fonte-corpo: system-ui, -apple-system, 'Segoe UI', Roboto,
        Helvetica, Arial, sans-serif;
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
      font-size: clamp(2.6rem, 7vw, 3.4rem); line-height: 1;
      letter-spacing: -0.015em; }}
    .ea-colofao {{ color: var(--cinza); font-size: .82rem; margin-top: .55rem; }}
    .ea-headline {{ font-family: var(--fonte-titulo); font-weight: 500;
      font-size: clamp(1.9rem, 5vw, 2.85rem); line-height: 1.14;
      color: var(--tinta); max-width: 19ch; }}
    .ea-sub {{ color: var(--cinza); font-size: 1.02rem; line-height: 1.55;
      max-width: 36rem; }}

    /* Trilha dos sete passos — sem trilho nem seta; a ordem é a numeração. */
    .ea-passos {{ display: flex; flex-wrap: wrap; gap: 1rem 1.7rem; }}
    .ea-passo {{ display: flex; align-items: baseline; gap: .5rem; }}
    .ea-passo .n {{ color: var(--oliva-escuro); font-weight: 700; font-size: .78rem;
      font-variant-numeric: tabular-nums; min-width: .95rem; }}
    .ea-passo .t {{ color: var(--tinta); font-weight: 600; font-size: .95rem; }}
    .ea-passo .d {{ color: var(--cinza); font-size: .78rem; }}

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

    .ea-mapear {{ display: flex; flex-direction: column; gap: .7rem; }}
    .ea-mapa-grade {{ display: grid; gap: .7rem 1rem;
      grid-template-columns: repeat(auto-fit, minmax(205px, 1fr)); }}
    .ea-mapa-item {{ display: flex; flex-direction: column; gap: .25rem; }}
    .ea-col-nome {{ font-weight: 600; font-size: .85rem; color: var(--tinta);
      overflow-wrap: anywhere; }}

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
