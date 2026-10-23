# Fonte do caso de estudo — Extração de compostos bioativos de Licaria armeniaca (DCCR)

## Citação (ABNT)

> FERREIRA, Lanalice R.; ABELÉM, Bianca R.; REIS, José Diogo E.; HERMAN,
> Christelle Anne N. P.; FIGUEIREDO, Pablo Luis B.; PINTO, Laine Celestino;
> MARTINS, Luiza Helena S.; SILVA, Milton Nascimento da; GOMES, Paulo Wender
> P.; SILVA, Joyce Kelly R. da. Optimization of the Extraction of Bioactive
> Compounds and Metabolomic Profile of Licaria armeniaca. **Plants**, v. 14,
> n. 20, art. 3158, 2025. DOI: 10.3390/plants14203158

- **DOI / URL:** https://doi.org/10.3390/plants14203158
- **Mirror de acesso aberto:** https://pmc.ncbi.nlm.nih.gov/articles/PMC12566995/
- **Acesso em:** 2026-10-23, por extração direta do HTML do PMC (não resumo
  de IA, não humano abrindo PDF).
- **Autora correspondente:** Joyce Kelly R. da Silva (joykellys@ufpa.br) —
  Luiza H. S. Martins é coautora (7ª de 10), não a correspondente deste
  artigo (diferente de Carapa/Murumuru/Pracaxi, onde Martins é
  corresponding/última autora).
- **Tipo de planejamento:** DCCR, 3 fatores, 17 ensaios (8 fatoriais + 6
  axiais + 3 centrais). α = 1,68.
- **Nº de ensaios:** 17 — **matriz de entrada publicada (Apêndice A.1), mas
  resposta por ensaio não publicada, ver ressalva**.

## Procedência dos dados

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Faixas dos fatores (Tabela 4) | Seção de metodologia | IA, extração HTML direta (2026-10-23) | |
| Matriz de entrada dos 17 ensaios (Apêndice A.1) | Apêndice | IA, extração HTML direta (2026-10-23) | |
| ANOVA de 3 das 6 combinações (Tabela 1) | Seção de resultados | IA, extração HTML direta (2026-10-23) | |
| Equações (1) e (2) dos 2 modelos adotados | Seção de resultados, corpo do texto | IA, extração HTML direta (2026-10-23) | |
| **Resposta observada por ensaio** | **não localizada** | — | — |

## Ressalvas

- **Bloqueante:** o artigo não publica a resposta (DPPH%, TPC) medida em
  cada um dos 17 ensaios para nenhuma das 6 combinações matriz×resposta —
  só agregados (ANOVA, Pareto, equação). Sem isso, não dá para montar
  `dados.csv` nem rodar `validar_caso`, mesmo tendo a matriz de entrada
  completa (o que falta é a COLUNA de saída, não a de entrada).
- Estrutura fora do padrão dos demais casos desta leva: o mesmo delineamento
  foi aplicado a 3 matrizes vegetais (folhas, galhos finos, galhos grossos)
  × 2 respostas (DPPH, TPC) = 6 combinações, mas só 2 geraram modelo
  considerado significativo e preditivo pelos próprios autores — ver
  `referencia.yaml` para os detalhes de quais passaram e por quê.
- O fator X3 (razão sólido:líquido) usa duas escalas reais diferentes
  conforme a matriz (folhas: 0,8-8,0% m/v; galhos finos: 2-20% m/v) — o
  schema de `referencia.yaml` só suporta uma faixa por fator, então
  `fatores.razao_solido_liquido` usa a escala de folhas; a resposta
  `tpc_galhos_finos` reaproveita a mesma posição codificada numa régua real
  diferente, documentado em observações.
- O Apêndice A.1 (matriz de entrada) tem um valor isolado que não bate com a
  Tabela 4 de níveis (ensaio 4, RSL-folhas=1,12 em vez do +1 esperado,
  6,54) — transcrito verbatim, não corrigido, ver `dados.csv`.
- Mesmo tipo de lacuna estrutural (falta resposta bruta por ensaio) dos
  outros três casos desta leva (Carapa, Murumuru, Pracaxi), mas artigo e
  grupo de pesquisa diferentes (UFPA, não UFRA) — mera coincidência de
  lacuna, não o mesmo template de tabela.
