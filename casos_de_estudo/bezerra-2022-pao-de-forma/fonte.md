# Fonte do caso de estudo: pão de forma por processo rápido (R1)

Artigo de referência R1 da especificação v0.6 (§14.3).

## Citação (ABNT)

> BEZERRA, Luciana Cristina Nogueira de Moraes; SILVA, Claudio Ernani Mendes
> da; NASCIMENTO, Hélio Oliveira do; CONSTANT, Patrícia Beltrão Lessa et al.
> Produção e caracterização de pão de forma obtido por processo rápido.
> **Research, Society and Development**, v. 11, n. 11, e297111133569, 2022.
> DOI: 10.33448/rsd-v11i11.33569.

- **DOI / URL:** https://doi.org/10.33448/rsd-v11i11.33569
- **PDF:** https://rsdjournal.org/index.php/rsd/article/download/33569/28453/377102
- **Licença:** CC BY 4.0.
- **Acesso em:** 2026-10-25.
- **Tipo de planejamento:** DCCR, 3 fatores (extrato flavorizante, fermento
  químico e gordura vegetal), 8 fatoriais + 6 axiais + 3 centrais.
- **Nº de ensaios:** 17.
- **Software do artigo:** Statistica 10.

## Procedência dos dados

O texto foi extraído do PDF oficial com `pypdf` e transcrito tabela por tabela.
Cada número foi conferido rodando o pipeline do EnsaIA e comparando com o que o
artigo publica (ver "Conferência numérica"). Ainda falta a dupla conferência
humana que `casos_de_estudo/README.md` exige.

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Matriz codificada e real (`dados.csv`) | Tabela 1, p. 4 | IA (pypdf, 2026-10-25) | |
| Volume específico, cor da crosta, característica interna da crosta | Tabela 3, p. 9 (médias) | IA (pypdf, 2026-10-25) | |
| Cor do miolo, estrutura das células, textura, aroma, sabor | Tabela 4, p. 10 (médias) | IA (pypdf, 2026-10-25) | |
| Efeitos e p-valores | Tabelas 5 a 8, p. 11–17 | IA (pypdf, 2026-10-25) | |

## Ressalvas

- **Matriz codificada, não real.** Os autores elevaram para 1% os pontos −α do
  extrato (de 0 para 1%) e do fermento (de −0,7 para 1%, igual ao nível −1).
  Em unidades reais, a planilha deixa de ser um DCCR simétrico, mas o
  Statistica analisou pelos valores codificados. Por isso `dados.csv` está em
  valores codificados. Níveis reais (−1 / 0 / +1): extrato 2 / 8,5 / 15%,
  fermento 1 / 3,5 / 6%, gordura 3 / 5,5 / 8%.
- **α exato.** A Tabela 1 imprime ±1,68; `dados.csv` usa 8^(1/4) = 1,68179.
  Com o α exato, os efeitos do volume específico batem com a Tabela 8 até
  5 × 10⁻⁷; com 1,68, ficam a até 0,05%.
- **Termo de erro: erro puro.** Os p-valores das Tabelas 5–8 só são
  reproduzidos com o erro puro (3 pontos centrais, 2 g.l.). Com o resíduo, a
  significância muda em vários termos.
- **Respostas são médias.** As Tabelas 3 e 4 publicam média ± desvio de um
  painel; as médias têm 2 casas. É a provável causa dos desvios pequenos nos
  p-valores (até 0,013) e no E² da cor do miolo (coeficiente de 0,03; erro
  relativo de 4,35%).
- **Coeficientes = efeito / 2.** O Statistica publica efeitos (linear,
  quadrático e interação), que valem o dobro do coeficiente codificado. O
  intercepto não é publicado.
- **5 de 8 respostas no caso.** O EnsaIA analisa até 5 respostas por vez
  (RNF-12). O caso usa volume específico, cor da crosta, cor do miolo,
  estrutura das células do miolo e sabor. Textura, aroma e característica
  interna da crosta estão em `dados.csv` e são conferidas em
  `tests/unit/test_artigos_referencia.py`.
- **Escore total ficou de fora.** Os efeitos de fermento, gordura e das três
  interações (Tabela 8) batem com o escore da Tabela 9, mas os termos que
  dependem dos axiais do extrato não (efeito linear do extrato −1,93 calculado
  contra −1,19 publicado). O escore dos ensaios 9 e 10 na Tabela 9 não deve
  ser o que entrou na análise. É uma inconsistência do próprio artigo.
- **Quebra e simetria** não têm efeitos publicados (o artigo só diz que
  nenhum termo foi significativo).
- **Modelos reduzidos não comparados.** O texto dá R² e F dos modelos
  reduzidos (por exemplo, cor do miolo 81,66%; sabor 83,05%), mas não diz
  exatamente quais termos ficaram em cada um, e as equações estão em unidades
  reais com constantes avulsas. Por isso `r2` fica `null`.
- **Sem otimização pelo modelo.** A formulação escolhida (ensaio 12) saiu do
  maior escore total observado.

## Conferência numérica (2026-10-25)

Critérios do §4.3, com o pipeline do EnsaIA, termo de erro = erro puro:

| Resposta | (a) coeficientes dentro de 5% | maior erro | (b) significância |
|---|---|---|---|
| volume específico | 9/9 | 0,00% | 9/9 |
| cor da crosta | 9/9 | 0,15% | 9/9 |
| cor do miolo | 9/9 | 4,35% (E²) | 9/9 |
| estrutura das células do miolo | 9/9 | 0,37% | 9/9 |
| sabor | 9/9 | 0,14% | 9/9 |
| textura (fora do caso) | 9/9 | 3,1% | 9/9 |
| aroma (fora do caso) | 9/9 | 0,4% | 9/9 |
| característica interna da crosta (fora do caso) | 9/9 | 0,5% | 9/9 |
