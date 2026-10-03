# Registros de Decisão de Arquitetura (ADR)

Cada arquivo aqui documenta **uma** decisão de arquitetura: qual era o
contexto, o que foi decidido, e o que isso custa.

Por que manter isto num TCC: daqui a três meses, na defesa, alguém da banca
vai perguntar "por que vocês fizeram assim?". A resposta honesta e específica
está aqui, escrita no dia em que a decisão foi tomada — não reconstruída de
memória na véspera.

Formato: contexto → decisão → consequências (inclusive as ruins).

| # | Decisão | Status |
|---|---------|--------|
| [0001](0001-fronteira-deterministica-llm.md) | O LLM narra, mas não calcula | Aceita |
| [0002](0002-generalizacao-para-k-fatores.md) | Generalizar de 3 fatores fixos para k fatores | Aceita |
| [0003](0003-criterio-de-significancia.md) | α = 0,05 em vez de p ≤ 0,10 | Aceita |
| [0004](0004-casos-de-estudo-como-dados.md) | Casos de estudo são dados versionados, não código | Aceita |
| [0005](0005-anova-tipo-ii-encapsulada.md) | ANOVA Tipo II encapsulada em `AjusteOLS`, com autocheck em runtime | Aceita |
