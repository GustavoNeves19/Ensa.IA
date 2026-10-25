# Barros Neto, Scarminio e Bruns (2010) — referência de DCCR para o EnsaIA

> **Fonte:** BARROS NETO, B.; SCARMINIO, I. S.; BRUNS, R. E. *Como fazer experimentos: pesquisa e desenvolvimento na ciência e na indústria*. 4. ed. Porto Alegre: Bookman, 2010. E-book.
> **Para que serve este arquivo:** é a fonte de consulta para validar as métricas e os conceitos de DCCR implementados no EnsaIA, porque o PDF do livro (digitalizado, 44 MB) não pode ser lido diretamente pela IA do editor.
> **Como foi feito:** leitura dos capítulos 5 (p. 215–264) e 6 (p. 265–313) a partir do PDF, com conferência das fórmulas e tabelas na imagem das páginas. Todos os exemplos numéricos da seção 16 foram reajustados com numpy, e os valores publicados no livro foram reproduzidos.
> **Paginação:** a página citada é a do livro, que coincide com a página do PDF.
> **Data:** 23/10/2026.

---

## Regras de uso (para a IA do VS Code)

1. **Cite a página.** Toda afirmação sobre método deve apontar a página deste livro. Se o livro não cobre o assunto, a seção 18 diz isso, e o assunto precisa de outra fonte ou fica marcado como "a confirmar". Não invente fórmula nem limiar.
2. **Distinga o que é do livro e o que foi calculado.** Os valores marcados com **[LIVRO]** foram publicados pelos autores. Os marcados com **[CALCULADO]** foram obtidos reajustando os dados do livro com numpy e scipy; servem de oráculo de teste, mas não são citação do livro.
3. **Arredondamento:** o livro publica 2 ou 3 casas decimais. Para comparar, arredonde o valor do sistema para as mesmas casas do livro antes de calcular o erro relativo.
4. **Este arquivo é resumo, não cópia.** Conceitos estão reescritos; fórmulas e dados numéricos estão reproduzidos para fins de verificação.

---

## 0. Mapa do livro para DCCR

| Assunto | Seção do livro | Páginas |
|---|---|---|
| Por que variar todos os fatores ao mesmo tempo (interação) | 1.1 | 16 |
| Necessidade de computador para os cálculos | 1.3 | 22 |
| Modelo, mínimos quadrados, equação matricial | 5.1 | 215–227 |
| Análise da variância, R² | 5.2 | 227–231 |
| Erros-padrão, intervalos de confiança, previsão | 5.3 | 231–237 |
| Teste F da regressão e regra das 10 vezes | 5.4 | 237–238 |
| Modelo quadrático e resíduos com padrão | 5.5 | 238–241 |
| Falta de ajuste, erro puro, R² máximo | 5.6 | 242–249 |
| Correlação à regressão (significado de R) | 5.7 | 250–251 |
| Metodologia de superfície de resposta (RSM) | 6.1 | 265–278 |
| Escolha da escala (codificação) | 6.2 | 278–280 |
| Exemplo com 3 fatores e 2 respostas | 6.3 | 280–288 |
| Desejabilidade (Derringer e Suich) | 6.4 | 288–294 |
| **Planejamentos compostos centrais e rotabilidade** | **6.5** | **294–298** |
| Aplicações com composto central (exemplos resolvidos) | 6A.1 a 6A.4 | 299–309 |

---

## 1. Vocabulário e notação do livro

| Termo no livro | Significado | Página |
|---|---|---|
| Fator | Variável controlada pelo experimentador (letra maiúscula, ex.: T, C, V) | 217 |
| Resposta | Variável medida (letra minúscula, ex.: y) | 217 |
| Nível | Valor que o fator assume num ensaio | 266 |
| Variável codificada (x) | Fator transformado para a escala −1, 0, +1 (±α) | 267, 273 |
| Resíduo (e) | Diferença entre o valor observado e o previsto pelo modelo: e = y − ŷ | 219 |
| Soma quadrática (SQ) | Soma de quadrados de desvios | 228 |
| Média quadrática (MQ) | SQ dividida pelo seu número de graus de liberdade | 230 |
| Graus de liberdade (ν, "nº de g.l.") | Número de valores independentes necessários para calcular a SQ | 229 |
| % de variação explicada | É o R² (SQ_R / SQ_T) | 229, 245 |
| % máxima de variação explicável | (SQ_T − SQ_ep) / SQ_T | 245–246 |
| Erro puro (ep) | Variação entre repetições autênticas do mesmo ensaio | 243 |
| Falta de ajuste (faj) | Parte do resíduo que um modelo melhor poderia eliminar | 242–243 |
| Ponto central | Ensaio com todos os fatores no nível 0 | 266, 294 |
| Parte cúbica / fatorial | Pontos com todos os fatores em ±1 | 294 |
| Parte axial / em estrela | Pontos com um fator em ±α e os demais em 0 | 294 |
| Rodável (rotável) | Planejamento cuja variância da previsão só depende da distância ao centro | 296 |

Subscritos usados pelo livro: R = regressão; r = resíduos; faj = falta de ajuste; ep = erro puro; T = total.

---

## 2. Codificação dos fatores

O livro trabalha com fatores codificados pelo centro e pela meia-amplitude:

$$x = \frac{X - X_{centro}}{\Delta X}, \qquad \Delta X = \frac{X(+1) - X(-1)}{2}$$

Exemplos do livro:
- Tabela 6.1 (p. 267): x₁ = (C − 50)/5 e x₂ = (V − 100)/10.
- Tabela 6.5 (p. 273): x₁ = (C − 35)/5 e x₂ = (v − 125)/10.
- Tabela 6A.5 (p. 308): níveis reais e codificados lado a lado. Concentração 28, 30, 35, 40, 42 mM e tempo 2,5, 3, 4, 5, 5,5 dias correspondem a −1,41, −1, 0, +1, +1,41.

**Consequências da codificação apontadas pelo livro:**
- O valor dos coeficientes depende da escala escolhida. Se a faixa de um fator cai pela metade, seu coeficiente codificado também cai pela metade (p. 280).
- A rotabilidade depende de como os fatores foram codificados; transformar variáveis com escalas diferentes pode destruí-la (p. 297).
- O livro converte de volta para unidades reais ao calcular o caminho de máxima inclinação (p. 271–273) e ao dar o ponto ótimo (p. 277: x₁ = 0,15 e x₂ = −0,37 correspondem a 36% e 121 rpm).

