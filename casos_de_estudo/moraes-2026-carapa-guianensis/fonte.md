# Fonte do caso de estudo — Valorização de subprodutos de andiroba (DCCR)

## Citação (ABNT)

> MORAES, Vinicius Sidônio Vale; PANTOJA, Gabriela Vieira; LIMA, José
> Aparecido Ferreira de; BERALDO-NETO, Emídio; PRUDENTE, Emanuelle da Silva;
> OLIVEIRA, Johnatt Allan Rocha de; MARTINS, Luiza Helena da Silva;
> LOURENÇO, Lúcia de Fátima Henriques; PIMENTA, Daniel Carvalho; FONTANARI,
> Gustavo Guadagnucci. Valorization of Carapa guianensis By-Products:
> Extraction Optimization and Antimicrobial and Antioxidant Activity.
> **Foods**, v. 15, n. 15, art. 2641, 2026. DOI: 10.3390/foods15152641

- **DOI / URL:** https://doi.org/10.3390/foods15152641
- **Mirror de acesso aberto:** https://pmc.ncbi.nlm.nih.gov/articles/PMC13464831/
- **Acesso em:** 2026-10-23, por extração direta do HTML do PMC (não resumo
  de IA, não humano abrindo PDF).
- **Tipo de planejamento:** DCCR, 3 fatores, 17 ensaios (8 fatoriais + 6
  axiais + 3 centrais). α = 1,682 (rotacional para k=3, conforme Tabela 1).
- **Nº de ensaios:** 17 — **não transcritos individualmente, ver ressalva**.

## Procedência dos dados

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Faixas dos fatores (Tabela 1) | Seção 2.4, Tabela 1 | IA, extração HTML direta (2026-10-23) | |
| ANOVA de Y2=TPC (Tabela 2) | Seção 3, Tabela 2 | IA, extração HTML direta (2026-10-23) | |
| **Tabela bruta de ensaios** | **não localizada** | — | — |
| Coeficientes da equação | **não publicados no corpo do texto** | — | — |

## Ressalvas

- **Bloqueante:** o artigo não publica a tabela com os 17 ensaios e as
  respostas observadas em cada um — só a Tabela 1 (níveis) e a Tabela 2
  (ANOVA já com os termos não significativos removidos). Sem isso, não dá
  para montar `dados.csv` nem rodar `validar_caso` — ver observações em
  `referencia.yaml`.
- Mesmo grupo de pesquisa e mesmo template de três outros casos desta leva
  (`pantoja-2026-astrocaryum-murumuru`, `prudente-2025-pracaxi`) — os três
  compartilham a mesma lacuna estrutural.
- A Tabela 2 (ANOVA) tem células que parecem mescladas (rowspan) na
  extração — os valores de F calculado/F tabelado não foram usados com
  confiança; só R²/R² ajustado (em células próprias) entraram em
  `referencia.yaml`.
- A Seção 2.4 chama X1 de "temperature" no texto corrido, mas a nota de
  rodapé da própria Tabela 1 diz "X1 = extraction time (min)" — tratado como
  erro de template do artigo (a mesma frase aparece idêntica no Murumuru),
  seguimos a tabela.
