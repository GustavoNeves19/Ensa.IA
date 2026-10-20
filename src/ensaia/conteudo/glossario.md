# Glossário de planejamento de experimentos (DOE)

**Fator**: o que você controla no experimento (temperatura, pH, tempo, dose).

**Nível**: o valor de um fator num ensaio. Em fatoriais de dois níveis, o baixo e o alto.

**Resposta**: o que você mede no fim de cada ensaio (rendimento, remoção, pureza).

**Codificação**: reescrever cada fator na escala de −1 (nível baixo) a +1 (nível alto), com 0 no centro. Deixa os coeficientes comparáveis entre fatores de unidades diferentes.

**Ponto central**: ensaio com todos os fatores no nível 0. Repetido, estima o erro puro e testa curvatura.

**Fatorial 2ᵏ**: todas as combinações de dois níveis de k fatores. Serve para triagem: descobrir quais fatores importam.

**Composto central (DCCR)**: fatorial + pontos axiais (±α) + pontos centrais. Permite ajustar um modelo quadrático. É o único tipo de planejamento que o EnsaIA analisa hoje (ver ADR 0013) — os termos abaixo são vocabulário geral de DOE, úteis para ler artigos, mas o EnsaIA não reconhece esses outros tipos.

**Box-Behnken**: planejamento de três níveis sem os vértices do cubo, também para modelo quadrático, com menos ensaios.

**Efeito**: quanto a resposta muda, em média, quando o fator vai do nível baixo ao alto.

**Interação**: quando o efeito de um fator depende do nível de outro.

**Coeficiente**: o número que multiplica cada termo na equação do modelo (na escala codificada).

**p-valor**: a chance de ver um efeito tão grande só por acaso. Abaixo de α (geralmente 0,05), o termo é chamado de significativo.

**α (nível de significância)**: o limite para o p-valor; 0,05 quer dizer aceitar 5% de risco de declarar um efeito que não existe.

**ANOVA**: a tabela que divide a variação da resposta entre o que o modelo explica (regressão) e o que sobra (resíduo).

**R²**: fração da variação explicada pelo modelo (de 0 a 1). **R² ajustado** desconta o número de termos; **R² de predição** mede quanto o modelo acerta ensaios que não viu.

**Falta de ajuste**: teste que compara o erro do modelo com o erro puro das réplicas. Significativo = o modelo não descreve bem a forma da resposta.

**Resíduo**: observado menos previsto, ensaio por ensaio.

**Shapiro-Wilk**: teste de normalidade dos resíduos; p-valor baixo indica resíduos pouco normais.

**Distância de Cook**: quanto um único ensaio puxa o modelo. Acima de 1, com alavancagem alta, é ensaio influente.

**Superfície de resposta**: o modelo desenhado em função de dois fatores, com os demais fixos.

**Ponto estacionário**: onde a superfície fica plana: máximo, mínimo ou ponto de sela.

**Desejabilidade**: nota de 0 a 1 de quanto uma condição atende às metas; com várias respostas, combina todas numa só (D global).

**Lenth (PSE, ME)**: método para julgar efeitos de fatoriais sem réplicas; efeitos acima da margem de erro (ME) são ativos.