---

## 3. Modelo e ajuste por mínimos quadrados (cap. 5)

**Modelo com erro aleatório** (eq. 5.1, p. 217): y_i = β₀ + β₁X_i + ε_i. Na forma matricial (eq. 5.1a, p. 218):

$$\mathbf{y} = \mathbf{X}\boldsymbol{\beta} + \boldsymbol{\varepsilon}$$

**Estimadores de mínimos quadrados** (eq. 5.12, p. 222), que o livro recomenda saber de cor:

$$\mathbf{b} = (\mathbf{X}^{\prime}\mathbf{X})^{-1}\mathbf{X}^{\prime}\mathbf{y}$$

Condições para a solução existir (p. 222):
- a. **X'X não pode ser singular**, ou seja, a inversa precisa existir;
- b. o modelo precisa ser **linear nos parâmetros**. Modelos com termos quadráticos e interações continuam lineares nos parâmetros (p. 222; exercício 5.4, p. 225).

**Previsões e resíduos** (eq. 5.2 e 5.3, p. 219): ŷ = Xb e e = y − ŷ.

**Propriedades** (p. 225):
- a reta ajustada passa pelo ponto médio das observações;
- a soma dos resíduos de um modelo com intercepto é zero.

**Exemplo de verificação (Tabela 5.1, p. 217 e 223):** com T = 40, 45, 50, 55, 60 °C e y = 60, 70, 77, 86, 91%, o ajuste dá b₀ = −1,200 e b₁ = 1,560 **[LIVRO]**. Os resíduos são −1,2, 1,0, 0,2, 1,4 e −1,4 (p. 224).

---

## 4. Modelo quadrático completo (DCCR)

**Equação geral para k fatores** (eq. 6.15, p. 295):

$$y = \beta_0 + \sum_{i}\beta_i x_i + \sum_{i}\beta_{ii} x_i^2 + \sum_{i<j}\beta_{ij} x_i x_j + \varepsilon$$

- Número de parâmetros: **(k + 1)(k + 2)/2** (p. 294). São 6 para k = 2, 10 para k = 3 e 15 para k = 4.
- Para dois fatores (eq. 6.7, p. 275): ŷ = b₀ + b₁x₁ + b₂x₂ + b₁₁x₁² + b₂₂x₂² + b₁₂x₁x₂.
- A matriz X recebe uma coluna para cada termo. As colunas de x², e de x_i x_j, são os quadrados e os produtos das colunas da matriz de planejamento (p. 277).
- Para estimar um modelo, o número de **combinações distintas de níveis** precisa ser pelo menos igual ao número de parâmetros. Por isso um fatorial 2² com ponto central (5 combinações) não estima o modelo quadrático de 6 parâmetros, e é preciso acrescentar a estrela (p. 275).

---

## 5. Análise da variância (ANOVA)

**Decomposição dos desvios** (eq. 5.15, p. 227):

$$(y_i - \bar{y}) = (\hat{y}_i - \bar{y}) + (y_i - \hat{y}_i)$$

**Decomposição das somas quadráticas** (eq. 5.16, p. 228): SQ_T = SQ_R + SQ_r.

**Com repetições**, o resíduo se divide em falta de ajuste e erro puro (eq. 5.36a, p. 244): SQ_r = SQ_faj + SQ_ep.

**Tabela completa** (Tabela 5.8, p. 245). Notação: i = nível (combinação distinta de fatores), j = repetição, n_i = repetições no nível i, m = número de níveis distintos, n = Σn_i = total de observações, p = número de parâmetros do modelo.

| Fonte | Soma quadrática | g.l. | Média quadrática |
|---|---|---|---|
| Regressão | $SQ_R=\sum_i\sum_j(\hat{y}_i-\bar{y})^2$ | p − 1 | MQ_R = SQ_R/(p − 1) |
| Resíduos | $SQ_r=\sum_i\sum_j(y_{ij}-\hat{y}_i)^2$ | n − p | MQ_r = SQ_r/(n − p) |
| Falta de ajuste | $SQ_{faj}=\sum_i\sum_j(\hat{y}_i-\bar{y}_i)^2$ | m − p | MQ_faj = SQ_faj/(m − p) |
| Erro puro | $SQ_{ep}=\sum_i\sum_j(y_{ij}-\bar{y}_i)^2$ | n − m | MQ_ep = SQ_ep/(n − m) |
| Total | $SQ_T=\sum_i\sum_j(y_{ij}-\bar{y})^2$ | n − 1 | — |

Aqui ȳ_i é a média das repetições no nível i e ȳ é a média global.

- A soma de quadrados do erro puro **não depende do modelo**: estima σ² com ou sem falta de ajuste (p. 245).
- A MQ_faj só estima σ² se o modelo for adequado; caso contrário, inclui a contribuição da falta de ajuste (p. 245).

---

## 6. Coeficiente de determinação e variação máxima explicável

**R²** (eq. 5.17, p. 229), que o livro chama de "% de variação explicada":

$$R^2 = \frac{SQ_R}{SQ_T}$$

- O máximo é 1, quando não há resíduo. Quanto mais perto de 1, melhor o ajuste (p. 229).

**% máxima de variação explicável** (p. 245–246):

$$R^2_{máx} = \frac{SQ_T - SQ_{ep}}{SQ_T}$$

- Nenhum modelo reproduz o erro puro. Por isso, **com repetições, o R² deve ser comparado com o R² máximo, e não com 100%** (p. 246).

**Significado de R** (eq. 5.41, p. 251): em qualquer regressão linear, R é a correlação entre os valores observados e os previstos, r(y, ŷ). A igualdade R² = r(X, y)² vale **só para a reta** (eq. 5.40, p. 251).

**Não constam no livro:** R² ajustado e R² de predição (PRESS). Ver a seção 18.

---

## 7. Significância da regressão (teste F) e regra das 10 vezes

**Teste** (eq. 5.31, p. 237): se não há relação entre os fatores e a resposta, MQ_R / MQ_r segue uma distribuição F com (p − 1, n − p) graus de liberdade. A regressão é significativa se

$$\frac{MQ_R}{MQ_r} > F_{p-1,\;n-p} \quad \text{(ao nível de confiança escolhido; o livro usa 95\%)}$$

