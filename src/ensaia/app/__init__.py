"""Ponto de montagem do processo único (composition root).

Aqui a aplicação web é montada: um app FastAPI que serve a interface (NiceGUI),
a sonda de saúde e, na fase final (F9), o servidor MCP — tudo no mesmo processo
para caber no orçamento de memória (spec, seção 7.2).
"""
