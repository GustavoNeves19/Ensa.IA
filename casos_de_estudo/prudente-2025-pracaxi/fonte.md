# Fonte do caso de estudo — Extração ultrassônica de compostos bioativos de pracaxi (DCCR)

## Citação (ABNT)

> PRUDENTE, Emanuelle S.; SANTOS, Matheus M. dos; PANTOJA, Gabriela V.;
> BEZERRA, Fernanda W. F.; KOMESU, Andrea; FONTANARI, Gustavo G.; MARTINS,
> Luiza H. S. Sustainable Valorization of Amazonian Pracaxi (*Pentaclethra
> macroloba* (Willd.)) Residues via Optimized Ultrasound-Assisted Extraction
> of Bioactive Compounds. **Sustainable Processes Connect**, v. 1, n. 1,
> art. 0007, 2025. DOI: 10.69709/SusProc.2025.111299

- **DOI / URL:** https://doi.org/10.69709/SusProc.2025.111299
- **Acesso:** https://www.scifiniti.com/3079-1421/1/2025.0007
- **Acesso em:** 2026-10-23, por extração direta do HTML da scifiniti.com
  (não resumo de IA, não humano abrindo PDF). Diferente dos outros três
  artigos desta leva (Carapa, Murumuru, Licaria), este é publicado numa
  plataforma própria do grupo de pesquisa (Sustainable Processes Connect),
  não MDPI/PMC — acessível diretamente por `curl`, sem bloqueio HTTP 403.
- **Autora correspondente:** Luiza H. S. Martins (confirmado nos metadados
  do artigo).
- **Tipo de planejamento:** DCCR, 3 fatores, 17 ensaios (8 fatoriais + 6
  axiais + 3 centrais). α = 1,68.
- **Nº de ensaios:** 17 — **não transcritos individualmente, ver ressalva**.

## Procedência dos dados

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Faixas dos fatores (Tabela 1) | Seção de metodologia | IA, extração HTML direta (2026-10-23) | |
| ANOVA (Tabela 3) e R² | Seção de resultados | IA, extração HTML direta (2026-10-23) | |
| Equações do modelo (Equações 3, 4 e 5) | Seção de resultados, corpo do texto (MathML) | IA, extração HTML direta (2026-10-23) | |
| Condição ótima e confirmação experimental | Seção de resultados | IA, extração HTML direta (2026-10-23) | |
| **Tabela bruta de ensaios** | **não localizada** | — | — |

## Ressalvas

- **Bloqueante:** sem a tabela bruta dos 17 ensaios, não dá para montar
  `dados.csv` nem rodar `validar_caso` — mas as três equações do modelo
  reduzido (TPC, TF, AA) são reais e verificáveis, extraídas diretamente de
  MathML (não transcrição manual de imagem), ver `referencia.yaml`.
- A coluna "Maximum % explainable variation" da Tabela 3 (candidata a R²
  ajustado) tem uma ambiguidade de leitura — o valor 98,44 aparece repetido
  nas linhas de TPC e de AA, sugerindo mesclagem de célula (rowspan) na
  extração, mesmo padrão já visto no Carapa guianensis. Por isso
  `r2_ajustado` ficou `null` nas três respostas.
- Mesmo grupo de pesquisa e mesmo template de níveis de
  `moraes-2026-carapa-guianensis` e `pantoja-2026-astrocaryum-murumuru` (os
  três compartilham a mesma Tabela 1 de níveis, idêntica nos três artigos,
  incluindo a mesma inconsistência aritmética nos níveis de etanol — ver
  observações desses dois casos).
- O texto corrido troca "TPC" por "TCP" uma vez, ao comentar o teste F da
  regressão — tratado como erro de digitação do próprio artigo, não
  ambiguidade real.
