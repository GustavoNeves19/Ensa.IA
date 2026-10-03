# 0009 — Contrato `AnalysisResult` em Pydantic v2

**Status:** Aceita · **Data:** 2026-10-03 · **Refina:** [0001](0001-fronteira-deterministica-llm.md)

## Contexto

A [ADR 0001](0001-fronteira-deterministica-llm.md) definiu o `AnalysisResult`
como a fronteira entre o núcleo e a camada de LLM: congelado, serializável,
auto-contido. A implementação eram `@dataclass(frozen=True)`.

A especificação (seção 10) pede que esse contrato seja feito em **Pydantic v2**,
e por um motivo concreto: o mesmo objeto é a saída do núcleo, a resposta das
ferramentas MCP e a entrada da camada de IA e do relatório. Nos dois últimos
casos ele pode chegar vindo de fora (um JSON de uma ferramenta MCP, um arquivo
de resultado relido). Dataclass não valida nada em runtime — um campo com o tipo
errado passa direto e só quebra lá na frente, longe da causa. Pydantic valida na
construção e rejeita cedo, com mensagem clara.

## Decisão

Os modelos do contrato em `core/results.py` passam a ser Pydantic v2
(`BaseModel` com `model_config = ConfigDict(frozen=True)`), via uma base comum
`_Congelado`. Campos, ordem, tipos e defaults são idênticos aos da versão em
dataclass; o método `ajuste()` permanece.

`to_dict()` usa `model_dump()` e `to_json()` continua sendo
`json.dumps(self.to_dict(), indent=2, ensure_ascii=False)` — **de propósito**,
para preservar o formato exato (indentação, ordem de campos, repr de float) dos
resultados já versionados. Com isso os JSONs de evidência dos casos ficam **byte
a byte idênticos**: a conta não mudou, só o tipo que a carrega.

`pydantic` entra como dependência de produção. Só o contrato de saída vira
Pydantic; as estruturas internas de cálculo (`Table`, `Fator`, `AlvoResposta`) e
as de métrica seguem dataclasses — Pydantic não acrescenta nada a elas e a
`Table` em particular tem que ser leve.

## Consequências

**Boas**

- Validação de tipo na fronteira: um `AnalysisResult` malformado vindo de uma
  ferramenta MCP ou de um arquivo relido é rejeitado com `ValidationError`
  claro, em vez de propagar silenciosamente.
- Round-trip gratuito: `model_validate_json` reconstrói o objeto a partir do
  JSON, útil para reler evidência e para os testes.
- A imutabilidade (que sustenta "o LLM não altera número") passa a ser validada
  também em atribuição, não só por convenção.
- Os JSONs versionados não mudaram — a migração é verificável como neutra.

**Ruins, e assumidas**

- Mais uma dependência de produção (`pydantic`). Aceitável: é leve, já vem com a
  NiceGUI prevista para a UI (spec, seção 7.4), e o ganho de validação na
  fronteira MCP/IA justifica.
- Construção só por palavra-chave (Pydantic não aceita posicional). O código já
  construía assim; sem impacto.

## Alternativas descartadas

- **Manter dataclasses.** Mais simples e sem dependência, mas não valida nada —
  contraria o motivo da seção 10 (o contrato cruza a fronteira MCP/IA).
- **Converter tudo para Pydantic** (Table, métricas, Fator…). Desnecessário: só
  o contrato de saída cruza a fronteira e precisa de validação; a `Table` tem
  que ser leve (ADR 0008) e Pydantic não agrega às estruturas internas.
