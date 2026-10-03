# 0007 — Núcleo estatístico em numpy puro, statsmodels só como oráculo

**Status:** Aceita · **Data:** 2026-10-03 · **Sucede:** [0005](0005-anova-tipo-ii-encapsulada.md)

## Contexto

A [ADR 0005](0005-anova-tipo-ii-encapsulada.md) resolveu a ANOVA Tipo II
encapsulando o `statsmodels` dentro do `AjusteOLS`: um ajuste canônico sobre a
matriz montada à mão, mais um ajuste "sombra" por fórmula só para chamar
`anova_lm(typ=2)`, com uma camada de tradução de nomes patsy ↔ notação
canônica e autochecagem em runtime. Funcionou e passou nos casos de estudo.

Mas a especificação do sistema (`ESPECIFICACAO.md`, seção 7.4 e princípio P5)
fixou leveza como requisito **medido**: o pacote de produção cabe em 512 MB,
sobe em ≤ 5 s e tem uma lista fechada de dependências. `statsmodels` (que ainda
arrasta `patsy`) é pesado para o uso que o núcleo faz dele — essencialmente um
OLS e uma tabela de ANOVA, que são poucas fórmulas fechadas. A própria 0005
antecipava isto: "Existe para que o resto do EnsaIA não dependa de detalhes do
ajuste: se um dia a implementação mudar, muda aqui e em nenhum outro lugar."
Esse dia chegou.

## Decisão

O ajuste OLS e a ANOVA Tipo II passam a ser calculados em **numpy puro**
(`numpy.linalg` para mínimos quadrados e a inversa de `XᵀX`) com `scipy.stats`
para as distribuições t e F. `statsmodels` e `patsy` saem da dependência de
produção e passam a ser **dependência de teste apenas**, no papel de **oráculo**:
o núcleo é conferido contra eles, mas não os importa.

- `AjusteOLS` mantém exatamente a mesma interface pública (mesmos nomes de
  propriedade, mesmos nomes canônicos de termo, mesmo `tabela_tipo2`). Nada fora
  de `model.py` muda.
- A ANOVA Tipo II é computada pela definição clássica (estilo `car`): para cada
  termo `t`, `SQ(t) = SQ_res(modelo sem t e sem os termos que contêm t) −
  SQ_res(o mesmo modelo com t)`. "Conter" usa a noção de fatores atômicos do
  patsy — `x1:x2` contém `x1`, mas `x1^2` **não** contém `x1` (é um fator
  atômico distinto). Isso reproduz o `anova_lm(typ=2)` sem precisar dele.
- A recusa deliberada a montar Tipo II para modelo não hierárquico (fator em
  termo de ordem superior sem o termo linear) é mantida.
- O teste de arquitetura (`tests/test_arquitetura.py`) passa a proibir
  `statsmodels` dentro de `core/`, travando a decisão no CI.

`pandas` continua em produção por ora, como contêiner de dados na fronteira
(`matriz_modelo` devolve `DataFrame`, `AjusteOLS` devolve `Series`). Removê-lo é
uma frente própria (a estrutura `Table` em numpy da seção 8.1 da spec), separada
para manter esta mudança revisável.

## Consequências

**Boas**

- Uma dependência pesada a menos em produção, coerente com RNF-01/RNF-12.
- As contas ficam transparentes e lê­veis — bom para a monografia, que pode
  mostrar as fórmulas em vez de delegar a uma caixa-preta.
- A camada de tradução patsy ↔ canônico e o ajuste-sombra da 0005 somem: menos
  código e menos superfície de erro.
- A equivalência vira verificável nos dois sentidos: contra o cálculo
  independente em numpy/scipy (`tests/unit/test_model.py`) **e** contra o
  statsmodels como oráculo (`tests/unit/test_oraculo_statsmodels.py`), num design
  não-ortogonal em que a Tipo II de fato difere do teste-t.

**Ruins, e assumidas**

- Os JSONs de evidência dos casos mudaram no ~15º dígito significativo (o
  backend de álgebra linear é outro). As diferenças ficam na ordem de 1e-13
  relativo, muito abaixo das tolerâncias do §4.3 e do oráculo (rel=1e-9); os
  JSONs versionados foram regenerados para refletir o motor que de fato os
  produz.
- Reimplementar a Tipo II à mão transfere para nós a responsabilidade de acertar
  a marginalidade. Mitigado pelo teste-oráculo contra o statsmodels.
- `pandas` ainda está em produção; a leveza plena só chega quando a frente da
  estrutura `Table` for feita.

## Alternativas descartadas

- **Manter o statsmodels (status quo da 0005).** Mais simples, mas contraria o
  requisito de leveza medida e mantém a complexidade do ajuste-sombra.
- **Tirar statsmodels e pandas de uma vez.** Seria uma mudança muito maior
  (reescreve io, model, effects e runner sobre uma estrutura `Table` nova) e num
  único PR difícil de revisar e arriscado para o núcleo já validado. Fica para
  uma frente seguinte.
