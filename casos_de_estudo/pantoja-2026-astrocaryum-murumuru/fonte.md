# Fonte do caso de estudo — Extração verde de compostos fenólicos de sementes de murumuru (DCCR)

## Citação (ABNT)

> PANTOJA, Gabriela Vieira; LIMA, José Aparecido Ferreira de; BERALDO-NETO,
> Emídio; SILVA, Lucas Figueiredo da; OLIVEIRA, Johnatt Allan Rocha de;
> FONTANARI, Gustavo Guadagnucci; PIMENTA, Daniel Carvalho; MARTINS, Luiza
> Helena da Silva. Ultrasound-Assisted Green Extraction of Phenolic
> Compounds from Astrocaryum murumuru Biomass. **Foods**, v. 15, n. 8, art.
> 1368, 2026. DOI: 10.3390/foods15081368

- **DOI / URL:** https://doi.org/10.3390/foods15081368
- **Mirror de acesso aberto:** https://pmc.ncbi.nlm.nih.gov/articles/PMC13114846/
- **Acesso em:** 2026-10-23, por extração direta do HTML do PMC.
- **Tipo de planejamento:** DCCR, 3 fatores, 17 ensaios (8 fatoriais + 6
  axiais + 3 centrais). α = 1,682.
- **Nº de ensaios:** 17 — **não transcritos individualmente, ver ressalva**.

## Procedência dos dados

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Faixas dos fatores (Tabela 1) | Seção 2.2 | IA, extração HTML direta (2026-10-23) | |
| ANOVA (Tabela 2) e R²/R² ajustado | Seção 3.1 | IA, extração HTML direta (2026-10-23) | |
| Equação do modelo (Equação 3) | Seção 3.1, corpo do texto | IA, extração HTML direta (2026-10-23) | |
| **Tabela bruta de ensaios** | **não localizada** | — | — |

## Ressalvas

- **Bloqueante:** sem a tabela bruta, não dá para montar `dados.csv` nem
  rodar `validar_caso` — mas a equação do modelo reduzido é real e
  verificável (ver `referencia.yaml`).
- O cabeçalho da Tabela 2 cita o F tabelado da regressão como "4,12", mas o
  texto corrido diz "8,7 vezes maior que o F tabelado (2,48)" — divergência
  entre tabela e texto no próprio artigo, sinalizada, não corrigida.
- Tempo (X1) foi excluído do modelo final por não significativo a 90% de
  confiança — por isso não aparece em `termos_modelo`.
- Mesmo grupo de pesquisa e mesmo template de `moraes-2026-carapa-guianensis`
  e `prudente-2025-pracaxi` (os três compartilham a Tabela 1 de níveis,
  praticamente idêntica nos três artigos).
