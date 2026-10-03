> **Nota de 2026-08-24, posterior a este dossiê:** a seção 0 abaixo descreve o
> par canônico/sombra como duas saídas paralelas. Depois de ler o código já
> existente em `core/model.py`/`core/anova.py` (que já previa um único
> `AjusteOLS` servindo #3, #4 e #5), a decisão final ficou mais estrita: o
> ajuste-sombra é um detalhe interno de `AjusteOLS`, nunca exposto, com
> autocheck de SSR/R² em runtime — ver
> [ADR 0005](../decisoes/0005-anova-tipo-ii-encapsulada.md). O conteúdo
> técnico abaixo (a tradução de nomes, a necessidade do segundo ajuste)
> continua válido; só a exposição arquitetural mudou.
>
> Adendo de escopo para a seção 4 (`core/desirability`, issue #6): além do
> ótimo global, vale computar **três cenários representativos** dentre os
> pontos quase-ótimos — econômico, intermediário e de alta performance —
> ordenando por um critério de custo definido pelo usuário (ex.: soma dos
> tempos de processo) e escolhendo o de maior desejabilidade em cada faixa.
> É lógica determinística, pura em Python, que entra no `AnalysisResult` como
> mais um campo; `narrative` só narra os três pontos já escolhidos pelo
> núcleo. Motivação: o protótipo original (`github.com/GustavoNeves19/LYRA`)
> já tinha essa ideia, mas a decisão de qual linha representa cada cenário
> era feita pelo LLM em cima do JSON bruto — o que já produziu, num dos
> relatórios gerados, dois "cenários" diferentes apontando pra mesma linha.
> Mover a seleção para o núcleo preserva o valor de produto sem repetir o
> erro.

# Guia de Implementação — Núcleo LYRA (issues #3, #4, #5, #6 + notas #9/#10)

Ordem de execução: **#3 → #4 → #5** (sequencial, cada uma consome a saída da anterior) **desbloqueiam #8**. **#6** depende só de #3 (precisa do modelo ajustado, não da ANOVA). #9 e #10 podem começar em paralelo a #3, mas #10 só fecha de verdade depois de #6.

---

## 0. Decisão de arquitetura que atravessa #3, #4 e #5

**Problema central identificado na pesquisa:** `anova_lm(model, typ=2)` do statsmodels só funciona se o modelo foi ajustado via `statsmodels.formula.api.ols(formula, data).fit()` — o atributo `model_spec` que a função usa para separar cada termo dos termos de ordem superior que o contêm só é populado nesse caminho (confirmado lendo `statsmodels/base/model.py`). Mas a fórmula patsy nomeia colunas como `"I(x1 ** 2)"`, não `"x1^2"` — quebra a notação canônica exigida pela validação (a) do §4.3, que casa coeficientes por nome exato.

**Decisão a tomar (documentar no código):** dois modelos, uma fonte de verdade.

1. **Modelo canônico** (fonte de verdade para #3 e #5): matriz de projeto `X` construída manualmente em numpy/pandas, colunas nomeadas exatamente `"Intercept", "x1", "x2", ..., "x1^2", ..., "x1:x2", ...` na ordem de declaração dos fatores. Ajustado com `sm.OLS(y, X).fit()`. `.params`, `.bse`, `.conf_int()` daqui alimentam #5 e a validação (a)/(b).
2. **Modelo sombra** (só para #4, só para extrair a tabela ANOVA Tipo II): ajustado via `smf.ols(formula, data).fit()`, com a fórmula gerada **programaticamente** a partir da mesma lista ordenada de termos do modelo canônico (nunca digitada à mão). Um dicionário determinístico traduz `"x1^2" -> "I(x1**2)"` e `"x1:x2" -> "x1:x2"` (interação já bate) na ida, e faz o caminho inverso ao ler o `DataFrame` que `anova_lm` devolve.
3. **Teste de regressão obrigatório**: comparar `modelo_canonico.ssr` com `modelo_sombra.ssr` (e `rsquared`, `rsquared_adj`) e assertar igualdade numérica (tolerância de ponto flutuante) — isso é o que garante que os dois modelos são de fato o mesmo modelo, só nomeado diferente. Sem esse teste, um bug de tradução de fórmula passaria despercebido.

```python
def build_formula(term_names: list[str]) -> str:
    """Traduz a notação canônica do LYRA para sintaxe patsy, na ordem
    exata de declaração — nunca aceitar string de fórmula livre."""
    parts = []
    for t in term_names:
        if "^" in t:                      # "x1^2" -> "I(x1**2)"
            base, power = t.split("^")
            parts.append(f"I({base}**{power})")
        else:                             # "x1", "x1:x2" já são válidos
            parts.append(t)
    return "y ~ " + " + ".join(parts)
```

Escreva um teste de arquitetura (mesmo espírito do teste de AST que trava core/narrative) que congele essa convenção: gerar termos programaticamente a partir da lista de fatores, nunca aceitar fórmula digitada solta em nenhum ponto do pipeline.

---

## 1. Issue #3 — `core/model`

### O que implementar

1. **Codificação de níveis** para `[-1, +1]`:
   ```python
   def codificar(x_natural, low, high):
       avg = (high + low) / 2
       span = (high - low) / 2
       return (x_natural - avg) / span
   ```
   Fórmula confirmada em múltiplas fontes (NIST Handbook, material de curso "Empirical Model Building"). É transformação afim, reversível: `x_natural = avg + x_codificado * span`.

2. **Matriz de projeto (design matrix)** em ordem padrão: para fatorial 2^k, a coluna do fator *j* alterna sinal a cada `2^(j-1)` linhas. Gerar com `itertools.product([-1, 1], repeat=k)` (mais simples e não depende de biblioteca externa) — **preserva ordem de declaração dos fatores**, que é o que a notação canônica depende.

3. **Matriz de modelo (model matrix)**, construída manualmente — não usar `dmatrix()`/formula API aqui:
   - coluna `"Intercept"`: todos 1
   - colunas de efeito principal: `"x1"`, `"x2"`, ... (cópia direta das colunas codificadas)
   - colunas de interação: `"x1:x2"` = produto elemento a elemento de `x1` e `x2` (só incluir se o desenho suportar — 2^k completo sempre suporta até ordem k)
   - colunas quadráticas: `"x1^2"` = `x1 * x1` — **só incluir se o desenho tiver ≥3 níveis no fator** (CCD/BBD com pontos axiais/centrais; um 2^k puro sem ponto central não tem informação para estimar curvatura — não adicionar a coluna nesse caso, ou o modelo fica sem identificabilidade/aliasing espúrio).

   ```python
   def montar_matriz_modelo(df_codificado, fatores_ordenados, termos):
       X = pd.DataFrame(index=df_codificado.index)
       X["Intercept"] = 1.0
       for termo in termos:                     # ordem = ordem de declaração
           if ":" in termo:
               a, b = termo.split(":")
               X[termo] = df_codificado[a] * df_codificado[b]
           elif "^" in termo:
               base, _ = termo.split("^")
               X[termo] = df_codificado[base] ** 2
           else:
               X[termo] = df_codificado[termo]
       return X
   ```

4. **Ajuste OLS**:
   ```python
   import statsmodels.api as sm
   X = sm.add_constant(X, has_constant="raise")   # 'raise' pega bug de intercepto duplicado
   modelo = sm.OLS(y, X).fit()                    # method='pinv' é o default (Moore-Penrose)
   ```

5. **Checagem de posto/colinearidade — ANTES do fit, como validação explícita**, porque `sm.OLS.fit()` com `pinv` **não lança erro** em matriz rank-deficiente (retorna solução de norma mínima silenciosamente):
   ```python
   rank = np.linalg.matrix_rank(X.values)
   if rank < X.shape[1]:
       raise ValueError(f"Matriz de modelo com posto deficiente: rank={rank}, colunas={X.shape[1]}")
   cond = np.linalg.cond(X.values)   # complementar — detecta quase-colinearidade, que matrix_rank não pega
   ```
   Opcional: VIF por termo com `variance_inflation_factor(sm.add_constant(X).values, idx)` — **lembrar de somar a constante antes**, senão a definição de R² da regressão auxiliar muda (issues #2376/#6249 do próprio statsmodels).

### Armadilhas específicas do LYRA

- **`x1**2` numa fórmula patsy NÃO é potenciação** — é o operador de "crossing" (expansão de interação). Nunca gerar fórmula patsy sem passar por `I()`. Isso só importa no modelo sombra (item 0); o modelo canônico nem usa fórmula, então essa armadilha é evitada por construção.
- **Não confundir `resolução`/`aliasing` de fatorial fracionado com um 2^k completo** — o 2^k completo não tem relação definidora nenhuma; todos os `2^k - 1` efeitos são mutuamente independentes. Não implemente lógica de resolução (III/IV/V) achando que se aplica ao caso completo.
- **Codificar SEMPRE em unidades naturais → ±1 antes de montar termos quadráticos/interação.** Ajustar em unidades naturais (não codificadas) infla VIF artificialmente por multicolinearidade estrutural (correlação entre `x` e `x²` só por causa da escala/origem não centrada) — a codificação centraliza e resolve isso "de graça".
- **Ordem de declaração dos fatores tem que ser a mesma em todo o pipeline** (codificação → matriz → nomes de coluna → validação). Qualquer inconsistência de ordem entre o dataclass de entrada e as colunas da matriz de modelo produz um casamento de nomes errado na validação (a), silenciosamente — não dependa de ordenação implícita de `dict`/`set`.
- Se optar por `patsy.dmatrix()` só para prototipagem, **nunca** deixe esse caminho vazar para produção sem renomear as colunas explicitamente.

---

## 2. Issue #4 — `core/anova`

### O que implementar

1. **ANOVA Tipo II** via o modelo sombra descrito na seção 0:
   ```python
   import statsmodels.formula.api as smf
   from statsmodels.stats.anova import anova_lm

   modelo_sombra = smf.ols(build_formula(termos), data=df_codificado).fit()
   tabela_anova = anova_lm(modelo_sombra, typ=2)   # DataFrame: sum_sq, df, F, PR(>F)
   tabela_anova.index = [traduzir_para_canonico(t) for t in tabela_anova.index]
   ```
   **Documente no docstring por que Tipo II foi escolhido**: respeita marginalidade (efeito principal não é ajustado pelas interações que o envolvem), não depende da ordem de entrada dos termos (ao contrário do Tipo I), e tem maior poder estatístico que o Tipo III quando não há evidência forte de interação (Langsrud 2003, apoiado na crítica de Nelder & Lane 1995 ao Tipo III). Em desenho ortogonal/balanceado (2^k completo sem exclusão de corridas) Tipo I=II=III coincidem — a escolha só importa de fato quando o desenho perde ortogonalidade (réplicas desiguais em pontos centrais, exclusão de outlier, ou correlação estrutural entre `x1` e `x1^2` em CCD/BBD).

2. **Seleção de termos / redução do modelo — backward elimination com hierarquia obrigatória**:
   - α = 0,05 fixo e documentado explicitamente como parâmetro nomeado da função (nunca valor mágico solto) — é o alfa que a validação (b) do §4.3 vai comparar.
   - A cada passo: identificar o termo não-forçado com maior p-valor > α. **Antes de remover**, checar se ele é "pai" de algum termo ainda presente (`x1` é pai de `x1:x2` e de `x1^2`). Se for pai de um termo significativo, **não remover**, mesmo com p-valor alto — passar para o próximo candidato.
   - Reajustar (recalcular ANOVA Tipo II) a cada remoção e repetir até estabilizar.
   - Filtro final de sanidade: para cada termo de ordem superior remanescente, garantir que todos os termos de ordem inferior que ele implica estejam no modelo, reinserindo-os se faltarem.
   - Registrar no `AnalysisResult` um campo por termo, ex. `retained_reason: "significant" | "hierarchy"` — a camada narrative precisa dessa distinção para não inventar uma justificativa (ex.: "x1 foi mantido porque a interação x1:x2 é significativa", nunca decidido pelo LLM).

   ```python
   def backward_elimination_hierarquico(termos, X, y, alpha=0.05):
       ativos = list(termos)
       while True:
           anova = ajustar_e_anova(X[["Intercept"] + ativos], y)  # Tipo II
           candidatos = [t for t in ativos if anova.loc[t, "PR(>F)"] > alpha
                         and not eh_pai_de_termo_significativo(t, ativos, anova, alpha)]
           if not candidatos:
               break
           pior = max(candidatos, key=lambda t: anova.loc[t, "PR(>F)"])
           ativos.remove(pior)
       return reinserir_termos_hierarquicos_faltantes(ativos, termos)
   ```

3. **Teste de falta de ajuste (lack-of-fit)** — **não existe pronto em statsmodels**, precisa ser montado à mão:
   - Exige `point_id` (identificador da combinação exata de níveis codificados) preservado desde a leitura em `io/` (ver seção #9) — agrupar por proximidade numérica de float é errado.
   - Se não houver nenhuma combinação com réplica genuína (setup independente repetido, não medição repetida da mesma corrida), retornar explicitamente "teste não aplicável — desenho sem réplicas", nunca calcular com 0 graus de liberdade.

   ```python
   def teste_falta_de_ajuste(df, y_col, point_id_col, modelo_ajustado, p_params):
       grupos = df.groupby(point_id_col)[y_col]
       if grupos.size().max() < 2:
           return None  # sem réplicas -> não aplicável
       sspe = sum(((g - g.mean()) ** 2).sum() for _, g in grupos)
       n_obs, m_pontos = len(df), grupos.ngroups
       df_pe = n_obs - m_pontos
       sse = modelo_ajustado.ssr
       sslof = sse - sspe
       df_lof = m_pontos - p_params
       F = (sslof / df_lof) / (sspe / df_pe)
       from scipy.stats import f as f_dist
       p_valor = f_dist.sf(F, df_lof, df_pe)   # sf, não 1-cdf (precisão na cauda)
       return {"SSLOF": sslof, "df_LOF": df_lof, "SSPE": sspe, "df_PE": df_pe, "F": F, "p_valor": p_valor}
   ```

### Armadilhas específicas do LYRA

- **`anova_lm` com múltiplos modelos (comparação aninhada) só suporta `typ=1`** — a própria função lança erro se você pedir `typ=2`/`3` passando dois modelos. Para a comparação modelo-reduzido-vs-completo do backward elimination, rode `anova_lm(modelo_único, typ=2)` a cada passo, não a variante de dois modelos.
- **Tipo II não é apropriado quando há interação significativa presente** para interpretar os efeitos principais envolvidos — se o modelo final retiver uma interação significativa, documente essa ressalva no `AnalysisResult` em vez de reportar o p-valor Tipo II do efeito principal como se fosse a última palavra.
- **Fixar a versão do statsmodels** (`pyproject.toml`) — a API e o formato de retorno de `anova_lm` já mudaram entre versões 0.9–0.15; não assumir a doc da versão mais recente sem checar a instalada.
- **`p_params` no teste de falta de ajuste é o número de parâmetros do modelo REDUZIDO final** (pós-seleção de termos), não do modelo completo original — erro comum de trocar as contagens.
- **α=0,05 tem que ser o mesmo em toda a pipeline** (seleção de termos e teste de falta de ajuste) e igual ao software de referência usado na validação (b) — não deixar 0,05 num lugar e 0,10 (comum como "alfa de remoção" em alguns softwares comerciais) em outro sem justificar.

---

## 3. Issue #5 — `core/effects`

### O que implementar

1. **Coeficientes, erro-padrão, IC** — extraídos direto do **modelo canônico** de #3 (nunca do modelo sombra, cujos nomes de coluna não batem):
   ```python
   coefs = modelo_canonico.params        # index = nomes canônicos exatos
   erros = modelo_canonico.bse
   pvals = modelo_canonico.pvalues
   ic = modelo_canonico.conf_int(alpha=0.05)   # IC 95% por padrão
   ```

2. **Efeito clássico de Yates** a partir do coeficiente — só para **efeitos principais lineares em desenho 2^k com fatores codificados ±1**:
   ```python
   efeito_xi = 2 * coefs["x1"]
   ```
   Justificativa: com preditor codificado em `{-1,+1}`, `Δx = 2`, então `Efeito = Δy = coef · Δx = 2·coef`. **Essa relação de fator 2 é específica de efeitos principais de desenho de 2 níveis** — não aplique cegamente a termos quadráticos (`x1^2`) ou de interação de CCD/BBD; ali o coeficiente OLS já é a grandeza a reportar diretamente (o coeficiente de interação, na convenção clássica de Yates, também corresponde a metade do "efeito de interação", mas documente essa distinção explicitamente no docstring em vez de aplicar o `2×` de forma genérica em todos os termos).

3. **Exposição no `AnalysisResult`**: para cada termo, reportar coeficiente, efeito (quando aplicável), erro-padrão, IC 95%, p-valor — tudo indexado pelo nome canônico exato, serializável em JSON.

### Armadilhas específicas do LYRA

- **Não confundir "efeito" com "coeficiente de regressão"** — são convenções diferentes por um fator de 2. Misturar as duas ao relatar magnitude é o erro mais citado na literatura pesquisada. Deixe explícito na estrutura de saída qual dos dois cada campo representa.
- **A relação `efeito = 2×coef` pressupõe fatores codificados em ±1.** Se por algum motivo um valor não-codificado vazar até aqui, a relação quebra silenciosamente — trave isso com uma asserção (`assert X[termo].min() == -1 and X[termo].max() == 1` para termos lineares de fatorial 2 níveis) antes de calcular o efeito.
- Esta issue depende 100% da matriz canônica de #3 e da lista de termos retidos por #4 (pós-seleção) — não recalcule nada aqui, só extraia e formate.

---

## 4. Issue #6 — `core/desirability`

### O que implementar

1. **Funções de desejabilidade individual** (Derringer & Suich, 1980), puras e vetorizadas:
   ```python
   def d_max(y, A, B, s=1.0):
       d = np.where(y < A, 0.0, np.where(y > B, 1.0, ((y - A) / (B - A)) ** s))
       return np.clip(d, 0.0, 1.0)

   def d_min(y, A, B, s=1.0):
       d = np.where(y > B, 0.0, np.where(y < A, 1.0, ((y - B) / (A - B)) ** s))
       return np.clip(d, 0.0, 1.0)

   def d_target(y, A, T, B, s1=1.0, s2=1.0):
       d = np.where((y < A) | (y > B), 0.0,
           np.where(y <= T, ((y - A) / (T - A)) ** s1, ((y - B) / (T - B)) ** s2))
       return np.clip(d, 0.0, 1.0)
   ```
   `s`, `s1`, `s2` são hiperparâmetros do experimentador — expor como parâmetros públicos com default `1.0`, nunca hardcoded escondido.

2. **Desejabilidade composta (média geométrica)**, com proteção contra `log(0)`:
   ```python
   def D_global(d_list, weights=None):
       d = np.asarray(d_list)
       w = np.ones_like(d) if weights is None else np.asarray(weights)
       if np.any(d == 0):
           return 0.0
       return np.exp(np.sum(w * np.log(d)) / np.sum(w))
   ```
   Propriedade de veto: `D=0` se qualquer `d_i=0` — documente isso, e **alerte explicitamente no `AnalysisResult`** quando o `D` ótimo encontrado for 0 ou muito próximo disso (indica faixas `[A,B]` mal calibradas cobrindo região inteira inviável), em vez de devolver silenciosamente um "ótimo" sem significado.

3. **Busca do ótimo — grid para k≤4, Hipercubo Latino para k>4** (issue #6 original):
   ```python
   from scipy.stats import qmc
   from scipy.optimize import minimize

   SEED_FIXO = 42   # constante do módulo — NUNCA time-based, NUNCA os.urandom

   def gerar_pontos_iniciais(k, l_bounds, u_bounds, n_grid_por_eixo=5):
       if k <= 4:
           malha = np.meshgrid(*[np.linspace(lo, hi, n_grid_por_eixo)
                                  for lo, hi in zip(l_bounds, u_bounds)])
           return np.column_stack([m.ravel() for m in malha])
       else:
           n = max(10 * k, 40)   # regra prática Loeppky/Sacks/Welch 2008 — documentar como escolha de engenharia
           sampler = qmc.LatinHypercube(d=k, optimization="random-cd", seed=SEED_FIXO)
           amostra_unit = sampler.random(n)
           return qmc.scale(amostra_unit, l_bounds, u_bounds)

   def otimizar_desejabilidade(D_func, k, l_bounds, u_bounds):
       pontos = gerar_pontos_iniciais(k, l_bounds, u_bounds)
       valores = [D_func(p) for p in pontos]
       melhores_idx = np.argsort(valores)[-5:]   # multi-start a partir dos 5 melhores
       resultados = [minimize(lambda x: -D_func(x), pontos[i], method="Nelder-Mead")
                     for i in melhores_idx]
       return max(resultados, key=lambda r: -r.fun)
   ```
   `scipy.optimize.minimize(..., method="Nelder-Mead")` — obrigatório usar busca direta (sem gradiente): `D` tem quinas (não-diferenciável) em `A`, `B`, `T` de cada `d_i`.

4. **Registrar metadados de reprodutibilidade no `AnalysisResult`**: método usado (`grid` vs `lhs`), `n`, `seed`, esquema de otimização — a camada `narrative` precisa poder mencionar honestamente como o ótimo foi obtido, e a validação (d) do §4.3 (diferença na condição ótima) **não é reprodutível entre execuções sem isso**.

### Armadilhas específicas do LYRA

- **Tensão com "core sem aleatoriedade":** `LatinHypercube` usa gerador pseudoaleatório internamente. Isso só permanece determinístico se `seed` for **sempre** fixo e explícito — trate a ausência de seed como bug de arquitetura, não como detalhe de implementação. Escreva um teste que roda a mesma chamada duas vezes e assere igualdade bit-a-bit da amostra gerada.
- **LHS não é otimizador, é gerador de sementes de partida.** Nunca reporte o melhor ponto da amostra LHS crua como "ótimo" — sempre refine com Nelder-Mead a partir de multi-start, exatamente como a prática documentada do pacote R `desirability` (grid de reinício + `optim()`).
- **Não reaproveite os pontos da amostra LHS como malha de *visualização*** (issue #10) — `go.Surface`/`go.Contour` exigem `z` como array 2D regular; LHS não é regular. A malha de otimização e a malha de visualização são dois `meshgrid`s independentes.
- **A relação de `2^k grid` vs `10k` amostras LHS cresce muito diferente:** `k=6` com 5 níveis por eixo = 15.625 pontos de grid vs. 60 pontos LHS — não hardcode o limiar `k>4` sem revalidar contra o custo real de avaliação de `D` no LYRA (função barata de avaliar, então o gargalo real é a explosão combinatória, não o custo por ponto).
- **Não existe fonte revisada por pares comparando LHS vs. grid especificamente para qualidade do ótimo de Derringer-Suich** — trate `n=10k` como escolha de engenharia documentada, não como resultado garantido da literatura; para os casos `k≤4` do próprio conjunto de testes, rode grid E LHS e compare o ótimo encontrado como validação cruzada interna antes de confiar no LHS para `k>4` (onde o grid deixa de ser viável para comparar).
- Distinga claramente da issue #6 original (malha de *otimização*) da armadilha de #4 (falta de ajuste) e #3 (matriz de *projeto*) — são três "malhas" diferentes no vocabulário do LYRA, não confundir nomeação entre elas no código.

---

## 5. Notas — Issue #9 (`io/`)

- **Preservar `point_id`** (identificador da combinação exata de níveis codificados de cada ensaio) desde a leitura do CSV até `core/anova` — é indispensável para o teste de falta de ajuste (#4) agrupar réplicas corretamente. Não deduzir réplicas por comparação de float.
- **Preservar a ordem de declaração dos fatores** exatamente como veio da configuração/CSV de entrada — é a mesma ordem que define a notação canônica de termos em #3/#4/#5. Não depender de ordenação implícita de `dict`/`DataFrame.columns` sem fixá-la explicitamente numa lista ordenada carregada de configuração.
- Validar na leitura: réplica genuína (setup independente) vs. medição repetida da mesma corrida — se o formato de entrada não distingue isso, documentar a limitação e expor um alerta no `AnalysisResult` em vez de assumir silenciosamente que toda linha repetida é réplica válida para erro puro.
- Para desenhos com pontos centrais/axiais (CCD/BBD), garantir que a leitura reconheça o nível `0` (ponto central) distintamente de um nível intermediário qualquer, já que a decisão de incluir/excluir a coluna `x1^2` na matriz de modelo (#3) depende disso.

---

## 6. Notas — Issue #10 (`ui/app`, Streamlit + Plotly)

- **Formulário dinâmico de k fatores** (bounds `low`/`high` por fator, k só conhecido após upload do CSV): gerar em loop com `key` única e estável por fator, ex. `key=f"low_{dataset_id}_{factor.name}"` (incluir `dataset_id` no prefixo evita colisão de estado se dois datasets tiverem fator com mesmo nome). `st.data_editor` não resolve — só cobre número variável de *linhas*, não de *colunas*. Se precisar validar `low < high` ao vivo por fator, use `st.fragment` (Streamlit ≥1.37) em vez de `st.form` — widgets dentro de `st.form` não disparam callback entre si antes do submit.
- **Visualização de superfície/desejabilidade** com `k>2` fatores: **sempre** dois fatores por vez (`go.Surface` 3D ou `go.Contour` 2D), com os `k-2` fatores restantes fixados no ponto ótimo encontrado em #6. Nunca tentar plotar as `k` dimensões numa visualização só. Ofereça dois `st.selectbox` para o usuário escolher o par de fatores.
- **Gere a malha de plotagem com `np.meshgrid` próprio e fino**, reavaliando o modelo canônico (#3) e a função de desejabilidade (#6) ponto a ponto — nunca reaproveite diretamente os pontos de uma amostra LHS como `z` de `go.Surface`/`go.Contour` (exigem grade 2D regular).
- Para o mapa de desejabilidade: `go.Contour(..., contours=dict(start=0, end=1, size=0.1))` (D está sempre em `[0,1]` por definição) e marque o ponto ótimo global com `go.Scatter`/`go.Scatter3d` sobreposto.
- Essa integração Plotly+Derringer-Suich não tem exemplo oficial pronto na documentação — é decisão de engenharia própria do LYRA; vale documentar explicitamente essa escolha no TCC.

---

## 7. Checklist cruzado com a validação §4.3

| Item de validação | Issue responsável | O que garante |
|---|---|---|
| (a) erro relativo de coeficientes ≤5%, casado por nome exato | #3, #5 | matriz de modelo canônica com nomes fixos, sem depender de patsy |
| (b) concordância de significância a α=0,05 | #4 | ANOVA Tipo II + backward elimination hierárquico, α documentado e único em todo o pipeline |
| (c) diferença de R²/R² ajustado ≤0,01 | #3, #4 | teste de regressão comparando `ssr`/`rsquared` do modelo canônico vs. sombra |
| (d) diferença na condição ótima | #6 | seed fixo do LHS + multi-start Nelder-Mead + metadados de reprodutibilidade registrados |
| (e) fidelidade do relatório do LLM (classificação manual) | narrative (fora de escopo aqui) | depende de #3-#6 exporem `retained_reason`, efeito vs. coeficiente, e alertas de `D≈0` de forma explícita no `AnalysisResult`, para o LLM narrar sem inventar |