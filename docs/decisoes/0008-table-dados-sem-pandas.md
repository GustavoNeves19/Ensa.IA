# 0008 — Contêiner de dados próprio (`Table`), sem pandas no núcleo

**Status:** Aceita · **Data:** 2026-10-03 · **Relacionada:** [0007](0007-nucleo-em-numpy-sem-statsmodels.md)

## Contexto

A [ADR 0007](0007-nucleo-em-numpy-sem-statsmodels.md) tirou o statsmodels da
produção, mas deixou o pandas: `matriz_modelo` devolvia `DataFrame`, `AjusteOLS`
devolvia `Series`, e a leitura de dados usava `pd.read_csv`/`pd.read_excel`.

A especificação (seção 8.1 e princípio P5) pede que o núcleo não dependa de
pandas: os planejamentos de DOE têm dezenas de linhas, e um `DataFrame` custa
dezenas de MB de RAM para o que, aqui, é um punhado de colunas. A leitura por
`csv` da biblioteca padrão mais `openpyxl` cobre o caso sem a dependência.

Remover pandas de uma vez (io + model + effects + runner + todos os testes) seria
uma mudança grande e arriscada para o núcleo estatístico já validado, num único
PR difícil de revisar. Por isso a remoção é **faseada**.

## Decisão

Introduzir uma estrutura de dados própria, **`Table`** (`core/table.py`):
nomes de coluna mais colunas em `numpy` (numéricas) ou `tuple[str, ...]` (texto).
É um contêiner deliberadamente mínimo — sem índice, sem alinhamento automático,
sem operação vetorizada — só o que a leitura, a montagem da matriz do modelo e a
validação precisam.

A remoção do pandas é dividida em duas frentes:

- **3b-i (esta):** `io/readers.py` passa a devolver `Table` (sem pandas), e
  `matriz_modelo` passa a **aceitar** `Table`. O `AjusteOLS` e a *saída* de
  `matriz_modelo` seguem em pandas por ora. Resultado-chave: **nenhum número
  muda** — os JSONs de evidência dos casos ficam byte a byte idênticos, porque o
  motor estatístico não foi tocado. Risco mínimo.
- **3b-ii (próxima):** trocar a interface do `AjusteOLS` por numpy/`dict` e
  remover o pandas de `model.py` e do `runner`, encerrando a dependência.

Só quando a 3b-ii terminar é que o pandas sai do `pyproject` e entra na lista de
proibidos do núcleo no teste de arquitetura — fazer isso antes quebraria o
`model.py`, que ainda o usa.

## Consequências

**Boas**

- `io/` fica livre de pandas já agora; `Table` existe e está testada, abrindo
  caminho para a 3b-ii.
- A mudança é verificável de forma forte: os JSONs dos casos são idênticos, logo
  a plumbing de dados mudou sem afetar nenhum resultado.
- `Table` falha alto e claro: acesso a coluna de texto como numérica, coluna
  inexistente e colunas de tamanhos diferentes viram erro com mensagem útil — o
  oposto do `NaN` silencioso.

**Ruins, e assumidas**

- Durante a 3b-i convivem `Table` (entrada) e `DataFrame` (saída de
  `matriz_modelo`): há uma conversão no meio do `model.py`. É transitório e sai
  na 3b-ii.
- O pandas **ainda é dependência de produção** até a 3b-ii; o ganho pleno de
  memória só se realiza lá.
- `Table` é mínima de propósito; se um dia precisar de mais (junções, filtros),
  reavaliar — mas acrescentar função só quando o uso existir, não antes.

## Alternativas descartadas

- **Remover pandas num PR só.** Maior e mais arriscado para o núcleo já
  validado; a divisão em duas frentes mantém cada passo revisável e verde.
- **Manter pandas como contêiner.** Mais simples, mas contraria o requisito de
  leveza (P5) e a seção 8.1 da spec.
- **Reusar o `AnalysisResult` como contêiner de entrada.** Ele é o contrato de
  *saída* do núcleo (ADR 0001), congelado; sobrecarregá-lo com dados de entrada
  misturaria dois papéis distintos.
