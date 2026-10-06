# 0011 — Interface web em NiceGUI, num processo único

**Status:** Aceita · **Data:** 2026-10-06 · **Refina:** [0001](0001-fronteira-deterministica-llm.md)

## Contexto

O protótipo tinha a interface em **Streamlit** (extra `[ui]` = `streamlit` +
`plotly`). A especificação (seção 7.3) decidiu trocar por **NiceGUI**, e a 7.2
pede que a interface web, o servidor MCP e a sonda de saúde rodem **no mesmo
processo ASGI** (um Uvicorn, um *worker*) para caber no orçamento de 512 MB
(RNF-01) e subir em até 5 s (RNF-12).

O motivo da troca não é estético. O Streamlit reexecuta o script inteiro a cada
interação e sobe seu próprio servidor — não dá para montá-lo dentro do mesmo
processo que serve o MCP, e cada clique recarrega tudo. A NiceGUI roda **sobre
FastAPI**: atualiza só o que muda e, por ser um app FastAPI, pode ser acoplada
(`ui.run_with`) ao mesmo app que expõe `/health` e, depois, o MCP em `/api`.

## Decisão

- O extra `[ui]` passa a ser só **`nicegui`** (que já traz FastAPI, Uvicorn,
  Pydantic, Jinja2 e o ECharts). Saem `streamlit` e `plotly`.
- Ponto de montagem em `ensaia/app/main.py`: um app FastAPI com `GET /health` e a
  NiceGUI acoplada via `ui.run_with(app, ...)`. O servidor MCP entra na fase F9,
  montado em `/api` (nunca em `/`, para não encobrir a interface). Script
  `ensaia-ui` sobe o processo com 1 *worker*, sem *reload* em produção.
- A camada `ui/` é só apresentação (spec 7.1): chama o núcleo e as camadas de
  relatório/IA, não calcula nada. Um `ui/tema.py` concentra a identidade visual
  (ponto único de troca de marca), com a **mesma paleta do relatório PDF**
  (`report/theme.py`) — tela e documento falam a mesma língua.
- **Sem `app.storage.user`/`browser`** (que gravam em disco): a sessão vive só na
  memória, como exige o princípio P1 ("nada é armazenado"). Por isso também não
  se define `storage_secret`.

A `ui/` é um extra opcional: `pip install ensaia` sem extras continua fazendo DOE
completo e offline, sem baixar a NiceGUI.

## Consequências

**Boas**

- Um processo só para UI + saúde + (futuro) MCP: cabe no orçamento de memória e
  não duplica o núcleo em serviços separados ("um núcleo, várias portas", P7).
- Reatividade real (sem reexecutar a página a cada clique) e ECharts embutido —
  sem `plotly`.
- Identidade visual única entre tela e PDF, trocável num arquivo.

**Ruins, e assumidas**

- A NiceGUI mantém no servidor a árvore de elementos de cada sessão aberta; isso
  pede disciplina (criar elementos sob demanda, limpar ao trocar de arquivo,
  `reconnect_timeout` curto). Registrado para as telas que vierem.
- Teste de interface no navegador (ponta a ponta) exige um browser headless, fora
  da suíte unitária. Por ora os testes cobrem o processo único (o `/health`
  responde, a raiz serve a UI); o resto é validado abrindo a página.

## Alternativas descartadas

- **Manter o Streamlit.** Não acopla ao processo do MCP e recarrega a cada
  interação — contra o RNF de memória e a reatividade desejada.
- **Dois processos (UI e MCP separados).** Dobraria o custo de memória; a spec
  (7.2) exige processo único por causa do RNF-01.
- **`plotly` para os gráficos.** O ECharts já vem com a NiceGUI e cobre 2D e 3D
  (superfícies), sem mais uma dependência grande.
