# Fonte do caso de estudo: fotodegradacao de levofloxacino por hidroxiapatita

## Citacao

> GO, Adrian D.; DELA ROSA, Francis M.; CAMACHO, Drexel H.; PUNZALAN, Eric R.
> Dataset on photocatalytic degradation of Levofloxacin using hydroxyapatite
> photocatalyst: Optimization by response surface methodology. *Data in Brief*,
> v. 42, art. 108219, 2022. DOI: 10.1016/j.dib.2022.108219.

- **Dataset complementar:** Mendeley Data, DOI 10.17632/h82gspgkpf.2.
- **Artigo local:** `artigo_PMC9079681.xml`.
- **Planilha oficial local:**
  `Dataset on photocatalytic degradation of LEVO using HAp photocatalyst Optimization by RSM.xlsx`.
- **Software declarado pelo estudo:** MINITAB 17.
- **Planejamento:** Box-Behnken, tres fatores, 15 ensaios e tres repeticoes
  do ponto central.

## Procedencia da transcricao

| Conteudo | Aba da planilha oficial | Linhas | Status |
|---|---|---:|---|
| Niveis dos fatores | `BBD Model`, Table 1 | 5 a 9 | Transcrito |
| Matriz e eficiencia observada | `BBD Model`, Table 2 | 14 a 28 | Transcrito |
| ANOVA, falta de ajuste, R2 e R2 ajustado | `ANOVA` | 3 a 16 | Transcrito |
| Coeficientes codificados | `ANOVA` | 3 a 12 | Transcrito |
| Otimizacao e resposta prevista | `Reponse Optimizer` | 8 a 13 | Transcrito |

## Conferencia dupla pendente

Os dados foram copiados da planilha oficial local, nao de valores inferidos.
Antes de usar o caso como evidencia final, uma pessoa confere as linhas da
planilha e outra confirma a correspondencia entre os termos codificados e os
nomes usados no LYRA.

| Parte | Transcrito por | Conferido por | Data |
|---|---|---|---|
| BBD Model, Table 2 | Codex | Pendente | |
| ANOVA e coeficientes | Codex | Pendente | |
| Response Optimizer | Codex | Pendente | |

## Ressalvas metodologicas

- O estudo publicou um modelo 2FI. Termos quadraticos nao devem ser incluidos
  nesta comparacao.
- A falta de ajuste publicada e nao significativa: SQ = 17,72, GL = 6,
  F = 0,28 e p = 0,906.
- O p-valor do intercepto nao foi reportado e permanece `null`.