**Regra prática** (p. 238, citando Box e Wetz, 1973, e Box e Draper, 1987): uma regressão significativa nem sempre é útil para prever. Ela só é **útil para previsão** se MQ_R / MQ_r for **pelo menos cerca de 10 vezes** o valor tabelado de F. Isto é mais forte do que "significativa" (razão > 1): uma regressão pode passar no teste F e ainda assim não valer a pena usar para previsão.

**Restrições de uso do teste F:**
- O teste pressupõe resíduos com distribuição normal. Se o gráfico dos resíduos mostra um padrão, o teste F não deve ser usado (p. 239).
- Se há falta de ajuste significativa, um F de regressão alto não salva o modelo (p. 246).

**Valores de verificação [LIVRO]:**
- Tabela 5.3: MQ_R/MQ_r = 285,6 contra F₁,₃ = 10,13 (p. 237).
- 6A.2: MQ_R/MQ_r = 20,69, "mais de seis vezes" F₉,₉ (p. 303).

---

## 8. Falta de ajuste e erro puro

**Teste** (p. 245): compare

$$\frac{MQ_{faj}}{MQ_{ep}} \quad \text{com} \quad F_{m-p,\;n-m}$$

Valores altos indicam falta de ajuste: o modelo erra mais do que a própria repetição varia.

**Regras importantes:**
- **Para testar a falta de ajuste, o número de níveis distintos (m) precisa ser maior que o número de parâmetros (p)**, senão ν_faj = m − p = 0 (p. 244). Com repetições só no ponto central, o erro puro tem ν_ep = n_centro − 1.
- Sem falta de ajuste, MQ_faj e MQ_ep estimam σ², e a **MQ_r passa a ser uma estimativa legítima da variância**, com mais graus de liberdade (p. 248).
- Sem repetições não há medida do erro puro. Resta avaliar os resíduos graficamente (p. 242).
- No DCCR, as repetições no ponto central têm duas finalidades: fornecer o erro puro e estabilizar a variância da previsão (p. 297).

**Valores de verificação [LIVRO]:**

| Caso | MQ_faj/MQ_ep | F tabelado (95%) | Conclusão | Página |
|---|---|---|---|---|
| Tabela 5.9 (reta, dados em duplicata) | 55,39 | F₇,₉ = 3,29 | Falta de ajuste | 246 |
| Tabela 5.10 (quadrático) | 0,45 | — | Sem falta de ajuste | 248 |
| Tabela 6.2 (plano, 2² + centro) | 0,18 | — | Sem falta de ajuste | 268 |
| Tabela 6.6 (plano, região do ótimo) | 34,46 | F₃,₂ = 19,0 | Falta de ajuste → passar ao quadrático | 275 |
| Tabela 6.8 (quadrático, estrela) | 0,25 | — | Sem falta de ajuste | 277 |
| 6A.1 Mo(VI) quadrático | 9,6 | F₃,₄ = 6,59 | **Ainda há falta de ajuste**, embora o quadrático seja muito melhor | 300 |

---

## 9. Erros-padrão, intervalos de confiança e significância dos coeficientes

**Hipóteses sobre os erros** (p. 232):
1. variância constante em toda a faixa (homoscedasticidade);
2. erros não correlacionados;
3. distribuição normal.

**Matriz de covariância dos coeficientes** (eq. 5.30, p. 236):

$$\hat{V}(\mathbf{b}) = (\mathbf{X}^{\prime}\mathbf{X})^{-1}\,s^2$$

Os erros-padrão são a raiz da diagonal. No texto teórico, s² é a **MQ_r**, com ν = n − p (p. 231–237).

**Intervalo de confiança** (eq. 5.22, p. 233):

$$b_j \pm t_{\nu} \times \text{erro-padrão}(b_j)$$

Aqui ν é o número de g.l. da estimativa s² usada. **Se o intervalo contém zero, o coeficiente não é significativo** (p. 234).

**Hierarquia:** o costume é manter b₀ no modelo mesmo quando ele não é significativo (p. 234).

**Atenção — qual variância o livro usa nos exemplos (importante para a opção "termo de erro" do EnsaIA):** a recomputação mostra que, nos exemplos do capítulo 6, os erros-padrão publicados **não** vêm da MQ_r. Vêm do **erro puro** ou de uma **estimativa conjunta das repetições**.

| Exemplo | Variância usada nos erros-padrão publicados | Evidência |
|---|---|---|
| Tabela 6.1 / eq. 6.3 (p. 268) | s² = 2,33, das repetições no centro (MQ_ep) | Dito no texto |
| Eq. 6.8 (p. 277) | Estimativa conjunta das repetições dos dois planejamentos: (4,67 + 2,00)/(2 + 2) ≈ 1,67 | Dito no texto; erro-padrão de b₀ = 0,75 **[CALCULADO]** confere |
| 6A.1 Mo(VI) (p. 300) | MQ_ep | Os erros-padrão do livro coincidem com a coluna "erro puro" **[CALCULADO]** (seção 16.2) |
| 6A.2 abacaxi (p. 303) | MQ_ep | Idem (seção 16.3) |
| 6A.4 lacase (p. 307) | MQ_ep | Idem (seção 16.5) |

Conclusão: o livro apresenta as duas opções. A teoria usa o resíduo (p. 233 e 236); os exemplos usam o erro puro (ou a variância conjunta das repetições); e, sem falta de ajuste, o resíduo também é legítimo (p. 248). Isso **sustenta oferecer o termo de erro como opção** e exige registrar qual foi usado.

---

## 10. Previsão e extrapolação

Para a reta (seção 5.3):
- erro-padrão da média prevista em X_a (eq. 5.27, p. 235): $s\sqrt{\frac{1}{n} + \frac{(X_a - \bar{X})^2}{S_{xx}}}$;
- erro-padrão da previsão de **uma** observação (eq. 5.28, p. 236): $s\sqrt{1 + \frac{1}{n} + \frac{(X_a - \bar{X})^2}{S_{xx}}}$;
- erro-padrão da previsão da média de q observações (eq. 5.29, p. 236): o "1" vira 1/q.
- O erro aumenta à medida que nos afastamos do centro dos dados (p. 235).

**Forma matricial para vários fatores:** o livro dá V(b) (eq. 5.30), mas não escreve a variância da previsão em forma matricial. A expressão usual, $s^2\,\mathbf{x}_0^{\prime}(\mathbf{X}^{\prime}\mathbf{X})^{-1}\mathbf{x}_0$, decorre da eq. 5.30, mas **não está escrita no livro**.

