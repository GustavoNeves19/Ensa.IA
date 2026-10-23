# Fonte do caso de estudo — Hidrólise ácida de sementes de açaí (CCRD)

## Citação (ABNT)

> IGREJA, Willen Silva; MARTINS, Luiza Helena da Silva; ALMEIDA, Rafaela
> Rodrigues de; OLIVEIRA, Johnatt Allan Rocha de; LOPES, Alessandra Santos;
> CHISTÉ, Renan Campos. Açai Seeds (Euterpe oleracea Mart) Are
> Agroindustrial Waste with High Potential to Produce Low-Cost Substrates
> after Acid Hydrolysis. **Molecules**, v. 28, n. 18, art. 6661, 2023.
> DOI: 10.3390/molecules28186661

- **DOI / URL:** https://doi.org/10.3390/molecules28186661
- **Mirror de acesso aberto:** https://pmc.ncbi.nlm.nih.gov/articles/PMC10536898/
- **Acesso em:** 2026-10-23 — **texto completo do PDF colado diretamente
  pelo usuário na conversa**, não leitura assistida por IA via HTML/PMC.
  Maior confiança de todos os casos desta leva.
- **Tipo de planejamento:** CCRD, 3 fatores, 5 níveis (−α, −1, 0, +1, +α),
  17 ensaios, α = 1,68 (rotacional, confirmado contra a fórmula para k=3).
- **Nº de ensaios:** 17 (e mais 17 com H3PO4, não usados aqui — ver
  observações em `referencia.yaml`)

## Procedência dos dados

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Matriz de ensaios (`dados.csv`) | Tabela 1 (p. 4), 17 ensaios com H2SO4 | Usuário colou o PDF completo (2026-10-23) | |
| Faixas dos fatores (vértices/axiais) | Tabela 3 (p. 11) | Usuário colou o PDF completo (2026-10-23) | |
| R² por resposta | Texto, Seção 2.3 (p. 7) | Usuário colou o PDF completo (2026-10-23) | |
| Efeitos padronizados (Pareto) | Figura 2 (p. 5) | Usuário colou o PDF completo (2026-10-23) | |
| Condição ótima (prevista e confirmada) | Seção 2.3 (p. 7-8) | Usuário colou o PDF completo (2026-10-23) | |
| Coeficientes da equação / ANOVA completa | Tabela S3 (material suplementar) | **não acessado** | |

## Ressalvas

- O artigo usa **α = 0,10** (90% de confiança), não o 0,05 padrão do EnsaIA
  (ADR 0003) — ver observações em `referencia.yaml`.
- Os três modelos (TRS, HMF, massa solubilizada) têm **falta de ajuste
  significativa** — o próprio artigo admite que são "significativos, mas
  não preditivos", válidos só como indicadores de tendência dentro da
  faixa estudada. Isso é informação do artigo, não uma divergência do
  EnsaIA a explicar.
- Os coeficientes da equação de regressão não estão no corpo do artigo —
  só os efeitos padronizados (Pareto) e a menção de que a ANOVA completa
  está na Tabela S3 (suplementar, não acessada). Por isso `coeficientes` e
  `significancia` ficam vazios em `referencia.yaml` — preenchíveis se
  alguém baixar o material suplementar em mdpi.com.
- O valor de F da regressão para massa solubilizada (1,93) parece
  contradizer o texto do artigo (que o trata como significativo apesar de
  ser menor que o F tabelado de 2,72) — possível erro de digitação no
  artigo original, sinalizado, não corrigido.
- Há um segundo DCCR completo no artigo (H3PO4 em vez de H2SO4), cujos
  dados estão só na Tabela S1 suplementar — candidato a um caso adicional.
