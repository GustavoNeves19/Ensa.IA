# 0015 — Sistema só DCCR de ponta a ponta: tela, PDF e verificação

**Status:** Aceita · **Data:** 2026-10-25 · **Refina:** [0013](0013-restricao-a-dccr.md)

## Contexto

A [ADR 0013](0013-restricao-a-dccr.md) restringiu a **identificação** ao DCCR,
mas o resto do sistema continuava oferecendo coisas de outros planejamentos:
a etapa "Triagem" com as análises B1–B5 (efeitos de fatorial, Lenth,
meio-normal, gráficos de efeito e de interação, curvatura) no painel, na aba
de resultados e no PDF; textos de opções e do glossário falando em triagem e
Box-Behnken.

A especificação v0.6 (outubro de 2026, alinhada à Introdução revisada do TCC)
fecha o escopo: só os grupos A, C, D e E; B1–B5 reservados para a versão
geral; IA e MCP fora do escopo do TCC; três artigos de referência de DCCR
para a verificação numérica (§14.3), ainda a escolher.

## Decisão

1. **Grupo B sai da tela e do PDF, mas não do código.** O catálogo
   (`core/catalogo.py`) deixa de ter B1–B5; o painel perde a etapa
   "Triagem"; a aba de resultados e o PDF perdem efeitos, meio-normal,
   gráficos de efeito e de interação e curvatura, junto com as funções de
   gráfico que só serviam a eles (`ui/graficos.py`, `report/charts.py`).
   `core/fatorial.py` continua no núcleo, testado direto, como a ADR 0013
   decidiu.
2. **O Pareto fica, junto com os coeficientes (C1).** O Pareto dos efeitos
   padronizados mostra o |t| de cada termo do modelo quadrático; não é
   exclusivo de fatorial e é a saída padrão do Statistica em artigos de DCCR.
   Ele sai sempre que C1 estiver marcado.
3. **IA e MCP continuam no sistema como estão.** Ficam fora do escopo do TCC
   (spec v0.6, D-14), mas não são removidos nem escondidos. O MCP só passou a
   pedir C1 em vez de B1–B5 na ferramenta `compute_effects`.
4. **Blocos continuam.** Um DCCR feito em dois dias ou lotes segue analisável
   (o livro trata a blocagem ortogonal do composto central, p. 297–298). O
   bloco entra só para tirar a diferença entre blocos do erro, não como fator.
5. **O runner de validação usa o α rotacional.** Sem `alfa_axial` no
   `referencia.yaml`, um composto central usa (2ᵏ)^(1/4), e a busca do ótimo
   vai até ±α, como na tela.

## Consequências

**Boas**
- O usuário não vê mais nenhuma análise que não se aplique a um DCCR.
- Cinco exemplos de DCCR do livro (Barros Neto, Scarminio e Bruns, 2010) são
  reproduzidos em teste automático.

**Ruins / a vigiar**
- `core/fatorial.py` e o campo `efeitos_fatorial` do contrato continuam sem
  caminho de produção (ver ADR 0013).
- Os artigos de referência do TCC ainda precisam ser escolhidos e
  cadastrados como casos de estudo (spec v0.6, D-16).

**Revisão (2026-10-25)**
- Uma primeira versão desta ADR cadastrava como R1 e R2 os artigos de Bezerra
  et al. (2022) e Silva, Pereira e Almeida (2023), que a especificação v0.6
  lista só como candidatos e que não estão no TCC. Os dois casos e o teste
  saíram do repositório.