**Extrapolação** (p. 241): modelos empíricos são locais. O exemplo do livro: extrapolar 10 °C abaixo da faixa estudada dá rendimento negativo (−24,44%). Previsões fora da região exigem **experimentos confirmatórios** (p. 241). Após otimizar, ensaios de confirmação são "praticamente imprescindíveis" quando há várias respostas (p. 291).

---

## 11. Resíduos e diagnóstico

- O **exame gráfico dos resíduos é obrigatório** em qualquer situação (p. 242).
- Resíduos devem se distribuir ao acaso. Um padrão curvo (positivos no meio e negativos nas pontas) indica que falta um termo, por exemplo o quadrático (p. 239; Figuras 5.6 e 5.8).
- Variância dos resíduos que cresce com a resposta indica **heteroscedasticidade** (p. 283; Figura 6.7).
- **Gráfico de previstos a observados** para comparar modelos (Figura 6A.1, p. 301). **Erro médio absoluto** das previsões como medida de concordância (Tabela 6.11, p. 285).
- **Ponto anômalo:** quando um ensaio concentra os maiores erros, o livro recomenda repeti-lo para verificar erro de registro (6A.5, p. 312).

**Não constam no livro:** teste de Shapiro-Wilk, distância de Cook, alavancagem e gráfico de resíduos à ordem de execução. Ver a seção 18.

---

## 12. Superfície de resposta (RSM)

- A RSM tem duas etapas repetidas até chegar à região ótima: **modelagem** (modelos lineares ou quadráticos) e **deslocamento** pelo caminho de máxima inclinação (p. 265).
- **Curvas de nível** são linhas de resposta constante. Para um plano são retas; para o modelo quadrático, curvas (p. 270; Figura 6.6, p. 279).
- **Caminho de máxima inclinação** (eq. 6.4, p. 272): escolhido um fator base i com deslocamento Δx_i, os demais andam $\Delta x_j = (b_j / b_i)\,\Delta x_i$. Depois os passos são convertidos para unidades reais.
- **Escolha da escala inicial:** não há regra no livro. Ela depende do conhecimento do sistema; uma escala estreita demais ou larga demais atrapalha a busca (p. 278–280).
- **Formas da superfície** citadas: morro ou máximo (p. 277), vale (p. 285) e cumeeira (p. 300).

---

## 13. Planejamento composto central e DCCR (seção 6.5)

**Três partes** (p. 294), para k fatores codificados:
1. **parte fatorial (cúbica):** n_fat pontos com coordenadas ±1. Pode ser um fatorial completo ou fracionário; com muitos fatores, o livro recomenda fracionário de resolução V (p. 295);
2. **parte axial (estrela):** n_ax = 2k pontos com uma coordenada igual a ±α e as demais nulas;
3. **ponto central:** n_centro ensaios com todos os fatores em 0.

**Contagens** (p. 294):
- combinações distintas de níveis: n_fat + 2k + 1;
- parâmetros do modelo quadrático: (k + 1)(k + 2)/2.

**Escolha de α** (p. 295–297):
- α costuma ficar entre 1 e √k;
- α = √k gera o **planejamento esférico**: pontos cúbicos e axiais sobre a mesma (hiper)esfera;
- α = 1 gera o **planejamento de face centrada**: os pontos axiais ficam no centro das faces e só se usam 3 níveis. É útil quando algum fator é qualitativo;
- com muitos fatores, α = √k afasta demais os pontos axiais. Com k = 9, α = 3, e a região intermediária fica sem ensaios;
- **rotabilidade** (Box e Hunter, 1957): o planejamento é rodável se a variância da resposta prevista só depende da distância ao centro (p. 296). Para uma parte cúbica que seja fatorial completo, ou fracionário de resolução V, a rotabilidade é obtida com

$$\alpha = \sqrt[4]{n_{fat}}$$

(p. 297). A rotabilidade depende da codificação, e uma **quase rotabilidade** é aceitável (p. 297).

**Tabela 6.13 (p. 296) — parte axial de planejamentos rodáveis** (parte cúbica = fatorial completo):

| k | n_fat | α rodável | Pontos axiais |
|---|---|---|---|
| 2 | 4 | 1,414 (√2) | (±α, 0), (0, ±α) — usado na Tabela 6.7 |
| 3 | 8 | 1,68 | (±1,68, 0, 0), (0, ±1,68, 0), (0, 0, ±1,68) |
| 4 | 16 | 2 | (±2, 0, 0, 0) etc. |

**Pontos centrais** (p. 297): para estabilizar a variância, a regra prática é **3 a 5 repetições quando α está perto de √k**, e só 1 ou 2 a mais quando α está perto de 1. Para estimar o erro, quanto mais repetições, melhor.

**Construção sequencial** (p. 297):
1. começar pela parte cúbica e ajustar um modelo linear;
2. usar os pontos centrais para testar a curvatura;
3. se a curvatura for significativa, completar com os pontos axiais, como um segundo bloco.

**Blocagem ortogonal** (p. 297–298): o efeito de bloco não se confunde com os coeficientes se

$$\alpha = \sqrt{\frac{n_{fat}\,(n_{ax} + n_{centro,ax})}{2\,(n_{fat} + n_{centro,fat})}}$$

Em geral, blocagem ortogonal sacrifica a rotabilidade. A Tabela 6.14 (p. 298) dá três planejamentos que satisfazem as duas condições:

| k | n_fat | Blocos cúbicos | Centros por bloco cúbico | n_ax | Centros no bloco axial | α | Total de ensaios |
|---|---|---|---|---|---|---|---|
| 2 | 4 | 1 | 3 | 4 | 3 | 1,414 | 14 |
| 4 | 16 | 2 | 2 | 8 | 2 | 2,00 | 30 |
| 5 | 16 (fração) | 1 | 6 | 10 | 1 | 2,00 | 33 |

**Exemplos de composto central no livro:**

| Exemplo | k | α | Centros | Total | Página |
|---|---|---|---|---|---|
| Tabela 6.7 (rendimento) | 2 | √2 | 3 | 11 | 276 |
| 6A.1 Mo(VI) | 2 | 1,4 | 5 | 13 | 299 |
| 6A.2 abacaxi | 3 | 1,682 | 5 | 19 | 302 |
| 6A.3 colesterol | 4 | 2 | 5 | 29 | 305 |
| 6A.4 lacase | 2 | 1,41 | 4 (fatorial e axiais em duplicata) | 20 | 308 |

