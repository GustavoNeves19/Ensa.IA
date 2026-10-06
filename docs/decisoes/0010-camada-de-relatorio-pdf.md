# 0010 — Camada de relatório PDF (fpdf2 + matplotlib)

**Status:** Aceita · **Data:** 2026-10-06 · **Refina:** [0001](0001-fronteira-deterministica-llm.md)

## Contexto

A especificação (seção 13) pede um relatório PDF padronizado: capa, resumo,
modelo ajustado, ANOVA e R², diagnóstico, interpretação e apêndice de
rastreabilidade, com números no padrão brasileiro (vírgula decimal) e um ponto
único de troca de identidade visual (logo, cores, fonte).

Esse relatório é a **camada de apresentação**: consome o `AnalysisResult` (os
números, contrato congelado da [ADR 0001](0001-fronteira-deterministica-llm.md))
e o `RelatorioTextual` (a prosa do modo escolhido, da camada `ai/`), e desenha.
Ela não pode recalcular nada — se a tabela do PDF divergisse da conta do núcleo,
o relatório deixaria de ser evidência fiel. É a mesma regra "redige/desenha, não
calcula" que já vale para `ai/`.

## Decisão

Nova camada `report/`, isolada, que ninguém no núcleo nem na `ai/` importa:

- **`fpdf2`** monta o PDF. Leve (RNF-01 512 MB, RNF-12 startup ≤ 5 s), sem
  dependências pesadas, com API de tabela que quebra células longas (necessário
  para nomes de termo como `dose_catalisador:concentracao_levofloxacino`).
- **`matplotlib`** gera os gráficos (Pareto dos efeitos e coeficientes com IC)
  em PNG na memória, pelo objeto `Figure` **sem `pyplot`** — a forma recomendada
  fora de ambiente interativo: não mexe no estado global e libera a figura ao fim
  de cada gráfico.
- **`theme.py`** concentra cores, fonte e casas decimais — o ponto único de troca
  de marca que a seção 13 pede. Paleta deliberada (tinta carvão, acento petróleo,
  cinzas), não o visual padrão de nenhuma ferramenta.
- **Fonte DejaVu Sans embutida** no pacote (regular/negrito/oblíquo), para os
  acentos do português e os símbolos dos fatos (`≥`, `²`, `−`, `α`) renderizarem
  idênticos em qualquer máquina, sem depender das fontes do sistema.

`fpdf2` e `matplotlib` entram como extra **`[report]`** (e em `[dev]`, exercidos
pelos testes). O núcleo e a `ai/` não dependem de nada disso: uma instalação
só-núcleo valida casos sem a camada de relatório.

A data da capa (`gerado_em`) é recebida de fora, não de um relógio interno, para
o PDF continuar reproduzível em teste.

## Consequências

**Boas**

- Relatório padronizado e com rastreabilidade (versões de bibliotecas, hash
  SHA-256 do contrato, versão do prompt) — material direto para a banca.
- Camada isolada e opcional: quem só quer validar números não paga o custo das
  duas dependências de desenho.
- Troca de identidade visual em um arquivo (`theme.py`), como a spec exige.
- Nada se recalcula: tabelas e gráficos leem o contrato congelado, então o PDF
  é fiel por construção.

**Ruins, e assumidas**

- Duas dependências novas (`fpdf2`, `matplotlib`) e ~2 MB de fontes versionadas.
  Aceitável: ficam num extra à parte, e a fonte embutida garante renderização
  consistente (o ganho supera o peso).
- O PDF não é comparável byte a byte em teste (carrega data e metadados do
  ambiente). Os testes verificam estrutura (é um PDF, os gráficos são PNG
  válidos, a formatação é pt-BR), não pixels.

## Alternativas descartadas

- **ReportLab.** Mais poderoso, porém mais pesado e verboso; a API de tabela do
  `fpdf2` já cobre o que a seção 13 pede com menos código.
- **WeasyPrint (HTML/CSS → PDF).** Traria uma cadeia nativa pesada (Pango,
  Cairo), contra o RNF de leveza, e um motor de layout grande demais para um
  relatório de estrutura fixa.
- **`pyplot`** para os gráficos. Estado global e vazamento de figuras em uso
  repetido; o objeto `Figure` direto é a forma correta em servidor.
- **Seções que exigem dados crus** (estatística descritiva, matriz experimental,
  superfícies de resposta). Adiadas até o contrato carregar o que elas pedem —
  o relatório monta hoje só o que o `AnalysisResult` já fornece.
