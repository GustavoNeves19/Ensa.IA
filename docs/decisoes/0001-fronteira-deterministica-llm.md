# 0001 — O LLM narra, mas não calcula

**Status:** Aceita · **Data:** 2026-08-23

## Contexto

A hipótese de trabalho do TCC, registrada no §4 do pré-projeto, é que um
pipeline de DOE acoplado a uma camada de LLM produz resultados
"estatisticamente equivalentes aos obtidos por softwares com licenças pagas".

Essa afirmação tem um ponto cego. Modelos de linguagem erram aritmética de
formas difíceis de perceber, e erram com fluência: um relatório que diz "o R²
de 0,94 indica bom ajuste" quando o R² real é 0,74 parece perfeitamente
correto para quem não tem o número original à mão — que é exatamente o
usuário-alvo do EnsaIA.

Se o LLM tivesse qualquer participação no cálculo, a equivalência estatística
deixaria de ser demonstrável: cada execução poderia produzir um número
diferente, e a validação do §4.3 mediria o modelo de linguagem, não o
pipeline.

## Decisão

O sistema é dividido em duas camadas com uma fronteira explícita:

1. **`ensaia/core`** calcula tudo. Não importa `langchain`, não faz chamada de
   rede, não lê chave de API. Roda offline e é determinístico.
2. **`ensaia/narrative`** recebe um `AnalysisResult` congelado e produz texto.
   Não importa `numpy`, `pandas`, `statsmodels` nem `scipy`.

`AnalysisResult` (em `core/results.py`) é o único canal entre as duas. É
`frozen` e serializável em JSON — a camada narrativa recebe dado morto.

A fronteira é verificada por `tests/test_arquitetura.py`, que lê o AST de cada
arquivo e falha o CI se um import proibido aparecer.

## Consequências

**Boas**

- A afirmação central do TCC vira verificável: dá para rodar o núcleo sem
  internet e mostrar que os números não dependem do LLM.
- A métrica de fidelidade do §4.3(e) passa a ter sentido: mede exatamente
  quanto o LLM distorce ao *descrever*, isolado de erro de cálculo.
- Trocar de modelo de linguagem não afeta resultado estatístico nenhum.
- `pip install ensaia` sem extras instala uma ferramenta de DOE completa e
  funcional, sem dependência de LLM.

**Ruins, e assumidas**

- Quando o relatório precisa de um número que não está no `AnalysisResult`, o
  conserto é no núcleo, não no prompt. Dá mais trabalho.
- O `AnalysisResult` tende a crescer, e crescer sem critério vira um objeto
  inchado. Contrapartida: só entra o que o relatório ou a validação usam de
  fato.
- Nada disso impede o LLM de escrever bobagem *qualitativa* ("o modelo é
  excelente" para um R² de 0,55). Contra isso, só a checagem manual do
  §4.3(e).

## Alternativas descartadas

- **Dar ao LLM acesso a uma ferramenta de cálculo (function calling).** Mais
  flexível, mas reintroduz variabilidade no caminho dos números e torna a
  equivalência estatística indemonstrável. É o oposto do que o trabalho
  precisa provar.
- **Confiar em instrução de prompt ("não calcule nada").** Instrução em prompt
  não é garantia arquitetural. Vale como reforço — e está no prompt — mas não
  como mecanismo.