---

## 14. Ponto ótimo (ponto estacionário)

- O livro localiza o ótimo **derivando o modelo em relação a cada fator e igualando a zero** (exercício 6.8a, p. 278). O exercício 6.8b pede para tentar o mesmo com o modelo linear da eq. 6.6; como um plano não tem ponto extremo, as derivadas não se anulam.
- **Exemplo [LIVRO]** (p. 277, Figura 6.6): o máximo do modelo da eq. 6.8 está em x₁ ≈ 0,15 e x₂ ≈ −0,37, o que dá 36% e 121 rpm, com ŷ ≈ 89,6%. A recomputação dá (0,152; −0,373), ŷ = 89,56 e autovalores negativos (−1,94; −3,69), o que confirma um máximo **[CALCULADO]**.
- Se a região estudada não contém o ótimo (superfície em "ladeira"), o livro manda deslocar de novo pelo caminho de máxima inclinação e repetir a modelagem (p. 278).

**Forma matricial**, que **não está no livro** e é um complemento padrão, coerente com o exercício 6.8:

$$\mathbf{x}_s = -\tfrac{1}{2}\,\mathbf{B}^{-1}\mathbf{b}$$

Aqui **b** reúne os coeficientes lineares e **B** é a matriz simétrica com os b_ii na diagonal e b_ij/2 fora dela. Os sinais dos autovalores de **B** classificam o ponto: todos negativos = máximo; todos positivos = mínimo; sinais mistos = sela. A análise canônica não é tratada no livro.

---

## 15. Desejabilidade (Derringer e Suich, 1980)

**Desejabilidade global** (eq. 6.13, p. 289): média geométrica das desejabilidades individuais. Ela se anula quando qualquer resposta tem valor inaceitável (p. 290).

$$D = \sqrt[m]{d_1\,d_2 \cdots d_m}$$

**Resposta com valor-alvo A** dentro da faixa [LI, LS] (eq. 6.14a-c, p. 290):

$$d = \left(\frac{\hat{y} - LI}{A - LI}\right)^{s} \quad \text{para } LI \le \hat{y} \le A$$

$$d = \left(\frac{\hat{y} - LS}{A - LS}\right)^{t} \quad \text{para } A \le \hat{y} \le LS$$

$$d = 0 \quad \text{para } \hat{y} \text{ fora de } (LI, LS)$$

**Limites unilaterais** (p. 290–291):
- **minimizar** (basta ficar abaixo): elimine a eq. 6.14a e faça d = 1 para ŷ < LI;
- **maximizar** (basta ficar acima): elimine a eq. 6.14b e faça d = 1 para ŷ > LS.

**Expoentes s e t** (p. 290):
- valores altos, como 10, fazem d cair rápido longe do alvo;
- valores baixos toleram mais variação;
- s e t podem diferir; se é mais aceitável ficar acima do alvo, use t « s.

**Cuidados do livro** (p. 291–294):
- testar várias escolhas de s e t e ver se o ótimo é robusto;
- conferir cada resposta individualmente no ponto de D máximo;
- fazer **experimentos confirmatórios**;
- um fator **categórico** pode receber um "ótimo" sem sentido prático (P = −0,474, p. 293). Ele deve ser arredondado para um nível real.

**Exemplo [LIVRO]** (Tabela 6.12 e Figura 6.10, p. 292–293): módulo de Young (LI = 0,5; A = 2,0; LS = 2,5; s = t = 5) e rendimento (LI = 10; A = 15; LS = 20, com d = 1 em 15 e em 20; s = 5; t = 1). Busca em grade de 20 × 20 × 20 = 8.000 combinações, modelos quadráticos completos. Resultado:
- **D = 0,99** em t = −0,158, C = 0,895 e P = −0,474;
- módulo previsto = 2,00 MPa e rendimento previsto = 16,5%.

---

## 16. Exemplos numéricos para testes (golden datasets)

Para cada exemplo há os dados (codificados), o que o livro publica **[LIVRO]** e a recomputação com numpy/scipy **[CALCULADO]**. Todos os coeficientes publicados foram reproduzidos. Os modelos são o quadrático completo, salvo indicação.

### 16.1 Tabela 6.7 — rendimento à concentração e agitação (k = 2, α = √2, 3 centros, n = 11; p. 276–278)

Codificação: x₁ = (C − 35)/5 e x₂ = (v − 125)/10 (Tabela 6.5, p. 273).

```csv
ensaio,C_pct,v_rpm,x1,x2,y_pct
1,30,115,-1,-1,86
2,40,115,1,-1,85
3,30,135,-1,1,78
4,40,135,1,1,84
5,35,125,0,0,90
6,35,125,0,0,88
7,35,125,0,0,89
8,28,125,-1.4142,0,81
9,35,139,0,1.4142,80
10,42,125,1.4142,0,86
11,35,111,0,-1.4142,87
```

**[LIVRO]** (eq. 6.8, p. 277): ŷ = 89,00 + 1,51x₁ − 2,36x₂ − 2,81x₁² − 2,81x₂² + 1,75x₁x₂. Erros-padrão publicados: 0,75; 0,46; 0,46; 0,54; 0,54; 0,65, calculados com a variância conjunta das repetições das Tabelas 6.1 e 6.7.

**[LIVRO]** ANOVA (Tabela 6.8, p. 278):

| Fonte | SQ | g.l. | MQ |
|---|---|---|---|
| Regressão | 144,15 | 5 | 28,83 |
| Resíduos | 2,76 | 5 | 0,55 |
| Falta de ajuste | 0,76 | 3 | 0,25 |
| Erro puro | 2,00 | 2 | 1,00 |
| Total | 146,91 | 10 | — |

% explicada = 98,12; % máxima explicável = 98,64. Ótimo em (0,15; −0,37) com ŷ = 89,6%.

**[CALCULADO]**:
- b = 89,0000; 1,5089; −2,3624; −2,8125; −2,8125; 1,7500;
- F_reg = 52,18, contra F₅,₅ = 5,05 (razão 10,3);
- F_faj = 0,254, contra F₃,₂ = 19,16 (p = 0,855);
- R² ajustado = 0,9624; R² de predição = 0,9325; Shapiro-Wilk W = 0,982 (p = 0,974).

### 16.2 6A.1 — sinal catalítico do Mo(VI) (k = 2, α = 1,4, 5 centros, n = 13; p. 299–300)

