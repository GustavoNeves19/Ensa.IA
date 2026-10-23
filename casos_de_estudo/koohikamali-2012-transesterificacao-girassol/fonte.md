# Fonte do caso de estudo — Transesterificação de óleo de girassol (CCD)

## Citação (ABNT)

> KOOHIKAMALI, Sara; TAN, Chin Ping; LING, Tau Chuan. Optimization of
> Sunflower Oil Transesterification Process Using Sodium Methoxide. **The
> Scientific World Journal**, v. 2012, art. 475027, 2012.
> DOI: 10.1100/2012/475027

- **DOI / URL:** https://doi.org/10.1100/2012/475027
- **Mirror de acesso aberto:** https://pmc.ncbi.nlm.nih.gov/articles/PMC3349207/
- **Acesso em:** 2026-10-23, por leitura assistida (ferramenta de IA), não
  humano abrindo o PDF — ver pendência abaixo.
- **Tipo de planejamento:** CCD, 3 fatores, 5 níveis (−α, −1, 0, +1, +α),
  20 ensaios, **α = 2,0** (não o rotacional de 1,682 — ver observações em
  `referencia.yaml`).
- **Nº de ensaios:** 20

## Procedência dos dados

De onde saiu cada coisa. Sem isto, ninguém consegue reconferir a transcrição
— nem vocês daqui a dois meses.

Os números de `dados.csv` e `referencia.yaml` vieram de uma ferramenta de IA
lendo o mirror PMC — **ainda não é a dupla conferência humana que este
repositório exige.** Antes de usar este caso como evidência final do
capítulo de resultados, uma pessoa precisa abrir `PMC3349207` (ou o PDF via
DOI) e conferir item a item, preenchendo as duas colunas abaixo.

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Matriz de ensaios (`dados.csv`) | Tabela 1, 20 ensaios | IA (WebFetch, 2026-10-23) | |
| Equação do modelo reduzido (coeficientes) | Corpo do texto | IA (WebFetch, 2026-10-23) | |
| Tabela ANOVA (GL, QM, F, p — SQ não extraída) | Tabela de ANOVA do modelo reduzido | IA (WebFetch, 2026-10-23) | |
| R² / R² ajustado | Texto | IA (WebFetch, 2026-10-23) | |
| Condição ótima (previsto e confirmação) | Tabela de otimização | IA (WebFetch, 2026-10-23) | |

## Ressalvas

- **α = 2,0, não rotacional.** Os três fatores têm ponto axial a exatamente
  2× a distância do ponto vértice ao centro (ex.: tempo — centro 120 min,
  vértice ±30 min, axial ±60 min). Isso é um composto central no sentido
  amplo, não o DCCR estritamente rotacional (α = n_f^(1/4) = 1,682 para
  k=3) que o EnsaIA reconhece automaticamente desde o ADR 0013. Útil para
  validar o ajuste OLS/ANOVA contra um artigo publicado; **não** usar como o
  "exemplo" de reconhecimento automático de DCCR na tela/MCP.
- O artigo reporta só o modelo reduzido (backward elimination já aplicado):
  Intercepto, tempo, catalisador, metanol_excesso². Os demais termos do
  quadrático completo não foram publicados — não inventados, não incluídos.
- A ANOVA lida trouxe GL, QM, F e p por termo, mas não a soma de quadrados;
  conferir a Tabela original se o §4.3 exigir SQ.
- Condição ótima: previsto 100,04%, confirmação experimental 99,70% — são
  números diferentes, ambos do artigo; o critério (d) compara contra o
  previsto.
- Unidades: tempo em minutos; álcool em excesso estequiométrico e catalisador
  em % massa/massa (w/w%) — conferir a notação exata do artigo (o texto lido
  usa "w/w%").
