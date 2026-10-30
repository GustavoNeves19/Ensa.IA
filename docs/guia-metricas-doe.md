# Guia completo do EnsaIA: métricas, variáveis, opções e modelos de DOE

> **Para que serve este documento.** É uma referência de estudo de Planejamento de
> Experimentos (DOE) escrita a partir do que o EnsaIA **realmente calcula**: cada
> fórmula, limiar e regra aqui descritos são os do código do núcleo
> (`src/ensaia/core/`), não uma descrição genérica de livro. Use-o para estudar
> com um assistente de IA.
>
> **Sugestão de pedido para o Claude:** *"Use este documento como referência.
> Quero aprender DOE do zero. Me explique um tópico por vez, com exemplos
> numéricos, e me faça uma pergunta no fim de cada um para ver se entendi.
> Quando eu errar, explique de novo de outro jeito. Comece pela seção 2."*

---

## Sumário

1. [O que é o EnsaIA e o fluxo de uma análise](#1-o-que-é-o-ensaia-e-o-fluxo-de-uma-análise)
2. [Conceitos fundamentais de DOE](#2-conceitos-fundamentais-de-doe)
3. [Entrada de dados e mapeamento das colunas](#3-entrada-de-dados-e-mapeamento-das-colunas)
4. [Codificação dos fatores](#4-codificação-dos-fatores)
5. [Identificação do planejamento](#5-identificação-do-planejamento)
6. [Os modelos (linear, com interações, quadrático)](#6-os-modelos-linear-com-interações-quadrático)
7. [O ajuste por mínimos quadrados (OLS)](#7-o-ajuste-por-mínimos-quadrados-ols)
8. [Opções do modelo](#8-opções-do-modelo)
9. [Catálogo de análises (A1 a E5)](#9-catálogo-de-análises-a1-a-e5)
10. [Indicadores da primeira leitura](#10-indicadores-da-primeira-leitura)
11. [Melhor condição (otimização)](#11-melhor-condição-otimização)
12. [Prever uma condição](#12-prever-uma-condição)
13. [Próximos passos sugeridos](#13-próximos-passos-sugeridos)
14. [Dicas na tela e texto com IA](#14-dicas-na-tela-e-texto-com-ia)
15. [Exemplo resolvido: fotodegradação de levofloxacino](#15-exemplo-resolvido-fotodegradação-de-levofloxacino)
16. [Tabela-resumo de fórmulas e notação](#16-tabela-resumo-de-fórmulas-e-notação)
17. [Armadilhas comuns](#17-armadilhas-comuns)
18. [Roteiro de estudo e perguntas para praticar](#18-roteiro-de-estudo-e-perguntas-para-praticar)

---

## 1. O que é o EnsaIA e o fluxo de uma análise

O EnsaIA analisa e otimiza **experimentos químicos planejados** (DOE) e explica o
resultado em linguagem simples. Ele tem duas camadas separadas:

- **Núcleo estatístico determinístico** (`core/`): faz todas as contas (regressão,
  ANOVA, efeitos, diagnóstico, superfície, otimização). Mesmo dado → mesmo
  resultado, sempre. Não usa rede nem IA.
- **Camada de linguagem** (`ai/`): só *narra* os números que o núcleo produziu.
  **A IA narra, mas não calcula.** Todo número que aparece num texto gerado por
  IA é conferido contra o resultado do núcleo (ver seção 14).

### Os sete passos do fluxo

| Passo | O que acontece |
|---|---|
| 1. Enviar | Você envia a planilha (ou abre um exemplo publicado). |
| 2. Conferir | O EnsaIA mostra a leitura dos dados (prévia, separador, decimal). |
| 3. Mapear | Você diz qual coluna é fator, resposta, ordem ou "não usar". |
| 4. Analisar | Escolhe as análises e as opções do modelo e clica em Analisar. |
| 5. Ver | Tabelas e gráficos por resposta (abas Efeitos, ANOVA, Diagnóstico, Superfície). |
| 6. Explicar | Texto do relatório (sem IA ou com IA). |
| 7. Baixar | Relatório em PDF e resultados em JSON. |

### Limites do sistema

- Arquivo de até **5 MB**; até **10.000 linhas**.
- Até **7 fatores** e **5 respostas** por análise.
- O modelo precisa deixar **pelo menos 1 grau de liberdade** para o resíduo
  (menos termos do que ensaios).

---

## 2. Conceitos fundamentais de DOE

### Fator (variável independente)
O que você **controla** no experimento: temperatura, pH, tempo, dose de
catalisador, concentração. No EnsaIA aparece no grupo **"Variáveis
Independentes"**.

### Nível
O valor que um fator assume num ensaio. Num fatorial de 2 níveis há o nível
baixo e o alto; num Box-Behnken, três níveis (baixo, centro, alto); num composto
central, cinco (−α, −1, 0, +1, +α).

### Resposta (variável dependente)
O que você **mede** no fim de cada ensaio: rendimento, eficiência de remoção,
pureza, tempo. No EnsaIA aparece no grupo **"Variáveis Dependentes"**. É o que o
modelo tenta explicar.

### Ensaio (corrida, experimento)
Uma linha da planilha: uma combinação de níveis dos fatores e a(s) resposta(s)
medida(s) nela.

### Réplica (repetição genuína)
Repetir a **mesma condição** (os mesmos níveis de todos os fatores) em ensaios
independentes. É a única forma de medir o **erro puro**: a variação da resposta
que não vem dos fatores, e sim do próprio experimento (medição, amostra,
operador). Na prática de DOE, as réplicas costumam ser os **pontos centrais**.

### Ponto central
Ensaio com todos os fatores no nível do meio (0 na escala codificada). Repetido
algumas vezes, serve para: (1) estimar o erro puro; (2) testar se a resposta faz
curva (teste de curvatura); (3) testar falta de ajuste.

### Ordem de execução
A ordem em que os ensaios foram de fato realizados. Fazer os ensaios em ordem
aleatória protege contra efeitos do tempo (equipamento esquentando, reagente
envelhecendo). Se a planilha traz essa ordem, o EnsaIA desenha os resíduos na
ordem de execução para procurar deriva (ver D3).

### Região experimental
A "caixa" coberta pelos níveis estudados. O modelo só vale com segurança dentro
dela. Fora dela o modelo **extrapola** e a previsão pode não valer.

### Modelo
Uma equação que descreve a resposta em função dos fatores, por exemplo:

```
ŷ = b₀ + b₁x₁ + b₂x₂ + b₁₂x₁x₂ + b₁₁x₁² + b₂₂x₂²
```

`ŷ` (lê-se "y chapéu") é a resposta **prevista** pelo modelo; `y` é a resposta
**observada**; os `b` são os **coeficientes**, estimados a partir dos dados.

### Termo
Cada parcela da equação. Tipos:
- **Intercepto** (`b₀`): o valor previsto no centro da região (todos os fatores em 0).
- **Linear** ou **efeito principal** (`b₁x₁`): quanto a resposta muda com um fator.
- **Interação** (`b₁₂x₁x₂`): quando o efeito de um fator depende do nível de outro.
- **Quadrático** (`b₁₁x₁²`): curvatura, ou seja, a resposta faz curva (máximo ou mínimo) ao longo do fator.

No código, os termos têm uma notação própria: `x` (linear), `x^2` (quadrático),
`a:b` (interação). Na tela aparecem como `x`, `x²` e `a × b`.

### Significância e p-valor
O **p-valor** é a probabilidade de observar um efeito tão grande (ou maior) **só
por acaso**, se na verdade o efeito fosse zero. Se `p < α`, o termo é
**significativo**: o efeito é grande demais para ser só ruído.

### α (nível de significância)
O limite para o p-valor. α = 0,05 significa aceitar 5% de risco de declarar um
efeito que não existe (erro tipo I). O EnsaIA oferece 0,05 (padrão) e 0,10.

### Graus de liberdade (gl)
Quantas informações independentes sobram para estimar algo. Com `n` ensaios e
`p` parâmetros no modelo (contando o intercepto), sobram `n − p` graus de
liberdade para o resíduo. Sem gl no resíduo não há erro-padrão, nem t, nem
p-valor.

---

## 3. Entrada de dados e mapeamento das colunas

### Formatos aceitos
CSV, TSV, TXT (texto), XLSX, XLS (Excel antigo) e ODS (LibreOffice).

- Planilhas são lidas **somente leitura**: fórmulas e macros nunca são
  executadas; vale o valor calculado que está salvo no arquivo.
- Em planilhas com várias abas, o EnsaIA pula abas vazias (capa, instruções) e
  usa a primeira com dados; dá para trocar a aba.
- Em arquivos de texto, o EnsaIA **detecta** o separador de colunas (vírgula,
  ponto e vírgula, tabulação ou barra), o separador decimal (vírgula ou ponto) e
  a codificação de caracteres (ex.: UTF-8). O separador pode ser trocado na tela
  ("Trocar separador").
- O arquivo nunca é gravado em disco: fica só na memória da sessão.

### Os quatro papéis de uma coluna (mapeamento)

| Grupo na tela | Papel | Significado |
|---|---|---|
| Variáveis Dependentes | `resposta` | O que foi medido; o modelo explica. |
| Variáveis Independentes | `fator` | O que foi controlado; entra no modelo. |
| Ordem dos ensaios | `ordem` | Ordem de execução (só para o gráfico D3). Só uma coluna. |
| Não usar | `ignorar` | Fica fora da análise. Colunas de texto ficam sempre aqui. |

### Sugestão automática (o ponto de partida)
Antes de você mexer, o EnsaIA sugere:
1. Colunas de **texto** → Não usar.
2. Coluna cujo nome lembra ensaio/ordem (`ensaio`, `exp`, `experimento`, `run`,
   `ordem`, `corrida`, `n`, `nº`…) **e** cujos valores são exatamente 1, 2, …, n
   → Ordem dos ensaios.
3. A **última** coluna numérica (que não seja ordem) → Resposta.
4. As demais numéricas → Fatores.

Você corrige arrastando os cartões entre os grupos (ou clicando e escolhendo).

---

## 4. Codificação dos fatores

### O que é
Reescrever cada fator numa escala comum, em que o nível baixo vira **−1**, o
alto vira **+1** e o centro vira **0**:

```
x (codificado) = (X − centro) / meia-amplitude

centro         = (nível alto + nível baixo) / 2
meia-amplitude = (nível alto − nível baixo) / 2
```

E o caminho inverso: `X = x · meia-amplitude + centro`.

**Exemplo:** dose de catalisador estudada de 0,5 a 1,5 g/L.
centro = 1,0; meia-amplitude = 0,5. Então 0,5 → −1; 1,0 → 0; 1,5 → +1.
Um valor de 3,0 g/L daria x = (3,0 − 1,0)/0,5 = **+4**, muito fora da região.

### Por que codificar
1. **Comparabilidade:** fatores com unidades diferentes (pH, g/L, minutos) passam
   a ter a mesma escala, então o tamanho do coeficiente mostra a importância do
   fator.
2. **Estabilidade numérica:** em unidades reais, os termos quadráticos e de
   interação ficam muito correlacionados com os lineares, o que infla os
   erros-padrão e faz efeitos reais parecerem não significativos.
3. **Padrão da literatura:** os artigos publicam os coeficientes codificados.

### Como o EnsaIA descobre o −1 e o +1 (sozinho, a partir dos dados)

| Quantos níveis o fator tem | Como define ±1 |
|---|---|
| 2 ou 3 | ±1 = menor e maior valor. |
| 5 (composto central) | ±1 = 2º e 4º níveis em ordem; os extremos são ±α. O α é medido. |
| Já em −1/0/+1 (ou ±α simétrico) | A planilha já está codificada; fica como está. |
| Outra quantidade | Usa menor e maior e **avisa**. |

**Por que isso importa no composto central:** se o EnsaIA tomasse o mínimo e o
máximo como ±1 num composto central, a escala encolheria por um fator α. A ANOVA
e as previsões não mudariam, mas todos os coeficientes ficariam numa escala
diferente da publicada, e a comparação com o artigo perderia o sentido.

Avisos possíveis: níveis axiais não simétricos em torno do centro; nível central
que não fica no meio dos níveis ±1; fator com um único nível (não dá para
estimar efeito: deve ir para "Não usar").

A análise **A3 (Matriz real e codificada)** mostra lado a lado os valores reais e
os codificados de cada ensaio.

---

## 5. Identificação do planejamento

O EnsaIA reconhece o tipo de planejamento **pela geometria dos pontos** na escala
codificada, e não pela contagem de níveis (um Box-Behnken e um fatorial 3ᵏ, por
exemplo, têm os mesmos 3 níveis). Cada ensaio é classificado como:

| Tipo de ponto | Coordenadas codificadas | Onde aparece |
|---|---|---|
| Vértice | todas em ±1 | fatoriais e parte fatorial do composto central |
| Axial (estrela) | uma em ±α (α ≥ 1), as outras 0 | composto central |
| Aresta | exatamente duas em ±1, as outras 0 | Box-Behnken |
| Centro | todas em 0 | quase todos (pontos centrais) |

(Tolerância de 0,02 na escala codificada, para absorver arredondamento das planilhas.)

### Os tipos reconhecidos

**Fatorial completo 2ᵏ**
- Todas as 2ᵏ combinações de dois níveis de k fatores (ex.: 3 fatores → 8 vértices),
  com ou sem pontos centrais.
- Uso: **triagem** (descobrir quais fatores importam).
- Modelo natural: linear com interações. Não estima curvatura de cada fator
  (só testa se há curvatura geral, com pontos centrais: B5).

**Fatorial fracionado 2ᵏ⁻ᵖ**
- Só uma fração regular dos vértices (potência de 2, colunas balanceadas, ou seja,
  cada coluna soma zero). Ex.: 2⁵⁻¹ = 16 ensaios em vez de 32.
- Custa menos ensaios, mas alguns efeitos ficam **confundidos** (*aliased*): não
  dá para separá-los. O EnsaIA retira do modelo os termos que são combinação
  linear de outros e avisa.

**Delineamento composto central (DCC, DCCR)**
- Fatorial (vértices) + pontos axiais (estrela, em ±α) + pontos centrais.
- Cinco níveis por fator. Permite ajustar o **modelo quadrático**.
- **α rotacional** = (número de vértices)^(1/4). Ex.: k = 2 → 4 vértices → α = 1,414;
  k = 3 → 8 vértices → α = 1,682. Rotacional quer dizer que a precisão da
  previsão depende só da distância ao centro.
- **Face centrada:** α = 1 (os axiais ficam na face do cubo; 3 níveis por fator).
- O EnsaIA avisa se α não é nem rotacional nem 1, se faltam pontos axiais
  (deveriam ser 2k distintos) ou se a parte fatorial está incompleta.
- **Região experimental:** vai até ±α (os axiais fazem parte da região estudada).

**Box-Behnken (BBD)**
- Três níveis por fator, **sem os vértices do cubo**: os pontos ficam no meio das
  arestas (dois fatores em ±1, o resto em 0) + pontos centrais.
- Exige k ≥ 3. Também ajusta o modelo quadrático, com menos ensaios que o composto
  central e sem ensaios em condições extremas (todos os fatores no máximo ao mesmo
  tempo).
- Ex.: 3 fatores → 12 pontos de aresta + pontos centrais (15 ensaios com 3 centrais).

**Fatorial 3ᵏ**
- Todas as 3ᵏ combinações de {−1, 0, +1} (réplicas permitidas).

**Desconhecido (genérico)**
- A disposição não bate com nenhum tipo. A análise segue normalmente, mas sem as
  ferramentas específicas de cada planejamento, e o EnsaIA avisa.

A análise **A2 (Identificação do planejamento)** mostra o tipo reconhecido, o nº de
ensaios, o nº de pontos centrais e o α axial (no composto central).

---

## 6. Os modelos (linear, com interações, quadrático)

### Os três tipos de modelo

```
Linear:          ŷ = b₀ + Σ bᵢxᵢ
Com interações:  ŷ = b₀ + Σ bᵢxᵢ + Σ bᵢⱼxᵢxⱼ
Quadrático:      ŷ = b₀ + Σ bᵢxᵢ + Σ bᵢⱼxᵢxⱼ + Σ bᵢᵢxᵢ²
```

- **Linear:** cada fator age sozinho e em linha reta. Serve para triagem; não
  enxerga interação nem curvatura.
- **Com interações:** soma o efeito combinado de cada **par** de fatores
  (interações de 2ª ordem). É o modelo natural dos fatoriais de 2 níveis.
- **Quadrático (segunda ordem):** soma a curvatura de cada fator. Permite achar um
  máximo ou mínimo **dentro** da região. Exige **3 ou mais níveis por fator**.

Número de termos com k fatores (com intercepto): linear = 1 + k; interações = 1 +
k + k(k−1)/2; quadrático = 1 + 2k + k(k−1)/2. Ex.: k = 3 → 4, 7 e 10 termos.

### Regras do modo "Automático"

1. Fatorial completo ou fracionado (2 níveis, mesmo com pontos centrais) →
   **com interações**. Motivo: com pontos centrais o fator tem 3 valores (−1, 0,
   +1), mas todas as colunas x² são iguais (1 nos vértices, 0 no centro), então
   não dá para estimar a curvatura de **cada** fator; a curvatura é avaliada pelo
   teste próprio (B5).
2. Se **todos** os fatores têm 3 ou mais níveis (Box-Behnken, composto central,
   3ᵏ) → **quadrático**.
3. Senão → **com interações**.

### Outras regras de montagem do modelo

- **Termos quadráticos só para fatores com 3+ níveis.** Com 2 níveis, x² é uma
  coluna de 1 (igual ao intercepto) e não há curvatura a estimar. Pedir
  "Quadrático" com todos os fatores em 2 níveis vira "Com interações", com aviso.
- **Rebaixamento automático:** se não há ensaios suficientes para o modelo pedido
  (é preciso termos < ensaios), o EnsaIA desce um nível (quadrático → interações
  → linear) e avisa. Se nem o linear cabe, a análise é recusada.
- **Termos confundidos:** se a coluna de um termo é combinação linear das
  anteriores (a matriz fica singular), o termo sai do modelo e há aviso. Causas
  comuns: fatorial fracionado; termo quadrático num fatorial sem centros/axiais.
- **Intercepto é obrigatório:** sem ele, R² e ANOVA mudam de definição.
- **Hierarquia:** um modelo é *hierárquico* quando todo fator que aparece numa
  interação ou num quadrático também tem o seu termo linear. Modelo não
  hierárquico faz os coeficientes dependerem da codificação (de onde se pôs o
  zero) e deixa a ANOVA Tipo II indisponível. O EnsaIA avisa quando isso acontece
  (por exemplo, se você tirar à mão o termo linear de um fator que está numa
  interação).

---

## 7. O ajuste por mínimos quadrados (OLS)

### A matriz do modelo
Cada termo vira uma coluna de uma matriz **X** (n ensaios × p termos), calculada
com os fatores **codificados**: intercepto = coluna de 1; `x` = coluna
codificada; `x^2` = quadrado dela; `a:b` = produto das duas.

### A estimativa dos coeficientes

```
b = (XᵀX)⁻¹ Xᵀy          (mínimos quadrados ordinários)
ŷ = X b                  (valores previstos)
e = y − ŷ                (resíduos)
SQres = Σ eᵢ²            (soma de quadrados do resíduo)
QMres = SQres / (n − p)  (quadrado médio do resíduo = variância estimada do erro)
SQtotal = Σ (yᵢ − ȳ)²
```

"Mínimos quadrados" porque esses coeficientes são os que tornam a soma dos
quadrados dos resíduos a menor possível.

O EnsaIA verifica antes se **X tem posto cheio** (nenhuma coluna é combinação das
outras). Se não tiver, recusa com mensagem clara, em vez de devolver coeficientes
sem sentido.

### Erro-padrão, t e p de cada coeficiente

```
EP(bⱼ) = √( QMerro · [(XᵀX)⁻¹]ⱼⱼ )
t = bⱼ / EP(bⱼ)
p = 2 · P(T > |t|),  T ~ t de Student com gl do erro
significativo se p < α
```

`QMerro` é o do **resíduo** (padrão) ou o do **erro puro** (opção do modelo).

### Intervalo de confiança de cada coeficiente

```
IC(1 − α) = bⱼ ± t(1 − α/2; gl do erro) · EP(bⱼ)
```

Se o intervalo não contém zero, o termo é significativo (é a mesma decisão do p-valor).

### Coeficiente × efeito (a armadilha mais comum)

- **Coeficiente** (`b`): quanto a resposta muda do **centro (0) ao nível alto (+1)**.
- **Efeito** (de Yates): quanto a resposta muda do **nível baixo (−1) ao alto (+1)**,
  ou seja, o dobro do caminho.

```
Efeito = 2 · b       (EP do efeito = 2 · EP(b); t e p são os mesmos)
```

Isso vale para efeitos principais lineares e interações em escala ±1. **Não**
vale para termos quadráticos (de −1 a +1, x² vai de 1 a 1: não há "efeito" de
Yates; a curvatura é lida pelo coeficiente). Alguns artigos publicam efeitos,
outros coeficientes. Antes de comparar números, confira qual dos dois cada fonte usa.

---

## 8. Opções do modelo

Ficam no card **"Opções do modelo"**, antes de Analisar. O cabeçalho mostra a
escolha atual (ex.: "Modelo automático · resíduo · α = 0,05").

### 8.1 Termos do modelo
Automático, Linear, Com interações ou Quadrático (seção 6).

### 8.2 Termo de erro: resíduo × erro puro
É o "denominador" dos testes t e F dos termos.

- **Resíduo** (padrão; é o padrão do Minitab):
  ```
  QMres = SQres / (n − p)
  ```
  Tudo o que o modelo não explica. Funciona mesmo sem réplicas.

- **Erro puro** (comum no Statistica e em artigos brasileiros):
  ```
  SQep = Σ_grupos Σ (y − média do grupo)²     (grupo = ensaios com os mesmos níveis)
  gl_ep = n − m                               (m = nº de condições distintas)
  QMep = SQep / gl_ep
  ```
  Só a variação entre réplicas. Exige réplicas genuínas. Se não houver réplicas,
  ou se as réplicas forem idênticas, o EnsaIA **volta para o resíduo e avisa**.

O que muda com o erro puro: o erro-padrão, o t, o p-valor e o IC de cada
coeficiente, e o F de cada termo na ANOVA Tipo II. **Não muda:** os coeficientes,
o R², a ANOVA da regressão (que sempre usa QMres) nem as previsões.

**Para reproduzir um artigo, use o mesmo termo de erro que ele usou.** É a causa
mais comum de p-valores que "não batem".

### 8.3 Nível de significância (α)
0,05 (padrão; é o critério da maioria dos artigos) ou 0,10 (mais tolerante, comum em
triagem com poucos ensaios, quando perder um fator importante custa mais do que
incluir um a mais). α afeta: quais termos são significativos, o t crítico do
Pareto, o F tabelado, a falta de ajuste, a normalidade, a curvatura e a
simplificação.

### 8.4 Simplificar o modelo (eliminação *backward*)
Quando ligado, para cada resposta:

```
repita:
  ajuste o modelo e calcule o p-valor de cada termo (ANOVA Tipo II, com o
  termo de erro escolhido)
  entre os termos com p ≥ α que podem sair, remova o de MAIOR p
  (não pode sair o termo linear de um fator que ainda está numa interação
   ou num quadrático — hierarquia)
até não sobrar termo removível
```

Cada resposta pode terminar com termos diferentes. Os termos removidos aparecem
numa nota ("Removidos pela redução: …").

### 8.5 Ajustar termos (depois da análise)
No card **"Ajustar termos"** dos resultados, cada termo é uma pílula: verde = no
modelo; tracejada e riscada = fora. Você tira ou devolve termos à mão e clica em
**Reajustar** para ver os indicadores mudarem. O resumo conta o intercepto (ex.:
"9 de 10 termos no modelo · fora: ph²").

---

## 9. Catálogo de análises (A1 a E5)

As análises ficam em **cinco etapas** (dropdowns): Dados, Triagem, Modelo,
Diagnóstico e Otimização. As compatíveis com os seus dados vêm incluídas; as que
não se aplicam ficam apagadas, **com o motivo escrito**. O que fica de fora sai da
tela e do PDF (o núcleo calcula o que é barato de qualquer jeito).

### Pré-condições (quando cada análise "não se aplica")

| Situação dos dados | Análises afetadas | Motivo mostrado |
|---|---|---|
| Nenhum fator ou nenhuma resposta | todas | escolha ao menos um fator / uma resposta |
| n ≤ k + 1 (ensaios não bastam nem para o linear) | B1–B4 e todo C, D, E | ensaios não bastam |
| Planejamento não é fatorial de 2 níveis | B1, B3, B4, B5 | só para fatorial de 2 níveis |
| Fatorial **com** réplicas | B3 | com réplicas o erro é estimado direto (use o Pareto) |
| Menos de 2 pontos centrais | B5 | exige ao menos 2 ensaios no ponto central |
| Sem réplicas | C4 | exige réplicas (em geral, pontos centrais) |
| Menos de 3 ensaios | D2 | exige ao menos 3 ensaios |
| Sem coluna de ordem | D3 | arraste a coluna de ordem para "Ordem dos ensaios" |
| Menos de 2 fatores | E1, E2 | exige ao menos 2 fatores |
| Fatorial ou algum fator com < 3 níveis | E3 | exige modelo quadrático |
| Menos de 2 respostas | E5 | exige ao menos 2 respostas |

---

### Etapa 1 — Dados: "O que foi feito no experimento?"

#### A1 · Estatística descritiva
Resumo de cada resposta **antes** de qualquer modelo.

```
n, média ȳ = Σyᵢ / n
desvio-padrão amostral s = √[ Σ(yᵢ − ȳ)² / (n − 1) ]
mínimo, máximo
CV (%) = 100 · s / |ȳ|        (não calculado se a média é zero)
```

**Como ler:** o coeficiente de variação (CV) mostra quanto a resposta variou
entre os ensaios em relação à média. CV muito baixo já sugere que os fatores
mexeram pouco na resposta.

#### A2 · Identificação do planejamento
Ver seção 5.

#### A3 · Matriz real e codificada
Tabela com cada ensaio: nível real e, entre parênteses, o codificado. Serve para
conferir que a codificação está certa (que os ±1 são os níveis que você planejou).

---

### Etapa 2 — Triagem: "Quais fatores importam?"
(Para fatoriais de 2 níveis, exceto o Pareto, que vale para todos.)

#### B1 · Efeitos principais e interações
Tabela dos efeitos (Efeito = 2·b), com erro-padrão, p-valor e significância,
ordenados pelo tamanho. Efeito positivo: subir o fator aumenta a resposta.

#### B2 · Pareto dos efeitos padronizados
Gráfico de barras com **|t|** de cada termo, do maior para o menor, e uma linha
tracejada no **t crítico**:

```
t crítico = t(1 − α/2; gl do erro)
barra que passa da linha  ⇔  p < α  ⇔  termo significativo
```

É a forma mais rápida de ver quais termos importam. Na tela, **clicar numa barra**
abre a superfície daquele termo (uma interação a × b abre a superfície com a e b
nos eixos). Sem gl no erro não há linha de corte.

#### B3 · Gráfico meio-normal (método de Lenth)
Para fatoriais **sem réplicas** (sem erro puro, não há teste t confiável). Supõe
que a maioria dos efeitos é ruído e estima um "pseudo erro-padrão" a partir dos
próprios efeitos:

```
s₀  = 1,5 · mediana(|efeitos|)
PSE = 1,5 · mediana( |efeitos| que são < 2,5·s₀ )
ME  = t(0,975; m/3) · PSE                 (margem de erro)
SME = t(γ; m/3) · PSE, γ = (1 + 0,95^(1/m)) / 2   (margem simultânea)
m = nº de efeitos; precisa de m ≥ 3
```

Um efeito é **ativo** se `|efeito| > ME`. No gráfico, os efeitos são postos
contra o quantil meio-normal esperado `Φ⁻¹(0,5 + 0,5·(i − 0,5)/m)`: os que são só
ruído se alinham perto da origem; os ativos se afastam para a direita da linha
tracejada (ME).

#### B4 · Gráficos de efeito e de interação
- **Efeitos principais:** a média da resposta em cada nível de cada fator,
  calculada **só com os vértices** (pontos centrais ficam de fora), todos na mesma
  escala. Linha mais inclinada = fator mais importante.
- **Interação:** para a interação mais forte, uma linha por nível do segundo fator.
  Linhas **paralelas** = os fatores agem cada um por si; linhas que **se abrem ou
  se cruzam** = o efeito de um depende do nível do outro.

  ```
  Efeito AB = [ȳ(A+,B+) − ȳ(A−,B+) − ȳ(A+,B−) + ȳ(A−,B−)] / 2
  ```

#### B5 · Teste de curvatura
Com pontos centrais num fatorial, compara a média dos vértices com a do centro.
Se o centro foge do que um plano preveria, a resposta faz curva.

```
SQcurv = n_F · n_C · (ȳ_F − ȳ_C)² / (n_F + n_C)
F = SQcurv / QMep          gl = (1, gl_ep)
F = vértices (fatorial);  C = centro
```

Exige pelo menos 2 pontos centrais com variação (erro puro > 0). **Curvatura
significativa** → o modelo linear não basta: amplie para um composto central ou
um Box-Behnken.

---

### Etapa 3 — Modelo: "O modelo explica a resposta?"

#### C1 · Ajuste do modelo (coeficientes)
Tabela de cada termo: estimativa, erro-padrão, t, p-valor (e IC). Ver seção 7.
Sinal positivo: o termo aumenta a resposta; negativo: diminui.

#### C2 · ANOVA
Duas tabelas.

**ANOVA da regressão** (formato da literatura de DOE):

| Fonte | SQ | gl | QM | F |
|---|---|---|---|---|
| Regressão | SQR = SQT − SQres | p − 1 | SQR/(p−1) | QMR / QMres |
| Resíduo | SQres | n − p | SQres/(n−p) | |
| ↳ Falta de ajuste | SQfaj = SQres − SQep | (n−p) − (n−m) | | QMfaj / QMep |
| ↳ Erro puro | SQep | n − m | | |
| Total | SQT | n − 1 | | |

(As linhas de falta de ajuste e erro puro só aparecem quando há réplicas.)

- **p da regressão < α** → o modelo, como um todo, explica a resposta além do acaso.
- **Critério F calculado / F tabelado** (Barros Neto, Scarminio e Bruns; muito usado
  em artigos brasileiros):
  ```
  F tabelado = F(1 − α; p − 1, n − p)
  razão = F calculado / F tabelado    → maior que 1: regressão significativa
  ```
  (Alguns autores exigem razão bem maior que 1, por exemplo > 4 ou 10, para
  considerar o modelo útil para previsão; o EnsaIA mostra a razão e usa > 1 como
  critério de significância.)

**ANOVA Tipo II (efeito de cada termo):**
Para cada termo `t`:

```
SQ(t) = SQres(modelo sem t e sem os termos que CONTÊM t)
      − SQres(o mesmo modelo com t de volta)
F(t) = SQ(t) / QMerro       gl = (1, gl do erro)
```

"Conter": `a:b` contém `a`; mas `a²` **não** contém `a` (é tratado como um átomo
próprio). A Tipo II mede a contribuição de cada termo **depois** dos outros do
mesmo nível, respeitando a hierarquia. Só existe para modelos hierárquicos.

#### C3 · R², R² ajustado e R² de predição

```
R²     = 1 − SQres / SQT
R²aj   = 1 − [SQres/(n − p)] / [SQT/(n − 1)]
R²pred = 1 − PRESS / SQT,   PRESS = Σ [eᵢ / (1 − hᵢᵢ)]²
```

- **R²:** fração da variação da resposta explicada pelo modelo (0 a 1). Sozinho
  engana: todo termo a mais aumenta o R², mesmo que seja inútil.
- **R² ajustado:** o R² descontado pelo número de termos. Se cai muito em relação
  ao R², o modelo tem termos demais para a quantidade de ensaios.
- **R² de predição:** quanto o modelo acerta um ensaio que ele **não viu** (cada
  ensaio é previsto pelo modelo ajustado sem ele: isso é o PRESS, *Prediction Sum
  of Squares*). Muito abaixo do R² ajustado = o modelo **decorou** os dados
  (sobreajuste). **Negativo** = prevê pior que simplesmente usar a média
  (sinal de "atenção" na tela). Fica indefinido se algum ensaio tem hᵢᵢ = 1.
- Regra prática comum na literatura: R²aj e R²pred devem estar "razoavelmente
  próximos" (diferença menor que ~0,2).

#### C4 · Falta de ajuste
Compara o erro do modelo com o erro puro das réplicas:

```
F = QMfaj / QMep = [SQfaj / (m − p)] / [SQep / (n − m)]
```

- **Não significativa (p ≥ α): o desejável.** O desvio do modelo é do tamanho do
  ruído experimental; a forma do modelo acompanha a resposta.
- **Significativa (p < α):** o modelo não descreve bem a forma da resposta. Tente
  um modelo de ordem maior ou um planejamento com mais níveis.
- **Não aplicável** quando não há réplicas genuínas, ou quando o modelo não deixa
  gl para a falta de ajuste (termos demais para o nº de pontos distintos). O
  EnsaIA diz "não aplicável", e **nunca** "não houve falta de ajuste", nesses casos.

#### C5 · Equação do modelo
Três formas, em botões:

- **Codificada:** `ŷ = 53,48 + 7,025·X₁ − 7,538·X₂ + …`, com X₁, X₂… = fatores
  codificados. É a que os artigos publicam; dá para comparar o peso dos termos.
- **Só significativos:** a codificada só com os termos significativos (sem
  reajustar o modelo).
- **Unidades reais:** a mesma superfície reescrita nas unidades do laboratório,
  substituindo `Xⱼ = (xⱼ − centroⱼ)/meia-amplitudeⱼ` e expandindo os produtos (os
  coeficientes mudam de valor, mas as previsões são idênticas). Use para calcular
  a resposta direto com os valores do laboratório.

Os números saem com vírgula decimal e 4 algarismos significativos. O botão
"Copiar equação" copia a forma escolhida.

#### C6 · Previsto × observado
Gráfico com um ponto por ensaio: valor previsto (ŷ) contra observado (y), com a
reta `y = x`. Ponto sobre a reta = ensaio que o modelo acerta; quanto mais longe,
maior o erro naquele ensaio.

---

### Etapa 4 — Diagnóstico: "Dá para confiar no modelo?"

Os testes do modelo supõem que os erros são **independentes**, de **variância
constante** e aproximadamente **normais**. Um R² alto não garante nada disso; o
padrão dos resíduos é o que mostra se os p-valores merecem confiança.

#### D1 · Resíduos × previsto
`eᵢ = yᵢ − ŷᵢ` contra `ŷᵢ`. Os pontos devem se espalhar **ao acaso** em torno do
zero.
- **Funil** (espalhamento que cresce com ŷ) → variância não constante
  (heterocedasticidade); uma transformação da resposta (log, raiz) pode ajudar.
- **Curva** → falta um termo (o modelo deixou uma forma de fora).

#### D2 · Normalidade dos resíduos (Q-Q e Shapiro-Wilk)
- **Gráfico Q-Q:** os resíduos ordenados contra o quantil normal esperado, com
  posições de **Blom** (as do Minitab):
  ```
  z = Φ⁻¹[(i − 3/8) / (n + 1/4)]
  ```
  A reta de referência passa pelos quartis. Pontos perto da reta = resíduos
  normais; desvios nas pontas = caudas fora do normal.
- **Teste de Shapiro-Wilk:** `W = (Σ aᵢ·e₍ᵢ₎)² / Σ(eᵢ − ē)²`. **p < α** → há
  indício de que os resíduos **não** são normais (leia os p-valores com cautela).
  Exige ≥ 3 ensaios; não roda se os resíduos são todos iguais (ajuste exato).

#### D3 · Resíduos × ordem de execução
Resíduos na ordem em que os ensaios foram feitos (exige a coluna de ordem). Eles
**não** devem subir ou descer aos poucos: tendência indica **deriva** do
equipamento, do reagente ou do operador ao longo do tempo.

#### D4 · Pontos influentes
Para cada ensaio:

```
Alavancagem         hᵢᵢ = diagonal de X(XᵀX)⁻¹Xᵀ   (quão "isolado" o ponto é no espaço dos fatores)
Resíduo studentizado interno   rᵢ = eᵢ / √(QMres · (1 − hᵢᵢ))
Distância de Cook   Dᵢ = rᵢ² · hᵢᵢ / [p · (1 − hᵢᵢ)]   (quanto o ajuste inteiro mudaria sem o ensaio)
R-student (externo) tᵢ = rᵢ · √[(n − p − 1) / (n − p − rᵢ²)]
```

Regras do EnsaIA:
- **Ensaio influente:** `Dᵢ > 1` **e** `hᵢᵢ > 2p/n` (o dobro da alavancagem média).
  Só "Cook > 1" não serve em DOE: num fatorial todos os vértices têm alavancagem
  alta, e a regra dispararia em ensaios comuns.
- **Possível outlier:** `|tᵢ| > 3` (R-student). O externo detecta melhor que o
  interno quando a alavancagem é alta, porque o ensaio fica fora da estimativa do
  erro.

O que fazer: conferir esses ensaios no caderno de laboratório (erro de execução
ou de anotação?). A tabela "Valores por ensaio" mostra observado, previsto,
resíduo, alavancagem, resíduo studentizado e Cook de cada ensaio.

---

### Etapa 5 — Otimização: "Qual é a melhor condição?"

#### E1 · Superfície de resposta 3D e E2 · Curvas de contorno
A resposta **prevista pelo modelo** quando dois fatores variam e os demais ficam
fixos (por padrão no centro; dá para ajustar com controles deslizantes):

```
ŷ(x₁, x₂) com os demais fatores fixos
grade de 25 × 25 pontos cobrindo a região
```

- **3D:** a resposta como um relevo (picos, vales, selas); dá para girar.
- **Contorno:** o mesmo relevo visto de cima; cada linha liga condições com a
  mesma resposta. Anéis fechados indicam um máximo ou mínimo; linhas que se abrem
  em "X" indicam sela.
- O par de eixos inicial é o da **interação mais forte** (maior |t|) ou, sem
  interações, os dois fatores mais fortes.

#### E3 · Ponto estacionário (análise canônica)
Onde a superfície fica **plana** (o gradiente zera). Escrevendo o modelo
quadrático em forma matricial:

```
ŷ = b₀ + xᵀb + xᵀBx
b = vetor dos coeficientes lineares
B = matriz com os quadráticos na diagonal e METADE de cada interação fora dela

ponto estacionário:  xₛ = −½ · B⁻¹ · b
resposta nele:       ŷₛ = b₀ + ½ · xₛᵀ b
```

A **natureza** vem dos autovalores de B:
- todos negativos → **máximo**;
- todos positivos → **mínimo**;
- sinais misturados → **ponto de sela** (sobe numa direção e desce noutra; a melhor
  resposta fica na borda da região).

O EnsaIA também diz se o ponto cai **dentro da região** estudada. Exige o termo
quadrático de **todos** os fatores; com B singular, não há ponto estacionário.

#### E4 · Otimização de uma resposta e E5 · Desejabilidade
Ver seção 11.

---

## 10. Indicadores da primeira leitura

Logo no topo de cada resposta, um quadro **só para leitura** resume o modelo. O
sinal é um ícone ao lado do valor: ✓ = bom sinal, ⚠ = pede atenção. Nenhum
indicador cria limiar novo: cada sinal é uma decisão que o núcleo já tomou ao
nível α.

| Indicador | Bom sinal (✓) | Pede atenção (⚠) | Sem sinal |
|---|---|---|---|
| R² | — | — | sempre informativo |
| R² ajustado | — | — | sempre informativo |
| R² de predição | — | negativo | caso contrário, informativo |
| Regressão | p < α | p ≥ α | |
| Falta de ajuste | p ≥ α | p < α | não aparece sem réplicas |
| Normalidade dos resíduos | Shapiro p ≥ α | p < α | não aparece sem o teste |
| Ensaios influentes | nenhum | lista os ensaios | |

---

## 11. Melhor condição (otimização)

Para cada resposta você escolhe a **meta**: Maximizar, Minimizar, Atingir um alvo
(digita o valor) ou Não otimizar. O EnsaIA procura a combinação de fatores que
melhor atende **dentro da região estudada**.

### Quando a otimização é recusada
Se alguma resposta usada tem **R² < 0,50**, o modelo não descreve os dados bem o
bastante para apontar um ótimo, e a busca não é feita (com aviso).

### Dois métodos

- **E4, uma resposta a maximizar ou minimizar:** otimiza a **própria resposta
  prevista** (não a desejabilidade, que saturaria em 1 e deixaria o ótimo
  indefinido num platô). Método de busca: L-BFGS-B com limites.
- **E5, várias respostas ou uma com alvo:** maximiza a **desejabilidade global**
  de Derringer e Suich. Método de busca: Powell com limites.

### A desejabilidade (Derringer & Suich, 1980)

Cada resposta prevista vira uma nota `dᵢ` entre 0 (inaceitável) e 1 (ideal). Os
limites são os do próprio experimento: **L = menor valor observado** e **U = maior
valor observado** daquela resposta (padrão do Design-Expert). T = alvo; s = forma
(no EnsaIA, s = 1, subida linear).

```
Maximizar:  d = 0 se ŷ ≤ L;   ((ŷ − L)/(U − L))^s se L < ŷ < U;   1 se ŷ ≥ U
Minimizar:  d = 1 se ŷ ≤ L;   ((U − ŷ)/(U − L))^s se L < ŷ < U;   0 se ŷ ≥ U
Alvo T:     d = 0 fora de [L, U]
            ((ŷ − L)/(T − L))^s se L ≤ ŷ ≤ T     (sobe até 1 no alvo)
            ((U − ŷ)/(U − T))^s se T < ŷ ≤ U     (desce depois)
```

- O alvo precisa ficar **estritamente entre** L e U.
- Fora da faixa o valor é **saturado** (nunca passa de 1 nem fica abaixo de 0):
  é isso que torna respostas de escalas diferentes comparáveis.
- **Forma s:** s > 1 exige chegar perto do ideal para d crescer (mais rigoroso);
  0 < s < 1 recompensa qualquer melhora (mais tolerante).

**Desejabilidade global (média geométrica ponderada):**

```
D = (d₁^w₁ · d₂^w₂ · … · dₘ^wₘ)^(1/Σwᵢ)        (no EnsaIA, todos os pesos wᵢ = 1)
```

Média **geométrica**, não aritmética: se **qualquer** resposta for inaceitável
(dᵢ = 0), **D = 0** (veto). Com média aritmética, uma resposta péssima seria
compensada pelas boas, e o otimizador recomendaria uma condição que viola um
requisito. D = 1 = todas as metas plenamente atendidas.

### Como a busca é feita (e por que é reprodutível)
1. Avalia uma **malha** de pontos na região: com 1 fator, 201 pontos; com 2, 41 por
   eixo; com 3, 21 por eixo; com 4, 11 por eixo; com 5 ou mais, 4.000 pontos
   sorteados com semente fixa.
2. Refina localmente a partir dos **5 melhores** pontos da malha.
3. A região é a caixa **[−1, +1]** na escala codificada (**[−α, +α]** no composto
   central).

A busca é determinística: o mesmo dado dá o mesmo ótimo, byte a byte.

### Resultado
Os níveis dos fatores (em unidades reais), a resposta prevista em cada um, a meta
e, com várias respostas, d de cada uma e o D global. **Sempre confirme com um
ensaio** na condição encontrada antes de adotá-la.

---

## 12. Prever uma condição

Você digita os valores dos fatores (nas unidades do laboratório) e o modelo
calcula a resposta, substituindo os valores na equação:

```
ŷ = equação do modelo, com cada fator codificado: x = (X − centro)/meia-amplitude
```

Serve para planejar o próximo ensaio ou conferir o ensaio de confirmação.

**Extrapolação:** se algum fator codificado passar de ±1 (±α no composto
central), a condição está **fora da região estudada**. O EnsaIA mostra um alerta:
o modelo está extrapolando e a previsão pode não valer.

---

## 13. Próximos passos sugeridos

Regras que geram a lista numerada "Próximos passos":

| Situação | Sugestão |
|---|---|
| Regressão não significativa | Revise as faixas dos fatores (talvez estreitas demais) ou inclua outros fatores. |
| Falta de ajuste significativa | Experimente um modelo de ordem maior ou um planejamento com mais níveis. |
| Curvatura significativa (fatorial) | Amplie para um composto central ou um Box-Behnken. |
| Ponto estacionário fora da região ou de sela | A melhor resposta está na borda: desloque a região experimental na direção dela. |
| Ensaios influentes ou outliers | Confira esses ensaios no caderno de laboratório. |
| Melhor condição na borda (coordenada a menos de 0,02 do limite) | Vale estender os níveis nessa direção num novo planejamento. |
| Melhor condição calculada | Faça um ensaio de confirmação nela e compare com a previsão. |
| Há ponto estacionário mas ainda não buscou o ótimo | Use "Encontrar a melhor condição" e depois confirme com um ensaio. |

---

## 14. Dicas na tela e texto com IA

### Modos de dica (seletor abaixo da logo)
- **Sem Dicas:** some com as lâmpadas.
- **Dicas em Texto:** a lâmpada explica o que é e como ler.
- **Dicas em Fórmula:** a lâmpada mostra a fórmula da métrica.

### Texto do relatório (quatro modos)
- **M0 · Sem IA:** um texto fiel montado diretamente dos fatos do núcleo. Sempre
  disponível.
- **M1 · Copiar para a sua IA:** o EnsaIA monta o pedido; você cola numa IA
  qualquer e cola a resposta de volta.
- **M2 · IA local:** Ollama rodando no seu computador.
- **M3 · IA em nuvem:** com a sua chave (Gemini, Groq, OpenAI) ou a IA oferecida
  pelo servidor.

### Fidelidade: a IA narra, mas não calcula
Em todos os modos com IA, **cada número do texto é conferido** contra o resultado
do núcleo. Números sem correspondência ficam marcados em amarelo, e afirmações de
significância que contradizem os p-valores são apontadas. Com IA, todo o texto
vem do modelo: se um parágrafo cita um número fora dos fatos, o modelo tenta de
novo e, se não acertar, o parágrafo fica com o número marcado. Se o modelo não
responder (30 s; 60 s no Ollama), a tela mostra o erro, sem texto do sistema no
lugar.

---

## 15. Exemplo resolvido: fotodegradação de levofloxacino

Caso publicado incluído no EnsaIA (Box-Behnken), com os números que o sistema de
fato produz. Use para treinar a leitura de cada métrica.

### Planejamento
- **Tipo:** Box-Behnken, 3 fatores, **15 ensaios**, **3 pontos centrais**.
- **Fatores (faixa estudada → codificação):**
  - X₁ = dose de catalisador: 0,5 a 1,5 (centro 1,0; meia-amplitude 0,5)
  - X₂ = concentração de levofloxacino: 4 a 10 (centro 7; meia-amplitude 3)
  - X₃ = pH: 4 a 10 (centro 7; meia-amplitude 3)
- **Resposta:** eficiência de fotodegradação (%).
- **Modelo (Automático):** quadrático, **10 termos** (intercepto + 3 lineares + 3
  quadráticos + 3 interações), gl do resíduo = 15 − 10 = **5**.

### Estatística descritiva (A1)
n = 15; média = 53,349; desvio-padrão = 9,758; mínimo = 34,3; máximo = 73,13;
CV = 18,3%.

### Coeficientes (C1), escala codificada, termo de erro = resíduo

| Termo | Estimativa | EP | t | p |
|---|---|---|---|---|
| Intercepto | 53,4833 | 1,5969 | 33,49 | < 0,0001 |
| dose | 7,0250 | 0,9779 | 7,18 | 0,0008 |
| concentração | −7,5375 | 0,9779 | −7,71 | 0,0006 |
| pH | 3,8700 | 0,9779 | 3,96 | 0,0108 |
| dose² | −0,3342 | 1,4394 | −0,23 | 0,8256 |
| concentração² | −0,1192 | 1,4394 | −0,08 | 0,9372 |
| pH² | 0,2008 | 1,4394 | 0,14 | 0,8945 |
| dose × concentração | 5,2250 | 1,3829 | 3,78 | 0,0129 |
| dose × pH | 7,0600 | 1,3829 | 5,11 | 0,0038 |
| concentração × pH | 2,0250 | 1,3829 | 1,46 | 0,2030 |

**t crítico** = t(0,975; 5) = **2,57**. Passam da linha do Pareto: concentração,
dose, dose × pH, pH, dose × concentração (5 termos significativos). Nenhum
quadrático é significativo.

**Leitura:** aumentar a dose aumenta a eficiência; aumentar a concentração do
fármaco diminui; pH alto ajuda; e há interações fortes: o efeito da dose depende
do pH e da concentração.

### ANOVA da regressão (C2)

| Fonte | SQ | gl | QM | F | p |
|---|---|---|---|---|---|
| Regressão | 1294,759 | 9 | 143,862 | 18,81 | 0,0024 |
| Resíduo | 38,251 | 5 | 7,650 | | |
| Falta de ajuste | 17,069 | 3 | 5,690 | 0,54 | 0,7019 |
| Erro puro | 21,181 | 2 | 10,591 | | |
| Total | 1333,009 | 14 | 95,215 | | |

- F tabelado = F(0,95; 9, 5) = 4,77; **razão F/Ftab = 3,94** (> 1: regressão
  significativa).
- gl do erro puro = 2 (3 pontos centrais − 1); gl da falta de ajuste = 5 − 2 = 3.
- Confira: 1294,759 + 38,251 = 1333,010 ≈ 1333,009 (arredondamento); 17,069 +
  21,181 = 38,250 ≈ 38,251.

### Qualidade do ajuste (C3, C4, D2, D4)
- **R² = 0,971** (o modelo explica 97,1% da variação).
- **R² ajustado = 0,920.**
- **R² de predição = 0,759** (diferença para o ajustado ≈ 0,16: aceitável).
- **Falta de ajuste:** p = 0,7019, não significativa (bom).
- **Shapiro-Wilk:** p = 0,4339, sem evidência contra a normalidade.
- **Ensaios influentes:** nenhum.

### Equação (C5)
Codificada:
```
ŷ = 53,48 + 7,025·X₁ − 7,538·X₂ + 3,870·X₃ − 0,3342·X₁² − 0,1192·X₂² + 0,2008·X₃²
    + 5,225·X₁·X₂ + 7,060·X₁·X₃ + 2,025·X₂·X₃
```
Em unidades reais:
```
ŷ = 115,5 − 40,61·dose − 7,385·conc − 5,304·pH − 1,337·dose² − 0,01324·conc²
    + 0,02231·pH² + 3,483·dose·conc + 4,707·dose·pH + 0,2250·conc·pH
```

### Ponto estacionário (E3)
É um **ponto de sela**: a melhor resposta está na borda da região. Por isso a
sugestão de deslocar a região experimental.

### Melhor condição (E4, maximizar)
dose = 1,5; concentração = 4; pH = 10 → eficiência prevista **71,473%**. Todos os
fatores estão na **borda** da região, o que reforça: vale estender os níveis nessa
direção num novo planejamento e fazer um ensaio de confirmação.

### Previsão (seção 12)
- No centro (1; 7; 7): ŷ = 53,483 (= intercepto, como esperado no centro codificado).
- Com dose = 3 (x = +4, fora de ±1): ŷ = 76,237, **com alerta de extrapolação**.

### Exercícios com este exemplo
1. Por que a previsão no centro é exatamente o intercepto?
2. Calcule o efeito (de Yates) da dose a partir do coeficiente. (Resposta: 14,05.)
3. Por que o pH² não é significativo, mas o termo dose × pH é?
4. Se os testes usassem o erro puro (QMep = 10,591, gl = 2) em vez do resíduo
   (QMres = 7,650, gl = 5), duas coisas mudariam: cada erro-padrão seria
   multiplicado por √(10,591/7,650) ≈ 1,177 (então cada t seria dividido por
   1,177), e o t crítico subiria de 2,57 para t(0,975; 2) ≈ 4,30. Quais termos
   deixariam de ser significativos? (Resposta: pH, com t ≈ 3,37, e
   dose × concentração, com t ≈ 3,21. Dose, concentração e dose × pH, com
   t ≈ 4,34, continuariam significativos.)
5. O que significa a razão F/Ftab = 3,94? E se fosse 0,8?

---

## 16. Tabela-resumo de fórmulas e notação

### Notação
| Símbolo | Significado |
|---|---|
| n | nº de ensaios |
| k | nº de fatores |
| p | nº de parâmetros do modelo (com o intercepto) |
| m | nº de condições distintas (na falta de ajuste); nº de efeitos (no Lenth) |
| y, ŷ, ȳ | resposta observada, prevista e média |
| e = y − ŷ | resíduo |
| xᵢ (Xᵢ) | fator codificado (na equação codificada) |
| bⱼ | coeficiente estimado |
| hᵢᵢ | alavancagem do ensaio i |
| SQ, QM, gl | soma de quadrados, quadrado médio (SQ/gl), graus de liberdade |
| α | nível de significância |

### Fórmulas principais
```
Codificação:         x = (X − centro) / meia-amplitude
OLS:                 b = (XᵀX)⁻¹ Xᵀ y
Erro-padrão:         EP(bⱼ) = √(QMerro · [(XᵀX)⁻¹]ⱼⱼ)
Teste t:             t = bⱼ / EP(bⱼ);  significativo se |t| > t(1−α/2; gl)
Efeito de Yates:     Efeito = 2·b
R²:                  1 − SQres/SQT
R² ajustado:         1 − (SQres/(n−p)) / (SQT/(n−1))
R² de predição:      1 − PRESS/SQT;  PRESS = Σ[eᵢ/(1−hᵢᵢ)]²
F da regressão:      (SQR/(p−1)) / (SQres/(n−p))
Razão F/Ftab:        F / F(1−α; p−1, n−p)
Falta de ajuste:     F = [SQfaj/(m−p)] / [SQep/(n−m)]
Erro puro:           SQep = Σ_grupos Σ(y − ȳ_grupo)²;  gl = n − m
Curvatura:           SQcurv = n_F·n_C·(ȳ_F − ȳ_C)²/(n_F+n_C);  F = SQcurv/QMep
Lenth:               s₀ = 1,5·med|e|;  PSE = 1,5·med{|e| < 2,5·s₀};  ME = t(0,975; m/3)·PSE
Studentizado:        rᵢ = eᵢ / √(QMres(1−hᵢᵢ))
Cook:                Dᵢ = rᵢ²·hᵢᵢ / [p(1−hᵢᵢ)];  influente se D > 1 e h > 2p/n
R-student:           tᵢ = rᵢ·√[(n−p−1)/(n−p−rᵢ²)];  outlier se |t| > 3
Q-Q (Blom):          z = Φ⁻¹[(i − 3/8)/(n + 1/4)]
Ponto estacionário:  xₛ = −½·B⁻¹·b;  ŷₛ = b₀ + ½·xₛᵀb
Desejabilidade:      D = (Π dᵢ^wᵢ)^(1/Σwᵢ)
CCD rotacional:      α = (nº de vértices)^(1/4)
```

---

## 17. Armadilhas comuns

1. **Confundir coeficiente com efeito.** Efeito = 2 × coeficiente (em escala ±1).
   Antes de comparar com um artigo, veja qual dos dois ele publicou.
2. **Usar o termo de erro diferente do artigo.** Resíduo × erro puro muda os
   p-valores (com poucos gl de erro puro, o t crítico fica bem maior).
3. **Confiar só no R².** Todo termo a mais aumenta o R². Olhe o ajustado e o de
   predição.
4. **Interpretar "falta de ajuste não aplicável" como "não houve falta de
   ajuste".** Sem réplicas, o teste simplesmente não pode ser feito.
5. **Codificar errado o composto central** (tomar mínimo e máximo como ±1): os
   coeficientes saem numa escala diferente da publicada.
6. **Tirar o termo linear de um fator que está numa interação** (modelo não
   hierárquico): os coeficientes passam a depender da codificação.
7. **Extrapolar:** usar o modelo fora da região estudada.
8. **Adotar o ótimo sem ensaio de confirmação.**
9. **Ignorar o diagnóstico:** resíduos com funil, curva ou não normais tornam os
   p-valores pouco confiáveis.
10. **Chamar de "efeito do fator" um termo confundido** num fatorial fracionado.
11. **Otimizar com um modelo fraco:** o EnsaIA recusa com R² < 0,50 por esse motivo.
12. **Achar que o ponto de sela é o ótimo:** na sela, a melhor resposta está na borda.

---

## 18. Roteiro de estudo e perguntas para praticar

### Roteiro sugerido
1. Conceitos (seção 2) → codificação (4) → tipos de planejamento (5).
2. Modelos (6) → OLS, coeficiente × efeito (7).
3. ANOVA da regressão e Tipo II (C2) → R² (C3) → falta de ajuste (C4).
4. Triagem: Pareto (B2), Lenth (B3), curvatura (B5).
5. Diagnóstico (D1–D4).
6. Superfície, ponto estacionário (E1–E3) → desejabilidade (seção 11).
7. Refaça o exemplo da seção 15 inteiro, interpretando cada número.

### Perguntas para testar o entendimento
1. Por que os fatores são codificados em −1 a +1? Dê duas razões.
2. Num fatorial 2³ com 3 pontos centrais, quantos graus de liberdade tem o erro puro?
3. Qual a diferença entre um composto central rotacional e um de face centrada?
4. Por que um fatorial 2ᵏ com pontos centrais não estima o quadrático de cada fator?
5. O que acontece com o R² ajustado se eu adicionar um termo inútil?
6. Quando o R² de predição fica negativo, o que isso diz sobre o modelo?
7. Por que a falta de ajuste precisa de réplicas?
8. Na ANOVA Tipo II, por que x² não "contém" x, mas a:b contém a?
9. Por que o EnsaIA exige Cook > 1 **e** alavancagem alta para chamar um ensaio de influente?
10. O que os autovalores da matriz B dizem sobre o ponto estacionário?
11. Por que a desejabilidade global é uma média geométrica e não aritmética?
12. Por que o método de Lenth só é usado quando não há réplicas?
13. Se o ótimo cai na borda da região, o que fazer?
14. O que muda e o que não muda ao trocar o termo de erro de resíduo para erro puro?
15. Por que a simplificação (backward) não remove o termo linear de um fator presente numa interação?

---

*Gerado a partir do código do EnsaIA (`src/ensaia/core/`). Se o código mudar, as
fórmulas e limiares deste guia devem ser revistos.*
