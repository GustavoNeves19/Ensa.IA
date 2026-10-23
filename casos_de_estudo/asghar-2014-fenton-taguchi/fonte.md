# Fonte do caso de estudo — Comparação CCD × Taguchi no processo Fenton

## Citação (ABNT)

> ASGHAR, Aisha; ABDUL RAMAN, Abdul Aziz; WAN DAUD, Wan Mohd Ashri. A
> Comparison of Central Composite Design and Taguchi Method for Optimizing
> Fenton Process. **The Scientific World Journal**, v. 2014, art. 869120,
> 2014. DOI: 10.1155/2014/869120

- **DOI / URL:** https://doi.org/10.1155/2014/869120
- **Mirror de acesso aberto:** https://pmc.ncbi.nlm.nih.gov/articles/PMC4167450/
- **Acesso em:** 2026-10-23, download direto do HTML do PMC e extração das
  tabelas por código (não resumo de IA; não humano abrindo o PDF ainda).
- **Tipo de planejamento:** CCD, 4 fatores, 30 ensaios (16 fatoriais + 8
  axiais + 6 centrais). **α = 1** (axial coincide com o vértice do fatorial
  em cada fator — "face centrada", não rotacional).
- **Nº de ensaios:** 30

## Procedência dos dados

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Matriz de ensaios, valores reais e previstos (`dados.csv`) | Tabela 2, 30 ensaios | IA, extração HTML direta (2026-10-23) | |
| Faixas dos fatores | Tabela 1 | IA, extração HTML direta (2026-10-23) | |
| ANOVA parcial (Modelo + 4 termos nomeados, por resposta) | Tabela 3 | IA, extração HTML direta (2026-10-23) | |
| R² de cada resposta | Texto corrido (não tabela) | IA, extração HTML direta (2026-10-23) | |
| Equação completa (coeficientes) | Equação (13) | **NÃO transcrito** — ver ressalva | |
| Condição ótima | Seção 4.2.2 (não extraída ainda) | **NÃO transcrito** | |

## Ressalvas

- **α = 1 (face centrada), não rotacional.** Como em
  `koohikamali-2012-transesterificacao-girassol` (lá com α=2): este CCD não é
  o DCCR estritamente rotacional que `identificar_planejamento` reconhece
  (ADR 0013) — útil para validar o ajuste OLS/ANOVA, não para demonstrar
  reconhecimento automático.
- **Coeficientes não transcritos.** A Equação (13) do artigo é uma expressão
  polinomial longa (4 fatores, termos lineares/quadráticos/interação),
  tipografada em várias linhas MathML alinhadas. Uma tentativa de leitura
  manual produziu uma inconsistência (um termo repetido com coeficientes
  diferentes) — sinal de que a leitura estava errada, não de que o número
  estava errado no artigo. Ninguém deve confiar nesses coeficientes até
  alguém abrir o PDF/HTML e transcrever a equação com calma, termo a termo.
- **Modelo reduzido para COD.** A ANOVA (Tabela 3) mostra 12 graus de
  liberdade para o modelo de COD (não os 14 do quadrático completo para
  k=4) — dois termos foram eliminados, mas quais não ficou claro nesta
  leitura. Por isso `termos_modelo` não foi declarado; o EnsaIA vai ajustar
  o quadrático completo, o que deve dar R² ligeiramente MAIOR que o
  publicado para COD (não é erro, é o modelo completo nunca piorando em
  relação a um reduzido).
- **Condição ótima não localizada** nesta leitura — o texto menciona valores
  de resposta (~80% COD, ~99% descoloração) na Seção 4.2.2, mas as
  coordenadas dos 4 fatores não foram extraídas.
- Unidades: `h2o2_fe2` e `dye_fe2` são razões mássicas (wt/wt), sem unidade
  própria — conferir se o artigo usa outra notação.
