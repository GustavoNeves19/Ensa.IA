# Fonte do caso de estudo — Degradação de tilosina por foto-Fenton (CCD)

## Citação (ABNT)

> SARRAI, Abd Elaziz; HANINI, Salah; MERZOUK, Nachida Kasbadji; TASSALIT,
> Djilali; SZABÓ, Tibor; HERNÁDI, Klára; NAGY, László. Using Central
> Composite Experimental Design to Optimize the Degradation of Tylosin from
> Aqueous Solution by Photo-Fenton Reaction. **Materials**, Basel, v. 9, n. 6,
> art. 428, 2016.
> DOI: 10.3390/ma9060428

- **DOI / URL:** https://doi.org/10.3390/ma9060428
- **Mirror de acesso aberto:** https://pmc.ncbi.nlm.nih.gov/articles/PMC5456803/
- **Acesso em:** <preencher quando abrir de verdade>
- **Tipo de planejamento:** CCD ortogonal rotacional, 3 fatores, 5 níveis (−α, −1, 0, +1, +α), 20 ensaios
- **Nº de ensaios:** 20

## Procedência dos dados

De onde saiu cada coisa. Sem isto, ninguém consegue reconferir a transcrição
— nem vocês daqui a dois meses.

Números de tabela abaixo vieram de uma pesquisa automatizada anterior (que
leu o PMC via ferramenta, não um humano olhando o PDF) — servem só pra saber
ONDE procurar, não como valor já validado. Preencher página real ao abrir o
artigo.

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Matriz de ensaios (`dados.csv`) | Tabela 2 (observado × previsto, 20 ensaios) | | |
| Equação do modelo / coeficientes de remoção de TOC | Corpo do texto, equação do modelo quadrático | | |
| Tabela ANOVA completa | Tabela 3 | | |
| R² / R² ajustado | Junto da Tabela 3 | | |
| Condição ótima | Tabela 4 | | |

## Guia de preenchimento (transcrição humana, conferida em dupla)

Ordem sugerida para abrir o PDF uma vez só e preencher tudo. Cada valor vai
para o campo indicado; `null` em todo campo que o artigo não reportar.

1. **Fatores e faixas** → `referencia.yaml: fatores`. Confirme nome, unidade e
   os níveis **−1 e +1 do fatorial** (não os axiais ±α) de cada fator. Esses
   níveis definem a escala codificada contra a qual os coeficientes são
   comparados.
2. **Matriz de ensaios** (Tabela 2) → `dados.csv`. As 20 linhas em unidades
   reais, resposta na última coluna. Veja o cabeçalho do `dados.csv` para a
   composição esperada e o cálculo dos pontos axiais.
3. **Modelo / coeficientes** (equação no texto) → `referencia.yaml: respostas.
   remocao_toc.coeficientes`. **Atenção (lição do caso Go):** confira se o
   artigo ajustou o **quadrático completo** (os 10 termos listados) ou um
   **modelo reduzido** (descartou termos não significativos). Se for reduzido,
   acrescente `termos_modelo:` com exatamente os termos publicados e deixe só
   esses em `coeficientes`/`significancia` — senão o LYRA ajusta o completo e
   os coeficientes não batem por diferença de modelo, não de cálculo.
4. **ANOVA, R² e R² ajustado** (Tabela 3) → `r2`, `r2_ajustado` e a
   classificação de **significância** por termo (significativo = `true`,
   não significativo = `false`; não reportado = `null`).
5. **Condição ótima** (Tabela 4) → `condicao_otima.coordenadas` (nos mesmos
   níveis/escala dos fatores) e `resposta_prevista`. Anote em `observacoes`
   tanto o previsto quanto a confirmação experimental, se o artigo der os dois.
6. **Conferência dupla:** preencha a coluna "Conferido por" da tabela de
   procedência acima. Quem confere não pode ser quem transcreveu.

Quando tudo estiver preenchido e conferido, troque `status: rascunho` por um
status normal (ou remova a linha) no `referencia.yaml` — só então o caso entra
na execução do `lyra-validar`.

## Ressalvas

Registre aqui qualquer decisão de interpretação tomada durante a transcrição.
Estas notas viram texto do capítulo de resultados — em especial quando
explicam uma divergência entre o LYRA e o valor publicado.

- Fatores identificados na pesquisa anterior: H2O2, pH, Fe²⁺ (nomes e ordem
  a confirmar contra o artigo real antes de virar `x1`, `x2`, `x3`).
- Resposta: remoção de TOC (%).
- α (parâmetro axial do CCD) = 1,68 — confirmar contra o artigo, não contra
  esta nota.