```csv
ensaio,x1,x2,y
1,-1,-1,0.373
2,1,-1,0.497
3,-1,1,0.483
4,1,1,0.615
5,-1.4,0,0.308
6,1.4,0,0.555
7,0,-1.4,0.465
8,0,1.4,0.628
9,0,0,0.538
10,0,0,0.549
11,0,0,0.536
12,0,0,0.549
13,0,0,0.538
```

**[LIVRO]** (p. 300):
- **Linear:** ŷ = 0,510 + 0,076x₁ + 0,058x₂, com MQ_faj/MQ_ep = 90,7.
- **Quadrático:** ŷ = 0,542 + 0,076x₁ + 0,058x₂ − 0,055x₁² + 0,003x₂² + 0,002x₁x₂, com MQ_faj/MQ_ep = 9,6 > F₃,₄ = 6,59.
- Erros-padrão publicados: (0,003), (0,002), (0,002), (0,002), (0,002), (0,003).
- São significativos: x₁, x₁² e x₂. Não são significativos: x₂² e x₁x₂. A superfície é uma **cumeeira**.

**[CALCULADO]** quadrático:
- erros-padrão com **erro puro** = 0,0029; 0,0023; 0,0023; 0,0025; 0,0025; 0,0032. **Coincidem com o livro.** Com o resíduo seriam 0,0062; 0,0050; 0,0050; 0,0054; 0,0054; 0,0070;
- SQ_R = 0,09339 (5 g.l.); SQ_r = 0,00136 (7); SQ_faj = 0,00120 (3); SQ_ep = 0,00017 (4); SQ_T = 0,09475 (12);
- R² = 98,56%; R² máximo = 99,82%; R² ajustado = 0,9754; R² de predição = 0,9074; F_reg = 95,97 contra F₅,₇ = 3,97.

**Uso no teste do sistema:** é o caso em que **o modelo quadrático ainda tem falta de ajuste**, e o sinal do indicador deve acusar isso.

### 16.3 6A.2 — desidratação osmótica de abacaxi (k = 3, α = 1,682, 5 centros, n = 19; p. 301–303)

```csv
ensaio,x1,x2,x3,perda_peso_pct
1,-1,-1,-1,47.34
2,1,-1,-1,53.00
3,-1,1,-1,53.64
4,1,1,-1,54.28
5,-1,-1,1,48.85
6,1,-1,1,53.73
7,-1,1,1,55.19
8,1,1,1,58.31
9,-1.682,0,0,51.90
10,1.682,0,0,57.34
11,0,-1.682,0,47.62
12,0,1.682,0,57.35
13,0,0,-1.682,50.73
14,0,0,1.682,57.68
15,0,0,0,56.24
16,0,0,0,55.74
17,0,0,0,57.23
18,0,0,0,56.85
19,0,0,0,55.42
```

Fatores: x₁ = tempo de contato, x₂ = temperatura, x₃ = concentração da solução osmótica.

**[LIVRO]** (p. 303):
- **Linear:** ŷ = 54,13 + 1,72x₁ + 2,55x₂ + 1,43x₃, com MQ_faj/MQ_ep = 8,50.
- **Quadrático:** ŷ = 56,32 + 1,72x₁ + 2,55x₂ + 1,43x₃ − 0,71x₁² − 1,47x₂² − 0,86x₃² − 0,85x₁x₂ + 0,21x₁x₃ + 0,42x₂x₃.
  - Erros-padrão: 0,34 (b₀); 0,20 (lineares e quadráticos); 0,27 (interações).
  - MQ_faj/MQ_ep = 2,66, sem falta de ajuste a 95%.
  - **Explica 95,4%.**
  - **MQ_R/MQ_r = 20,69, mais de 6 vezes F₉,₉.**

**[CALCULADO]** quadrático:
- erros-padrão com erro puro = 0,336; 0,203; 0,203; 0,203; 0,203; 0,203; 0,203; 0,266 (×3). Coincidem com o livro. No modelo linear, o livro imprime 0,22 para x₂, mas a recomputação dá 0,20, provável erro de impressão;
- SQ_R = 202,402 (9); SQ_r = 9,780 (9); SQ_faj = 7,521 (5); SQ_ep = 2,259 (4); SQ_T = 212,183 (18);
- R² = 95,39%; R² máximo = 98,94%; F_reg = 20,69 contra F₉,₉ = 3,18 (razão 6,5); F_faj = 2,66 contra F₅,₄ = 6,26 (p = 0,18);
- R² ajustado = 0,9078; R² de predição = 0,7045;
- p-valores (t com resíduo, 9 g.l.): x₁ 0,0002; x₂ < 0,0001; x₃ 0,0007; x₁² 0,032; x₂² 0,0006; x₃² 0,014; x₁x₂ 0,047; x₁x₃ 0,58; x₂x₃ 0,29.

### 16.4 6A.3 — redução de colesterol (k = 4, α = 2, 5 centros, n = 29; p. 303–306)

```csv
ensaio,x1,x2,x3,x4,colesterol_mg_g
1,-1,-1,-1,-1,1.701
2,1,-1,-1,-1,1.120
3,-1,1,-1,-1,1.607
4,1,1,-1,-1,0.881
5,-1,-1,1,-1,1.860
6,1,-1,1,-1,0.965
7,-1,1,1,-1,1.786
8,1,1,1,-1,0.933
9,-1,-1,-1,1,2.131
10,1,-1,-1,1,2.072
11,-1,1,-1,1,2.095
12,1,1,-1,1,2.002
13,-1,-1,1,1,2.101
14,1,-1,1,1,2.055
15,-1,1,1,1,2.017
16,1,1,1,1,1.972
17,0,0,0,0,1.763
18,0,0,0,0,1.840
19,0,0,0,0,1.935
20,-2,0,0,0,1.713
21,2,0,0,0,1.089
22,0,-2,0,0,1.643
23,0,2,0,0,1.601
24,0,0,-2,0,1.691
25,0,0,2,0,1.648
26,0,0,0,-2,0.675
27,0,0,0,2,2.049
28,0,0,0,0,1.783
29,0,0,0,0,1.983
```

Fatores: x₁ = concentração de quilaia, x₂ = terra diatomácea, x₃ = temperatura, x₄ = pH.

