# 0003 — α = 0,05 em vez de p ≤ 0,10

**Status:** Aceita · **Data:** 2026-08-23

## Contexto

O protótipo selecionava os termos do modelo com p ≤ 0,10. O §4.3(b) do
pré-projeto assinado diz outra coisa:

> "será verificado se a classificação de significância produzida pela ANOVA do
> pipeline (p < 0,05) coincide com a classificação reportada na referência"

Havia divergência real entre o que o código fazia e o que o documento
entregue à orientadora promete.

Os dois valores têm defesa legítima. Em DOE exploratório com poucos graus de
liberdade residuais — situação comum em planejamentos pequenos — 0,10 é
prática corrente, justamente porque o poder do teste é baixo e 0,05 descarta
efeitos reais. Mas 0,05 é o padrão amplamente esperado e o que está assinado.

## Decisão

α = 0,05 como padrão, alinhado ao documento.

O valor é parâmetro (`alfa` em `MetadadosExecucao`, `selecionar_termos`,
`extrair_coeficientes`), nunca constante embutida. Toda análise registra o α
usado no `AnalysisResult`, para que nenhum resultado guardado fique ambíguo
sobre qual critério o produziu.

## Consequências

- Modelos mais enxutos que os do protótipo. Alguns termos que entravam com
  0,10 saem, e o R² de alguns casos vai cair.
- Isso pode *melhorar* a concordância do §4.3(b) com a literatura, que
  majoritariamente reporta a 0,05 — ou piorar, se o artigo de referência usou
  0,10. Divergência de critério entre artigos é um achado a discutir na
  monografia, não um defeito a esconder.
- Como α é parâmetro, dá para rodar a validação inteira nos dois valores e
  reportar os dois. Isso é material de resultado, não retrabalho: mostra
  quanto a conclusão depende do critério — uma análise de sensibilidade que
  fortalece o capítulo.

## Pendência

Se durante a validação ficar claro que 0,10 descreve melhor os casos de
estudo selecionados, o caminho correto é **corrigir o §4.3(b) do documento** e
justificar na monografia — não mudar o código em silêncio e deixar a
divergência.
