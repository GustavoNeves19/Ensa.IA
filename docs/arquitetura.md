# Arquitetura

## Fluxo

```
  dados.csv
     │
     ▼
  io/readers ──► io/schemas          valida e falha cedo, com mensagem útil
     │
     ▼
  core/design                        Fator, codificação [-1,+1], termos
     │
     ▼
  core/model                         matriz X, ajuste OLS
     │
     ▼
  core/anova                         ANOVA tipo II, seleção (α=0,05), falta de ajuste
     │
     ▼
  core/effects                       coeficientes, efeitos, IC
     │
     ▼
  core/desirability                  otimização Derringer-Suich
     │
     ▼
  ╔══════════════════╗
  ║  AnalysisResult  ║               frozen · serializável · auto-contido
  ╚════════╤═════════╝
           │
     ┌─────┴──────┐
     ▼            ▼
 narrative/   validation/
  (LLM)        (§4.3)
```

## A fronteira

`AnalysisResult` é o único canal entre o núcleo e o resto. Está em
`core/results.py`, é `frozen`, e serializa em JSON sem perda.

Consequência prática: quando o relatório precisar de um dado que não está no
`AnalysisResult`, o caminho é **adicioná-lo ao contrato**, e não dar à camada
narrativa acesso ao DataFrame original. O segundo caminho é mais rápido e
destrói a garantia que sustenta o trabalho.

Ver [ADR 0001](decisoes/0001-fronteira-deterministica-llm.md). O teste que
trava isso é `tests/test_arquitetura.py`.

## Por que `core` não conhece `narrative`

Três razões, em ordem de importância para o TCC:

1. **A hipótese exige.** "Resultados estatisticamente equivalentes a software
   pago" só é verificável se o LLM não puder tocar em número.
2. **Reprodutibilidade.** O núcleo roda offline, sem chave de API. Qualquer
   pessoa da banca reproduz os resultados numéricos sem gastar um centavo de
   API.
3. **Independência de fornecedor.** Trocar Gemini por outro modelo não muda
   uma casa decimal.

## O que ainda não existe

O contrato, as métricas do §4.3 e os testes de arquitetura estão prontos e
funcionando. O núcleo estatístico está com assinaturas e docstrings
definidas, e as implementações marcadas com `TODO(#n)` apontando para issues:

| Issue | Módulo | O que falta |
|---|---|---|
| #3 | `core/model` | Matriz de modelo e ajuste OLS |
| #4 | `core/anova` | ANOVA tipo II, seleção de termos, falta de ajuste |
| #5 | `core/effects` | Coeficientes, efeitos, IC |
| #6 | `core/desirability` | Desejabilidade e otimização |
| #7 | `narrative/chain` | Cadeia LangChain |
| #8 | `validation/runner` | Runner dos casos de estudo |
| #9 | `io/` | Leitura e validação de entrada |
| #10 | `ui/app` | Interface Streamlit |

Ordem sugerida: #3 → #4 → #5 desbloqueiam #8, que é o que produz o capítulo de
resultados. #7 e #10 podem correr em paralelo depois que o `AnalysisResult`
tiver dado real dentro.