> **Errata (2026-10-25):** com o CSV acima como está, os termos significativos são os da **1ª e da 4ª colunas**, não da 1ª e da 3ª. Os coeficientes [CALCULADO] que este resumo chama de x₃ (0,3475; −0,0926; 0,1757) saem na 4ª coluna. Ou a 3ª e a 4ª colunas do CSV estão trocadas, ou os rótulos x₃/x₄ do texto estão; conferir na tabela do livro (p. 304) antes de citar. O teste `tests/unit/test_barros_neto_dccr.py` usa o CSV como está e afirma sobre a 4ª coluna.

**[LIVRO]** (p. 303–304):
- o quadrático é melhor que o linear, não tem falta de ajuste a 95% e explica 94,3%;
- só os termos com x₁ e x₃ são significativos;
- modelo reduzido publicado: ŷ = 1,861 − 0,189x₁ − 0,083x₁² + 0,348x₃ − 0,093x₃² + 0,176x₁x₃.

**[CALCULADO]**:
- quadrático completo: b₀ = 1,8608; x₁ = −0,1894; x₃ = 0,3475; x₁² = −0,0829; x₃² = −0,0926; x₁x₃ = 0,1757. R² = 94,30%; R² máximo = 99,26%; F_faj = 2,68 contra F₁₀,₄ = 5,96 (25 combinações distintas − 15 parâmetros = 10 g.l. de falta de ajuste; a versão anterior deste resumo escrevia F₁₈,₄).
- **Atenção:** os coeficientes do "modelo reduzido" do livro são **os mesmos do modelo completo**, só sem os termos não significativos. **Não houve reajuste.** Reajustando só com x₁ e x₃, b₀ vira 1,8135, x₁² vira −0,0760 e x₃² vira −0,0857.
- O sistema precisa documentar qual das duas práticas usa na redução do modelo (seção 17).

### 16.5 6A.4 — produção de lacase (k = 2, α = 1,41, n = 20, todos os pontos em duplicata e 4 centros; p. 307–308)

Níveis reais: concentração do álcool 28, 30, 35, 40, 42 mM e tempo de cultivo 2,5, 3, 4, 5, 5,5 dias, para os códigos −1,41, −1, 0, +1, +1,41.

```csv
ensaio,x1,x2,PPO_U_mL
1,-1,-1,3.50
2,-1,-1,3.20
3,1,-1,1.17
4,1,-1,1.70
5,-1,1,4.10
6,-1,1,5.40
7,1,1,1.90
8,1,1,2.10
9,0,0,4.80
10,0,0,5.00
11,0,0,4.70
12,0,0,5.20
13,-1.41,0,5.25
14,-1.41,0,5.41
15,0,1.41,6.00
16,0,1.41,3.20
17,1.41,0,2.30
18,1.41,0,1.60
19,0,-1.41,0.50
20,0,-1.41,0.50
```

**[LIVRO]** (p. 307):
- ŷ = 4,93 − 1,18x₁ + 0,97x₂ − 0,70x₁² − 1,25x₂² − 0,21x₁x₂, com erros-padrão 0,35; 0,18; 0,18; 0,23; 0,23; 0,25;
- todos os termos são significativos, exceto a interação;
- explica 84,9%; o máximo explicável é 91,2%, porque o erro puro é alto; não há falta de ajuste.

**[CALCULADO]**:
- erros-padrão com erro puro coincidem com o livro;
- ν_ep = 11, porque todos os pontos repetidos contam para o erro puro;
- F_faj = 2,63 contra F₃,₁₁ = 3,59 (p = 0,10); são 9 combinações distintas − 6 parâmetros = 3 g.l. de falta de ajuste (a versão anterior deste resumo escrevia F₅,₁₁);
- R² ajustado = 0,7956; R² de predição = 0,6824.

### 16.6 Exemplos auxiliares (capítulo 5 e início do capítulo 6)

| Exemplo | Dados | Valores [LIVRO] | Página |
|---|---|---|---|
| Reta, Tabela 5.1 | T = 40…60; y = 60, 70, 77, 86, 91 | b₀ = −1,200; b₁ = 1,560; SQ_R = 608,4; SQ_r = 6,4; R² = 98,96%; erro-padrão de b₀ = 0,0923; erro-padrão de b₁ = 4,665; IC₉₅ de b₁ = (1,266; 1,854) | 223–234 |
| Duplicatas, Tabela 5.7 | 9 temperaturas × 2 | Reta: SQ_faj = 1.938,59 (7), SQ_ep = 45,00 (9), MQ_faj/MQ_ep = 55,39. Quadrático (Tabela 5.10): MQ_faj/MQ_ep = 0,45; % explicada 99,35; máximo 99,50 | 242–248 |
| 2² + 3 centros, Tabela 6.1 | 7 ensaios | ŷ = 68,00 − 5,25x₁ + 4,25x₂; s² = 2,33; MQ_faj/MQ_ep = 0,18; % explicada 97,07; máximo 97,52 | 267–269 |

---

## 17. Métricas do EnsaIA × livro (mapeamento)

Base: `ESPECIFICACAO.md` v0.6 (grupos A, C, D e E). **Confirme no código** que a implementação corresponde à especificação. Legenda: ✅ coberto pelo livro · ⚠️ coberto com ressalva · ❌ não está no livro.

