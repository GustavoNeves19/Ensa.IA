"""Servidor MCP do EnsaIA (spec §11): as análises como ferramentas de IA.

Qualquer assistente compatível com o Model Context Protocol (Claude, ChatGPT,
LM Studio, clientes para Ollama) usa as mesmas análises da tela, com os mesmos
números: o assistente orquestra e redige, o núcleo determinístico calcula.

- `server.py`: as ferramentas, os recursos e os prompts, e o modo `stdio`
  (`ensaia-mcp`, local e privado).
- `montagem.py`: o modo HTTP em `/api/mcp`, no mesmo processo da interface,
  carregado só na primeira chamada para não pesar na memória ociosa.

Este pacote não importa o SDK do MCP no `__init__`: quem só sobe a interface
não paga por ele.
"""
