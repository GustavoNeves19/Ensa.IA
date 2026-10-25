# Glossário do delineamento composto central rotacional (DCCR)

**Fator**: o que você controla no experimento (temperatura, pH, tempo, dose).

**Nível**: o valor de um fator num ensaio. No DCCR, cada fator tem cinco níveis: −α, −1, 0, +1 e +α.

**Resposta**: o que você mede no fim de cada ensaio (rendimento, remoção, pureza).

**Codificação**: reescrever cada fator como x = (X − centro) / meia-amplitude, com 0 no centro e ±1 nos níveis da parte fatorial. Deixa os coeficientes comparáveis entre fatores de unidades diferentes.

**DCCR (delineamento composto central rotacional)**: o planejamento que o EnsaIA analisa. Tem três partes: a parte fatorial, os pontos axiais e os pontos centrais. Com ele dá para ajustar um modelo quadrático e encontrar um máximo ou um mínimo.

**Parte fatorial (cúbica)**: os ensaios com todos os fatores em −1 ou +1, nas combinações de um fatorial.

**Pontos axiais (estrela)**: os ensaios com um fator em −α ou +α e os demais no centro (0). São 2 por fator.

**Ponto central**: ensaio com todos os fatores no nível 0. Repetido, mede o erro puro e estabiliza a qualidade da previsão perto do centro.

**α axial**: a distância dos pontos axiais ao centro, na escala codificada. No DCCR ele é o rotacional: α = (número de ensaios da parte fatorial)^(1/4), ou seja, 1,414 para 2 fatores, 1,682 para 3 e 2 para 4.

**Rotabilidade**: a propriedade de o modelo prever com a mesma precisão em todos os pontos à mesma distância do centro. É o que o α rotacional garante.

**Efeito**: quanto a resposta muda quando o fator varia.

**Interação**: quando o efeito de um fator depende do nível de outro.

**Termo quadrático**: o termo x² de um fator. Representa a curvatura da resposta, e é o que permite haver um máximo ou um mínimo dentro da região.

**Coeficiente**: o número que multiplica cada termo na equação do modelo (na escala codificada).

**p-valor**: a chance de ver um efeito tão grande só por acaso. Abaixo de α (geralmente 0,05), o termo é chamado de significativo.

**α (nível de significância)**: o limite para o p-valor; 0,05 quer dizer aceitar 5% de risco de declarar um efeito que não existe. Não confundir com o α axial.

**ANOVA**: a tabela que divide a variação da resposta entre o que o modelo explica (regressão) e o que sobra (resíduo).

**Erro puro**: a variação entre repetições do mesmo ensaio (em geral, os pontos centrais). Não depende do modelo.

**Falta de ajuste**: teste que compara o erro do modelo com o erro puro. Significativo quer dizer que o modelo não descreve bem a forma da resposta.

**R²**: fração da variação explicada pelo modelo (de 0 a 1). **R² ajustado** desconta o número de termos; **R² de predição** mede quanto o modelo acerta ensaios que não viu; **R² máximo** é o teto que o R² pode alcançar com o erro puro que há nos dados. Com repetições, compare o R² a esse teto, não a 100%.

**F calculado / F tabelado**: quantas vezes o F da regressão passa do valor de tabela. Acima de 1, a regressão é significativa; acima de cerca de 10, ela é útil para prever.

**Resíduo**: observado menos previsto, ensaio por ensaio.

**Shapiro-Wilk**: teste de normalidade dos resíduos; p-valor baixo indica resíduos pouco normais.

**Distância de Cook**: quanto um único ensaio puxa o modelo. Acima de 1, com alavancagem alta, é ensaio influente.

**Superfície de resposta**: o modelo desenhado em função de dois fatores, com os demais fixos.

**Curvas de nível**: linhas da superfície em que a resposta prevista é a mesma.

**Ponto estacionário**: onde a superfície fica plana: máximo, mínimo ou ponto de sela.

**Desejabilidade**: nota de 0 a 1 de quanto uma condição atende às metas; com várias respostas, combina todas numa só (D global).

**Ensaio de confirmação**: repetir o experimento na condição ótima encontrada para conferir se o resultado previsto se confirma.
