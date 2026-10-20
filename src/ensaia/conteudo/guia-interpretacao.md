# Como ler os resultados do EnsaIA

Os números vêm sempre do núcleo determinístico do EnsaIA. Ao explicar, use os
valores exatamente como aparecem e não refaça contas.

## 1. O planejamento
Confira o tipo reconhecido — hoje só o composto central rotacional (DCCR) —,
quantos ensaios e quantos pontos centrais. Se os dados não formam um DCCR, o
tipo vem "não identificado" e os avisos dizem a que a disposição mais se
parece; os avisos da análise também dizem se algo no planejamento limita as
conclusões.

## 2. Os termos significativos
Cada termo do modelo tem um p-valor. Se p < α (normalmente 0,05), o termo é
significativo: aquele fator, interação ou curvatura muda a resposta além do que
o acaso explicaria. O sinal do coeficiente diz a direção: positivo aumenta a
resposta, negativo diminui.

## 3. A ANOVA e o R²
- A regressão significativa (p < α), ou F calculado / F tabelado maior que 1,
  indica que o modelo explica a resposta.
- R² perto de 1 é bom, mas olhe também o R² ajustado e o de predição: se o de
  predição for muito menor, o modelo pode estar decorando os dados.
- Falta de ajuste não significativa (p ≥ α) é o desejável.

## 4. O diagnóstico
Os resíduos devem se espalhar ao acaso em torno do zero, sem forma de funil ou
curva, e seguir a normal (Shapiro-Wilk com p ≥ α). Ensaios influentes ou
outliers merecem ser conferidos no caderno de laboratório.

## 5. A superfície e o ótimo
O ponto estacionário diz se a superfície tem um máximo, um mínimo ou uma sela,
e se ele cai dentro da região estudada. A otimização por desejabilidade procura
a melhor condição dentro dessa região; D perto de 1 indica metas atendidas.
Recomende sempre um ensaio de confirmação na condição sugerida.

## 6. Próximo passo
Se o ótimo cai na borda ou o ponto estacionário fica fora da região, vale
deslocar a região experimental naquela direção. Se o modelo tem falta de
ajuste, um modelo de ordem maior ou mais níveis podem ser necessários.
