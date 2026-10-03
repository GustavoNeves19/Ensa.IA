# 0006 — A camada de IA fala HTTP direto, sem LangChain

**Status:** Aceita · **Data:** 2026-10-02

## Contexto

A [ADR 0001](0001-fronteira-deterministica-llm.md) já fixou que o LLM narra e
não calcula: a camada narrativa recebe um `AnalysisResult` congelado e produz
texto. Esta decisão trata de uma pergunta diferente, deixada em aberto por
aquela: **como** essa camada conversa com o modelo de linguagem.

A especificação do sistema (`ESPECIFICACAO.md`, seção 12) define um papel
deliberadamente mínimo para a IA:

- O `core/` já produz frases prontas e verificadas no campo `facts` (ex.: *"O
  fator X1 é significativo (p = 0,0005 < 0,05)"*).
- **O código orquestra, não o modelo.** A camada chama `run_full_analysis`
  diretamente e entrega ao modelo apenas o resultado. O modelo não decide quais
  ferramentas usar.
- É **uma chamada por seção** do relatório, com contexto curto, temperatura
  baixa e saída em prosa.
- Os prompts são templates Jinja2; a checagem de fidelidade do §4.3(e) é código
  próprio (regex nos números), não recurso de framework.

Ou seja: o trabalho concreto é "manda um prompt, recebe um texto" — sem cadeia,
sem agente, sem RAG, sem o modelo chamando ferramentas.

Ao mesmo tempo, a leveza é requisito **medido**, não detalhe (RNF-01: ocioso
≤ 150 MB, pico ≤ 300 MB; RNF-12: servidor pronto em ≤ 5 s em hospedagem que
"adormece"). E o sistema precisa atender quatro modos com uma mesma base: M0
(sem IA), M1 (copiar prompt), M2 (Ollama local) e M3 (nuvem com chave do
usuário). Ollama, LM Studio e a maioria dos provedores de nuvem expõem o mesmo
endpoint `/v1/chat/completions` (compatível com OpenAI).

A implementação atual (`narrative/chain.py`) usa LangChain + Gemini. Esta
decisão a substitui pelo adaptador HTTP previsto na spec.

## Decisão

A camada de IA chama o modelo por **HTTP direto, com `httpx`**, contra o
endpoint compatível com OpenAI (`/v1/chat/completions`). Um único adaptador de
~100 linhas (URL base + nome do modelo + chave opcional) cobre M2 e M3.

**LangChain fica fora da dependência de produção.** Pode existir como *extra*
opcional (`[langchain]`) apenas para fins de comparação na monografia, e, se
usado, deve produzir texto equivalente ao do adaptador próprio.

Motivos, na ordem do peso que tiveram:

1. **Leveza é requisito medido.** O `httpx` já vem como dependência transitiva
   do SDK do `mcp`, então o custo marginal é ≈ zero. O caminho mínimo em
   LangChain (`langchain-core` + `langchain-openai` + SDK `openai` + `tiktoken`)
   adiciona dezenas de MB de RAM e um tempo de import alto — empurra contra
   RNF-01 e RNF-12.
2. **O papel da IA é mínimo por projeto.** Chains, agents e retrievers — o
   motivo de existir do LangChain — não estão no escopo. Seria carregar um
   framework de agentes para não usar agente nenhum.
3. **Portabilidade por um endpoint só.** `/v1/chat/completions` unifica Ollama,
   LM Studio e nuvem. A doc atual do LangChain confirma que o caminho "nativo"
   pede um pacote por provedor (`langchain-ollama`, `langchain[google-genai]`…);
   unificar via `langchain-openai` + `base_url` seria usar o framework como um
   `httpx` mais pesado.
4. **Controle e estabilidade.** O adaptador próprio dá controle explícito de
   timeout, retry, streaming e do *fallback* por seção para o M0 (spec 12.3.6).
   O `httpx` tem API estável há anos; o LangChain tem histórico de mudanças
   que quebram compatibilidade — risco real num trabalho que precisa ser
   reproduzível na defesa.
5. **Transparência para a banca.** ~100 linhas que dá para ler, entender e
   explicar no texto valem mais, academicamente, que delegar a chamada a uma
   caixa-preta.

## Consequências

**Boas**

- Custo de memória da camada de IA no servidor fica praticamente nulo (não há
  modelo nem biblioteca pesada rodando lá), coerente com o orçamento de 512 MB.
- Um só adaptador atende Ollama, LM Studio e nuvem; trocar de provedor é mudar
  URL, modelo e chave.
- O comportamento da chamada (retry, timeout, *fallback* para o texto M0) fica
  explícito e testável — `httpx` é trivial de mockar (`httpx.MockTransport`).
- Abre um ponto de mérito na monografia: avaliar as duas abordagens e
  demonstrar equivalência de resultado, adotando a leve por justificativa
  técnica registrada aqui.

**Ruins, e assumidas**

- Recursos que o LangChain daria de graça (output parsers com retry,
  observabilidade via LangSmith, troca entre dezenas de provedores
  heterogêneos) passam a ser responsabilidade nossa — aceitável porque nenhum
  deles está no escopo.
- Streaming via SSE e tratamento de erro de cada provedor exigem algumas linhas
  a mais de código manual no adaptador.
- Se o escopo mudar no futuro para exigir agentes ou RAG de verdade, esta
  decisão precisa ser revista (não é irreversível: o `[langchain]` opcional é a
  porta de entrada).

## Alternativas descartadas

- **LangChain em produção como camada principal.** Descartado pelo peso
  (RNF-01/RNF-12) e por trazer um framework de orquestração para um uso que é
  uma única chamada sem orquestração. Faz sentido para agentes e RAG — não para
  "prompt entra, texto sai".
- **SDK oficial de um provedor específico (ex.: `google-generativeai`).**
  Amarraria o sistema a um provedor e quebraria o M2 (Ollama local) e o modelo
  "traga sua própria chave" para outros provedores. O endpoint compatível com
  OpenAI é o denominador comum.
