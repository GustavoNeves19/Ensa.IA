# 0004 — Casos de estudo são dados versionados, não código

**Status:** Aceita · **Data:** 2026-08-23

## Contexto

O §4.2 do pré-projeto prevê de três a cinco casos de estudo tirados da
literatura, cada um com dados experimentais publicados e resultados
estatísticos de referência. Esses casos são a evidência do TCC inteiro.

A tentação é escrever um script de validação por caso. Isso apodrece rápido:
os scripts divergem entre si, ninguém sabe qual gerou qual número da
monografia, e a comparação entre casos vira trabalho manual.

## Decisão

Cada caso de estudo é um diretório com dados, e o código de validação é único
para todos.

```
casos_de_estudo/<nome-do-caso>/
├── dados.csv        ensaios: níveis dos fatores + respostas medidas
├── referencia.yaml  valores publicados no artigo original
├── fonte.md         citação ABNT completa, DOI, e como os dados foram obtidos
└── resultados/      saída do EnsaIA + planilha de fidelidade preenchida
```

`referencia.yaml` guarda os coeficientes, R², significâncias e condição ótima
como o artigo publicou — usando a mesma notação canônica de termos do EnsaIA.

O runner de validação varre o diretório, roda o pipeline em cada caso e aplica
as métricas do §4.3. Adicionar um caso novo é criar uma pasta, sem tocar em
código.

## Consequências

- Os testes de regressão (`tests/regressao/`) parametrizam sobre os casos:
  toda alteração no núcleo é conferida contra todos os valores publicados
  automaticamente. Se um refactor mudar um coeficiente, o CI acusa na hora.
- O capítulo de resultados da monografia sai de uma execução reproduzível, e
  não de números copiados à mão de execuções avulsas.
- `fonte.md` é obrigatório. Um dataset sem procedência não é evidência — e o
  §4.2, critério 1, exige disponibilidade pública verificável.
- Custo: extrair os valores do artigo para o `referencia.yaml` é trabalho
  manual e chato, e um erro de digitação aqui envenena a validação daquele
  caso. Por isso a transcrição é conferida por ambos, e o `fonte.md` registra
  a página/tabela de onde cada bloco de valores veio.
