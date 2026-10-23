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
- **Acesso em:** 2026-10-23, por leitura assistida (ferramenta de IA), não
  humano abrindo o PDF — ver pendência abaixo.
- **Tipo de planejamento:** CCD ortogonal rotacional, 3 fatores, 5 níveis (−α, −1, 0, +1, +α), 20 ensaios
- **Nº de ensaios:** 20

## Procedência dos dados

De onde saiu cada coisa. Sem isto, ninguém consegue reconferir a transcrição
— nem vocês daqui a dois meses.

Os números de `dados.csv` e `referencia.yaml` vieram de uma ferramenta de IA
lendo o mirror PMC (duas consultas, a segunda para separar os 6 pontos
centrais que a primeira devolveu como um intervalo) — **ainda não é a dupla
conferência humana que este repositório exige.** Antes de usar este caso como
evidência final do capítulo de resultados, uma pessoa precisa abrir
`PMC5456803` (ou o PDF via DOI) e conferir item a item, preenchendo as duas
colunas abaixo.

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Matriz de ensaios (`dados.csv`) | Tabela 2 (observado × previsto, 20 ensaios) | IA (WebFetch, 2026-10-23) | |
| Equação do modelo / coeficientes de remoção de TOC | Corpo do texto, equação do modelo quadrático | IA (WebFetch, 2026-10-23) | |
| Tabela ANOVA (GL, QM, F, p — SQ por termo não extraída) | Tabela 3 | IA (WebFetch, 2026-10-23) | |
| R² / R² ajustado | Junto da Tabela 3 | IA (WebFetch, 2026-10-23) | |
| Condição ótima (previsto e confirmação experimental) | Tabela 4 | IA (WebFetch, 2026-10-23) | |

## Ressalvas

Registre aqui qualquer decisão de interpretação tomada durante a transcrição.
Estas notas viram texto do capítulo de resultados — em especial quando
explicam uma divergência entre o EnsaIA e o valor publicado.

- Fatores: H2O2 (g/L), pH, Fe²⁺ (mg/L) — nomes e unidades conforme a leitura;
  confirmar contra o artigo real antes de assumir como definitivo.
- Resposta: remoção de TOC (%).
- α (parâmetro axial do CCD) = 1,68 nominal; os valores axiais lidos por
  fator (ver `referencia.yaml`, observações) têm pequenas divergências do
  α teórico aplicado ao centro/passo — confirmar se é arredondamento do
  artigo ou dose real de laboratório.
- SQ por termo da ANOVA (Tabela 3) não foi extraída, só GL/QM/F/p — se o
  §4.3 exigir, voltar à fonte para completar.
