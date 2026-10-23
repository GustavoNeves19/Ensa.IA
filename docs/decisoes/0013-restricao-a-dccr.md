# 0013 — Restringir o escopo a DCCR; generalização vira trabalho futuro

**Status:** Aceita · **Data:** 2026-10-20 · **Relacionada:** [0002](0002-generalizacao-para-k-fatores.md)

## Contexto

O EnsaIA reconhecia e analisava seis geometrias de planejamento: fatorial
completo, fatorial fracionado, fatorial 3^k, Box-Behnken, composto central (com
qualquer α, inclusive de face centrada) e um grupo genérico de catch-all. O
ADR 0002 generalizou o núcleo de 3 fatores fixos para k fatores justamente para
cobrir essa variedade, citando o §4.2 (critério 2) do pré-projeto assinado:
"cobertura de diferentes tipos de planejamento experimental (ex.: fatorial
completo 2^k, delineamento composto central, Box-Behnken)".

**Motivo da mudança.** A dupla (eu e o Gustavo) ainda está consolidando alguns
conceitos estatísticos por trás desses outros delineamentos. É mais correto e
mais produtivo reduzir o escopo agora — dominar DCCR de ponta a ponta, com
rigor — do que manter a superfície ampla meio por cima. Isso vale tanto para o
código quanto para a monografia.

**Consequência administrativa.** Esta decisão estreita o que o §4.2 (critério
2) do pré-projeto promete. Falta alinhar isso formalmente com a orientadora e,
se necessário, corrigir o documento — ver `CONTRIBUTING.md`, regra 2, que trata
exatamente desse tipo de divergência entre o que o TCC promete e o que o
sistema faz. Este ADR registra a decisão técnica; não substitui essa conversa.

## Decisão

O EnsaIA passa a reconhecer **só o delineamento composto central rotacional
(DCCR)** — composto central cujo α é o rotacional, não o de face centrada nem
qualquer outro. A generalização para outros tipos de planejamento volta a ser
trabalho futuro, não suporte atual.

Mudanças concretas:

- `core/identificacao.py`: `_classificar` só devolve `"composto_central"` para
  um DCCR de verdade (vértices + estrela axial + α rotacional dentro da
  tolerância). Qualquer outra geometria — incluindo um composto central de
  face centrada (α=1) — volta `"desconhecido"`, com um aviso que nomeia o que a
  disposição mais parece (fatorial completo, fracionado, 3^k, Box-Behnken),
  para orientar quem está montando a planilha.
- `core/results.py`: o `Literal` `TipoPlanejamento` encolhe para
  `"composto_central" | "desconhecido"`. Isso é reforçado pelo contrato
  Pydantic `AnalysisResult`: tentar produzir um resultado com qualquer outro
  tipo agora falha alto e cedo, em vez de silenciosamente aceitar um estado que
  não deveria mais existir.
- `core/termos.py` (`tipo_padrao`) e `core/catalogo.py` (disponibilidade de
  E3): o modelo quadrático — e o ponto estacionário que depende dele — ficam
  condicionados a `tipo == "composto_central"`, não mais a uma contagem de
  níveis (que um fatorial com pontos centrais também "engana", por ter 3
  valores distintos por fator sem ter graus de liberdade reais para curvatura).
- `ui/analise.py`: o seletor manual "forçar tipo de planejamento" perde as
  opções que não existem mais; só resta "Automático" e "Composto central
  rotacional (DCCR)".
- `io/modelo.py`: a planilha-modelo para baixar passa a ser um DCCR de 3
  fatores (20 ensaios: 8 fatoriais + 6 axiais + 6 centrais, α≈1,682), não mais
  um Box-Behnken.
- `ensaia/exemplos/`: os dois exemplos embutidos (remoção de metronidazol e
  fotodegradação de levofloxacino) eram Box-Behnken — saíram. Repostos (2026-
  10-23) por dois DCCR reais: degradação de tilosina por foto-Fenton (Sarrai
  et al., 2016) e hidrólise ácida de sementes de açaí (Igreja et al., 2023,
  com coautoria da orientadora) — ver `casos_de_estudo/tylosin-photo-fenton`
  e `casos_de_estudo/igreja-2023-acai-hidrolise-acida`.
- A tolerância para aceitar um α como "rotacional" subiu de 2% para 5%
  (`identificacao.py`, `_TOL_ALFA_ROTACIONAL`): com 2%, o próprio caso do
  Tylosin acima — um DCCR real, intencionalmente rotacional segundo o artigo
  — era rejeitado como "desconhecido", porque os níveis axiais publicados
  (já arredondados pelos autores) medem α=1,639, não os 1,682 exatos. 5%
  ainda rejeita com folga α=1 (face centrada) e α=2 num k=3.
- `casos_de_estudo/`: os dois casos Box-Behnken (`go-2022-levofloxacino-
  hidroxiapatita-bbd`, `mazloomi-2023-zif67-metronidazol`) saíram do
  repositório — não fazem mais parte do conjunto de validação do §4.3.

**O que foi deliberadamente preservado.** `core/fatorial.py` (efeitos de Yates,
Lenth, meio-normal, teste de curvatura — o Grupo B do catálogo) continua no
código. Hoje é inalcançável pelo fluxo real, porque `identificar_planejamento`
nunca mais produz um tipo fatorial — mas apagar esse módulo agora só para
reescrevê-lo quando a generalização voltar seria descartar trabalho por
estética. Ele fica coberto por testes que o chamam diretamente (não mais via
`AnalysisResult`, que já rejeita esses tipos), documentando essa fronteira.

## Consequências

**Boas**
- Escopo do TCC alinhado com o que a dupla domina de verdade hoje.
- `AnalysisResult` (a fronteira do ADR 0001) passa a travar em runtime que
  nenhum tipo fora do DCCR chega ao relatório ou à validação — não é mais só
  convenção de UI.
- A planilha-modelo e os exemplos embutidos deixam de ensinar, por exemplo
  (Box-Behnken), um delineamento que o sistema não analisa mais.

**Ruins / a vigiar**
- Perde-se a cobertura de validação externa (§4.3) que os dois casos
  Box-Behnken davam. Atualização de 2026-10-23: dois casos DCCR reais entraram
  (Tylosin e o açaí de Igreja et al. 2023/Martins), ambos com R² batendo com
  o publicado dentro da tolerância — mas os dois seguem `status: rascunho`
  até a dupla conferência humana formal (ver `casos_de_estudo/README.md`).
  Outros candidatos CCD mapeados em `docs/pesquisa/casos-de-estudo-candidatos.md`
  (e mais achados depois, por busca direta de artigos da orientadora) ficam
  como reserva.
- `core/fatorial.py` vira código sem um caminho real de produção até a
  generalização voltar — justificável, mas é superfície morta que alguém pode
  achar estranha sem ler este ADR.
- O §4.2 (critério 2) do pré-projeto assinado ainda descreve um escopo mais
  amplo do que o sistema cobre agora; pendente alinhar com a orientadora (ver
  Contexto, acima).