| ID | Métrica do sistema | Livro | Página | Observação para validação |
|---|---|---|---|---|
| A1 | Estatística descritiva | ⚠️ | cap. 2 | Conceitos de média e desvio no cap. 2 (não detalhado aqui). O CV não foi verificado. |
| A2 | Identificação do DCCR | ✅ | 294–297 | Três partes; n_ax = 2k; α rodável = n_fat^(1/4); contagem de combinações = n_fat + 2k + 1. |
| A2 | Aviso de α não rodável | ✅ | 295–297 | O livro aceita α entre 1 e √k; quase rotabilidade é aceitável. Face centrada (α = 1) é outro planejamento. |
| A2 | Nº de pontos centrais | ✅ | 297 | Regra: 3 a 5 repetições se α ≈ √k. Bom candidato a indicador de atenção. |
| A3 | Codificação real ↔ codificada | ✅ | 267, 273, 308 | x = (X − centro)/meia-amplitude. Coeficientes mudam com a escala (p. 280). |
| C1 | Coeficientes (MQO) | ✅ | 222 (eq. 5.12) | b = (X'X)⁻¹X'y. Teste com a seção 16. |
| C1 | Coeficientes em unidades reais | ⚠️ | 273, 277 | O livro só converte pontos (ótimo e caminho), não a equação inteira. |
| C1 | Erro-padrão, t, IC 95% | ✅ | 233–236 (eq. 5.22, 5.30) | ν = g.l. da variância usada. Ver a seção 9 sobre resíduo × erro puro. |
| C1 | Termo de erro (resíduo × erro puro) | ✅ | 233, 236, 248, 268, 300–307 | Teoria com MQ_r; exemplos com MQ_ep. As duas opções têm base. Registrar a escolhida. |
| C1 | Significância por p < α | ⚠️ | 234 | O livro usa o IC (contém zero?) e trabalha a **95%**. Não usa α = 0,10. |
| C1 | Hierarquia (manter b₀) | ✅ | 234 | Mantém-se b₀ mesmo não significativo. Hierarquia para outros termos não é discutida. |
| C1 | Redução do modelo | ⚠️ | 285, 304 | Em 6A.3 o livro **não reajusta**: mantém os coeficientes do modelo completo (seção 16.4). Na eq. 6.11 (p. 285) também apenas elimina termos. Documentar a prática do sistema. |
| C2 | Tabela ANOVA completa | ✅ | 245 (Tabela 5.8) | Fórmulas e g.l. na seção 5. |
| C3 | R² | ✅ | 229 (eq. 5.17) | "% de variação explicada". |
| C3 | R² máximo | ✅ | 245–246 | (SQ_T − SQ_ep)/SQ_T. Só com repetições. |
| C3 | R² ajustado | ❌ | — | Não está no livro. Precisa de outra fonte. |
| C3 | R² de predição (PRESS) | ❌ | — | Não está no livro. Precisa de outra fonte. |
| C3 | F da regressão e F tabelado | ✅ | 237 (eq. 5.31) | MQ_R/MQ_r contra F(p − 1, n − p). |
| C3 | Razão F_calc/F_tab ≥ ~10 | ✅ | 238 | Regra de Box e Wetz (1973) para regressão útil para previsão. |
| C4 | Falta de ajuste | ✅ | 244–245 | MQ_faj/MQ_ep contra F(m − p, n − m). Exige m > p e repetições. |
| C5 | Equação do modelo | ✅ | 277, 303 | Em variáveis codificadas. |
| C6 | Previstos × observados | ✅ | 285, 301 | Gráfico e erro médio absoluto (Tabela 6.11). |
| C7 | Comparação de modelos | ✅ | 238–241, 283 | Linear × quadrático por % explicada, falta de ajuste, F e resíduos. |
| D1 | Resíduos × previstos | ✅ | 239, 242, 283–284 | Padrão curvo = termo faltando; funil = heteroscedasticidade. |
| D2 | Normalidade dos resíduos | ⚠️ | 232, 239 | O livro exige a hipótese de normalidade, mas **não usa Shapiro-Wilk**. Precisa de outra fonte para o teste. |
| D3 | Resíduos × ordem de execução | ❌ | — | Não encontrado no livro. |
| D4 | Pontos influentes (Cook, alavancagem) | ⚠️ | 312 (só ideia) | O livro só sugere repetir um ensaio anômalo. Cook e alavancagem precisam de outra fonte. |
| E1, E2 | Superfície e curvas de nível | ✅ | 270, 279, 285–288 | — |
| E3 | Ponto estacionário | ⚠️ | 277–278 | Via derivadas (exercício 6.8). A forma matricial e a classificação por autovalores não estão no livro (seção 14). |
| E3 | Aviso de ótimo fora da região | ✅ | 241, 278 | Extrapolação é arriscada; deslocar e remodelar. |
| E4 | Otimização de uma resposta | ⚠️ | 277–278 | O conceito está no livro; o algoritmo (busca em malha + refinamento local) não. |
| E5 | Desejabilidade | ✅ | 289–294 (eq. 6.13–6.14) | Conferir as fórmulas, os unilaterais, s e t, e a grade. Teste com Tabela 6.12 — D = 0,99. |
| E6 | Previsão "e se?" e intervalo | ⚠️ | 235–236 (eq. 5.27–5.29) | Fórmula só para a reta; a forma matricial decorre da eq. 5.30 (seção 10). |
| E6 | Ensaio de confirmação | ✅ | 241, 291 | — |
| — | Curvatura pelo ponto central | ✅ | 161, 297 | Relevante só para fatoriais (fora do escopo). No DCCR, a curvatura vem dos termos quadráticos. |

---

## 18. O que o livro NÃO cobre (precisa de outra fonte ou fica "a confirmar")

- R² ajustado.
- R² de predição / PRESS.
- Teste de Shapiro-Wilk e outros testes formais de normalidade.
- Distância de Cook, alavancagem (h_ii) e resíduos studentizados.
- Gráfico de resíduos à ordem de execução.
- Análise canônica e classificação do ponto estacionário por autovalores.
- Uso de α = 0,10; o livro trabalha sempre a 95%.
- Algoritmo numérico de otimização (malha + refinamento local, múltiplos pontos de partida).
- Conversão da equação inteira para unidades reais.
- Variância da previsão em forma matricial; apenas implícita na eq. 5.30.

---

## 19. Checklist de validação do código (para a IA do VS Code)

1. Para cada exemplo da seção 16, gere um teste com os dados em CSV e compare com os valores **[LIVRO]**, arredondados como no livro.
2. Rode os mesmos casos com o termo de erro **"erro puro"** e confirme os erros-padrão de 16.2, 16.3 e 16.5.
3. Confira as fórmulas da ANOVA (seção 5) e os graus de liberdade, inclusive ν_faj = m − p e ν_ep = n − m, com m = combinações distintas.
4. Confira o R² máximo e a regra de comparar o R² com ele (seção 6).
5. Confira a razão F_calc/F_tab e o limiar de cerca de 10 (seção 7).
6. Confira a identificação do DCCR e o α rodável = n_fat^(1/4) com os casos k = 2, 3, 4 (seção 13).
7. Confira a desejabilidade com a Tabela 6.12 (seção 15).
8. Confira o ponto ótimo da seção 16.1: (0,15; −0,37), ŷ ≈ 89,6, máximo.
9. Para cada métrica marcada ⚠️ ou ❌ na seção 17, verifique se o código cita outra fonte ou marca o limiar como "a confirmar".
10. Registre a prática de redução do modelo (com ou sem reajuste) e o termo de erro padrão no relatório e na documentação.
