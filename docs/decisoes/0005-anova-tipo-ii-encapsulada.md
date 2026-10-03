# 0005 — ANOVA Tipo II encapsulada em `AjusteOLS`, com autocheck em runtime

**Status:** Aceita · **Data:** 2026-08-24

## Contexto

`core/anova.py` já promete, no próprio docstring de `tabela_anova`, implementar
via `statsmodels.stats.anova.anova_lm(typ=2)` (TODO(#4)). E `core/model.py` já
promete, no docstring de `ajustar_ols`, guardar "o objeto de resultado
inteiro — a ANOVA e o teste de falta de ajuste precisam dos resíduos e da
matriz de covariância" (TODO(#3)). As duas intenções já estavam certas antes
desta ADR existir: um `AjusteOLS` só, usado tanto por #3/#5 quanto por #4.

O problema que uma leitura ingênua desses dois TODOs esconde: `anova_lm(typ=2)`
só sabe montar a tabela Tipo II a partir de um modelo ajustado pela API de
fórmula do statsmodels (`smf.ols("y ~ x1 + x2", ...)`) — é da fórmula que ela
lê a estrutura de termos (quem é marginal a quem) que o cálculo Tipo II
precisa. Mas a matriz de projeto do LYRA é montada à mão (`matriz_modelo`, #3),
com nomes de coluna na notação canônica (`"x1^2"`, `"x1:x2"`) que a validação
do §4.3(a) usa para casar coeficiente por nome — e um `sm.OLS(y, X).fit()`
sobre essa matriz não carrega a "receita" de fórmula que `anova_lm` precisa.

Ou seja: satisfazer os dois TODOs ao pé da letra, sem mais nenhuma decisão,
levaria a implementar dois ajustes — um canônico (para #3/#5) e um por
fórmula (só para alimentar `anova_lm` em #4) — como duas saídas públicas
paralelas. Isso funciona, mas exporia ao resto do sistema uma costura frágil
entre duas representações do "mesmo" modelo, cuja consistência dependeria de
alguém lembrar de testá-la a cada mudança no núcleo.

## Decisão

O ajuste por fórmula não é uma segunda saída pública — é um detalhe de
implementação **interno a `AjusteOLS`** (issue #3), que já existe no desenho
atual exatamente "para que o resto do LYRA não importe statsmodels
diretamente".

1. `ajustar_ols(X, y)` constrói o ajuste canônico (`sm.OLS(y, X).fit()`) e,
   internamente, também constrói o ajuste por fórmula equivalente — traduzindo
   a notação canônica dos termos para sintaxe patsy por uma função pura e
   determinística (`"x1^2" -> "I(x1**2)"`, `"x1:x2"` já é válido como está),
   nunca por fórmula digitada solta.
2. Na construção, `AjusteOLS` compara `ssr` e `rsquared` dos dois ajustes e
   **levanta exceção imediatamente** se divergirem além de uma tolerância de
   ponto flutuante. A garantia de que "canônico" e "sombra" são o mesmo
   ajuste deixa de ser um teste que alguém precisa lembrar de rodar — vira um
   invariante checado toda vez que o sistema roda, em qualquer caso de
   estudo, não só nos que têm teste unitário escrito.
3. `tabela_anova(ajuste, tipo=2)` (issue #4) chama um método do próprio
   `AjusteOLS` (ex. `ajuste.tabela_tipo2()`) que roda `anova_lm` sobre o ajuste
   por fórmula interno e traduz o índice de volta para notação canônica antes
   de devolver. Fora de `model.py`, nada no LYRA sabe que existe um segundo
   ajuste.

## Consequências

**Boas**

- Reaproveita `anova_lm`, uma função testada por uma base de usuários enorme,
  em vez de implementar Tipo II do zero — menos matemática estatística
  nossa para validar contra a literatura.
- A costura canônico↔sombra vira invisível para #4 e #5: quem lê
  `core/anova.py` ou `core/effects.py` não precisa saber que ela existe.
- A checagem de consistência é automática e acontece em produção, não só em
  CI — se um bug de tradução aparecer, ele quebra alto, na hora, com os
  dados reais que o expuseram, não seis meses depois num caso de estudo que
  ninguém rodou de novo.

**Ruins, e assumidas**

- Cada ajuste custa duas chamadas ao `OLS` do statsmodels em vez de uma —
  irrelevante em tempo de execução para os tamanhos de dados de DOE, mas é
  trabalho duplicado que existe só por causa de uma limitação de API do
  statsmodels, não por necessidade estatística.
- A função de tradução canônico→patsy é código nosso e precisa de teste
  próprio (`tests/unit/test_model.py` ou equivalente) cobrindo termo linear,
  quadrático e de interação — se ela tiver um bug, o autocheck de SSR/R²
  pega quase todo mundo, mas não uma tradução que por acaso preserva SSR
  (caso degenerado, improvável, mas não impossível de descartar sem teste).

## Adendo (2026-09-03) — validado contra dado real, um risco a mais encontrado

Prototipagem contra um CCD real (17 ensaios, estágio do Gustavo) confirmou o
autocheck de SSR/R² funcionando (divergência ~1e-13). Mas achou um segundo
risco que este documento não cobria: a tradução canônico→patsy que gera a
fórmula (`"x1^2" -> "I(x1**2)"`) é fácil de acertar; a tradução **de volta**
(patsy→canônico, para nomear as linhas da tabela ANOVA) é fácil de errar,
porque o patsy re-formata a expressão ao guardar o nome da coluna —
`"I(x1**2)"` na fórmula de entrada volta como `"I(x1 ** 2)"` (com espaços) em
`ajuste_sombra.model.exog_names`. Uma tradução reversa por string literal
falha em silêncio: o termo não traduzido continua existindo na tabela, só com
o nome errado — mesmo tipo de falha silenciosa que o resto desta ADR já tenta
evitar, só que no rótulo, não no número.

**Correção:** nunca re-derivar o nome patsy por string própria na volta.
Construir o mapa de tradução reversa a partir dos nomes REAIS devolvidos por
`ajuste_sombra.model.exog_names` (posicionalmente, na mesma ordem dos termos
da fórmula), e adicionar uma segunda asserção, além do SSR/R²: o conjunto de
nomes traduzidos tem que ser exatamente igual ao conjunto de termos
esperados (`set(traduzidos) == set(termos)`) — se sobrar um nome não
traduzido, falhar alto, nunca deixar o nome patsy cru vazar pra fora de
`AjusteOLS`.

### Como ficou implementado (2026-09-21, issue #3)

- A tradução de volta **não é posicional**: o patsy reordena termos por grau e
  não garante a ordem dos fatores numa interação. O mapa reverso usa uma chave
  normalizada (sem espaços; fatores de uma interação em ordem alfabética) e as
  duas pontas passam pela mesma normalização.
- Os fatores vão para a fórmula como aliases `f0`, `f1`, ... — nomes reais como
  `Tempo (min)` ou `Razão S/L` não são identificadores válidos numa fórmula.
- Além de SSR, R² e do conjunto de nomes, o autocheck compara **cada
  coeficiente pelo nome traduzido**. Conjunto de nomes igual não pega dois
  termos com rótulos trocados; coeficientes diferentes pegam.
- Modelo não hierárquico (fator sem termo linear) ajusta normalmente, mas
  `tabela_tipo2()` falha alto: a fórmula sombra não tem como ser montada.
- Observação empírica no CCD do estágio (17 ensaios): Tipo II, Tipo III e o
  teste-t do coeficiente deram p-valores idênticos em todos os termos, porque
  num delineamento simétrico os efeitos principais são ortogonais às
  interações. Virou teste de invariante (`test_em_delineamento_simetrico_...`);
  não muda a decisão desta ADR, mas quebra se um delineamento perder a simetria
  (ensaio removido) e o tipo de ANOVA passar a importar.

## Alternativa descartada

**Calcular Tipo II na mão, sem `anova_lm` e sem fórmula nenhuma.** Dá para
fazer — para cada termo T, comparar a soma de quadrados residual do modelo
completo com a do modelo sem T (mantendo os termos que não contêm T), tudo
em cima da matriz canônica. Eliminaria o ajuste-sombra por completo. Foi
descartada como *decisão padrão* porque troca uma função testada por código
estatístico nosso que teria que ser validado do zero contra um caso com ANOVA
publicada (o caso de estudo de CCD da tilosina serviria para isso). Fica
registrada como caminho de fallback: se o autocheck de SSR/R² um dia se
provar inviável de manter (por exemplo, se um desenho futuro não tiver
tradução direta para fórmula patsy), este é o caminho a seguir — não uma
correção improvisada em cima da encapsulação.
