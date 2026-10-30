# 0016 — Texto com IA não se mistura com o texto do sistema

**Status:** Aceita · **Data:** 2026-10-30 · **Revisa:** [0006](0006-camada-de-ia-httpx-sem-langchain.md) (item 4)

## Contexto

A spec (§12.3.6) e a [ADR 0006](0006-camada-de-ia-httpx-sem-langchain.md)
previam um *fallback* por seção: se o parágrafo da IA citasse um número fora dos
fatos, ou se o modelo não respondesse, aquela seção (e as seguintes, no caso de
falha de conexão) saía com o texto M0, montado pelo sistema.

Na prática, o relatório "com IA" virava uma colcha: parte escrita pelo modelo,
parte pelo sistema, com outra voz e outro formato. Com o Gemini estourando o
tempo limite na primeira seção, o usuário pedia texto com IA e recebia o texto
M0 inteiro, sem perceber direito o que tinha acontecido.

## Decisão

1. **Com IA (M2 e M3), todo o texto vem do modelo.** Nenhuma seção é trocada
   pelo texto M0.
2. **Número fora dos fatos não derruba a seção.** O modelo tenta de novo
   (`tentativas_fidelidade`); se nenhuma versão sair fiel, fica a que tem menos
   números soltos, com um aviso. A conferência de fidelidade (§12.5) marca esses
   números em amarelo e lista as contradições de significância, como já fazia
   no modo M1.
3. **Falha do modelo vira erro na tela, não texto do sistema.** Tempo esgotado
   (30 s; 60 s no Ollama), chave recusada, limite de uso ou resposta vazia
   sobem como `ErroDeIA`; a tela mostra o motivo e não mostra texto nenhum.
4. **O M0 continua existindo como modo próprio** ("Sem IA"), e o PDF segue
   usando o texto M0 quando nenhum texto foi gerado.

## Consequências

**Boas**
- O que a tela chama de "texto com IA" é só da IA; a garantia de fidelidade
  passa a ser a marcação, igual nos modos M1, M2 e M3.
- A falha do modelo fica visível em segundos, em vez de escondida num texto
  M0.

**Ruins / a vigiar**
- Um texto com IA pode ir para o PDF com números marcados como não conferidos.
  O destaque e o resumo da conferência são o que impede o leitor de tomar esses
  números como resultado.
