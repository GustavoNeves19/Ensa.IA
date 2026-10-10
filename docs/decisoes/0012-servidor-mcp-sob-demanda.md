# 0012 — Servidor MCP com o SDK oficial v2, carregado sob demanda

**Status:** Aceita · **Data:** 2026-10-10 · **Refina:** [0011](0011-interface-nicegui-processo-unico.md)

## Contexto

A especificação (seções 7.2 e 11) pede o servidor MCP no mesmo processo da
interface, em `/api/mcp`, e também por `stdio` para uso local. O SDK oficial do
MCP para Python está na linha **2.x** desde agosto de 2026 (a classe passou a se
chamar `MCPServer`; as opções de transporte foram para `streamable_http_app()`).

Medido no ambiente do projeto, **importar o SDK custa cerca de 23 MB** de
memória residente. O servidor ocioso já estava em ~147 MiB no Linux, para um
teto de 150 MiB (RNF-01): montar o MCP na partida estouraria o orçamento de
todos os usuários, inclusive de quem só usa a tela e nunca chama o MCP.

## Decisão

- Dependência `mcp>=2.3,<3` num extra próprio, `[mcp]`, incluído na imagem
  Docker e no `[dev]`.
- `ensaia/mcp_server/server.py` define o `MCPServer` com as ferramentas, os
  recursos e os prompts da seção 11, sobre o mesmo fluxo da tela
  (`core/fluxo.py`): os números de uma ferramenta são os da tela por construção.
- **HTTP sem estado e sob demanda.** Em `/api` fica montado um app ASGI leve
  (`mcp_server/montagem.py`) que só importa o SDK na primeira requisição, cria o
  app `streamable_http_app(stateless_http=True, json_response=True)` e mantém o
  gerenciador de sessões aberto numa tarefa de fundo, fechada no `lifespan` do
  FastAPI. O `/api` é montado antes da NiceGUI, que ocupa `/`.
- **stdio** pelo script `ensaia-mcp`, o único modo em que a ferramenta
  `read_table` aceita um caminho de arquivo local.
- **Segurança.** A proteção do SDK contra *DNS rebinding* fica ligada; o domínio
  público é liberado por `ENSAIA_HOSTS`. Entradas têm o mesmo teto de 5 MB da
  tela.

## Consequências

**Boas**
- Memória ociosa medida no CI (Linux, imagem Docker): 146,8 MiB pelo script e
  148 MiB no contêiner, dentro do teto; pico com análise e PDF em 226 MiB.
- Quem usa só a tela não paga pelo MCP; a primeira chamada ao `/api/mcp` leva o
  tempo da importação (uma vez por processo).
- Assistentes de IA, inclusive modelos pequenos via `run_full_analysis`, obtêm
  os mesmos resultados do núcleo, sem calcular nada.

**Ruins / a vigiar**
- A folga de memória ociosa é pequena (cerca de 3 MiB): qualquer importação nova
  na partida precisa ser medida.
- O SDK traz dependências que aumentam a imagem (`cryptography`, `jsonschema`,
  `opentelemetry-api`): ela foi a 415 MB em disco (142 MB compactada), acima da
  meta de 300 MB da RNF-10.
- Depois da primeira chamada, os ~23 MB do SDK ficam no processo até ele
  reiniciar.
