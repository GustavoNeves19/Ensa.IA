# Shortlist de Casos de Estudo para o TCC EnsaIA

## Critério de corte aplicado

Nenhum dos 11 candidatos tem `confiabilidade: "baixa"`, `existe: false` ou `url_resolve: false` na verificação — então, pelo filtro literal do §4.2, nenhum é tecnicamente descartado. Mas "aprovado no filtro" não é o mesmo que "recomendável para citar direto". Por isso separei em três grupos por tipo de planejamento e, dentro de cada um, dividi entre **recomendado (confiabilidade alta, dados batem sem ressalva relevante)** e **não recomendado sem correção manual (confiabilidade média, com erro factual concreto encontrado)**. Só escrevi `fonte.md` pronto para os candidatos que considero seguros para entrar no pipeline; os de confiabilidade média ficam como alerta, não como recomendação.

---

## 1. Fatorial 2^k

### Recomendado — Extração de polifenóis de *Crataegus monogyna* (MAE)

**Diretório sugerido:** `casos_de_estudo/crataegus-monogyna-mae-polifenois/fonte.md`

```
# Caso de estudo: Extração assistida por micro-ondas de polifenóis de Crataegus monogyna

**Referência (ABNT):**
GAVRILA, Adina I.; DAMIAN, Emilia J.; ROSCA, Anca; CALINESCU, Ioan;
HODOSAN, Camelia; POPA, Ioana. Optimization of Microwave-Assisted
Extraction of Polyphenols from Crataegus monogyna L. Antioxidants,
Basel, v. 14, n. 3, art. 357, 2025.

**DOI:** https://doi.org/10.3390/antiox14030357
**Mirror de acesso aberto verificado:** https://pmc.ncbi.nlm.nih.gov/articles/PMC11939473/

## Tipo de planejamento
Fatorial 2^3 completo (8 ensaios de vértice, sem réplica) + 4 réplicas
no ponto central = 12 ensaios no total. NÃO é um 2^3 "puro" fechado:
os 4 pontos centrais foram usados para estimar erro puro / falta de
ajuste, junto com os vértices, na mesma ANOVA.

## Fatores e níveis
- x1: razão solvente/planta, 10-30 mL/g
- x2: temperatura, 50-70 °C
- x3: concentração de etanol, 25-75%
- Respostas: teor de fenólicos totais (TPC) e atividade antioxidante (AA)

## Modelo ajustado (sem termos quadráticos, notação EnsaIA)
- TPC: 77,46 + 3,68 x1 + 4,86 x2 + 10,36 x3 − 2,43 x2:x3
- AA: 224,09 + 18,95 x1 + 8,87 x2 + 7,54 x3

## O que foi verificado
- Título, autores, periódico e DOI conferem exatamente com PMC11939473.
- Tabela 9 (12 ensaios) e Tabela 10 (ANOVA com SQ, GL, QM, F, p por
  termo, incluindo falta de ajuste não significativa: p=0,1604 TPC,
  p=0,2322 AA) conferidas diretamente no texto.
- R²=0,9847 (TPC) e R²=0,9760 (AA) conferidos.
- Condição ótima confirmada: S/P=20,4 mL/g, T=65 °C, EtOH=60% →
  TPC=116,23±2,85 mg GAE/g, AA=237,6±6,33 mg TE/g.

## Alertas para revisão humana antes do referencia.yaml
- Para validar o núcleo EnsaIA contra um 2^3 fechado "de livro-texto",
  isole apenas as 8 linhas de vértice da Tabela 9 e refaça o ajuste OLS
  só com elas — a ANOVA publicada mistura vértices e pontos centrais.
- Confirmar manualmente que os 4 ensaios centrais realmente têm o
  mesmo ponto (S/P=20, T=60, EtOH=50) antes de decidir se entram na
  validação como "réplicas puras" ou ficam de fora.
```

### Alternativas com ressalva — confiabilidade média, **não recomendadas sem correção**

Nenhuma delas é um bom substituto direto do Crataegus; ambas têm um problema específico que precisa ser resolvido antes de virar referência formal:

- **Biodiesel com catalisadores MoO3** (Silva et al., 2024, *Molecules* 29(10):2404, DOI 10.3390/molecules29102404). É de fato um 2^3 completo com 8 ensaios, mas a "réplica" é **duplicata analítica de injeção no cromatógrafo**, não repetição da reação — a descrição do tipo de planejamento no candidato original está enganosa e precisa ser corrigida. Além disso a equação de regressão completa (todos os coeficientes, incluindo interação tripla) veio corrompida em duas tentativas de extração automatizada; exige baixar o PDF original (mdpi.com bloqueia com 403) e conferir manualmente a Equação (2) antes de usar qualquer coeficiente no critério (a) do §4.3.
- **Óleo essencial de *Elyonurus hensii*** (Loumouamou et al., 2017, *Food Science & Nutrition* 5(3):784-792, DOI 10.1002/fsn3.459). 2^3 puro, 8 ensaios, sem réplica nem ponto central — estrutura mais "limpa" que o MoO3 — mas **não publica ANOVA nem p-valores** (só coeficientes de regressão), o que conflita com a exigência do §4.2 de ao menos significância dos termos. Também tem erro de autoria: os prenomes corretos são Aubin Nestor Loumouamou, Kévin Bikindou, Ernest Bitemou, Pierre Chalard, Thomas Silou, Gilles Figueredo (sobrenomes batem, prenomes do candidato original estavam errados em 4 dos 6 autores).

---

## 2. CCD (Delineamento Composto Central)

Este foi o tipo de planejamento com mais candidatos de confiabilidade alta — 4 no total. Recomendo um principal e listo os outros três como alternativas igualmente sólidas, cada uma com uma característica que pode interessar a diferentes partes do TCC.

### Recomendado principal — Degradação de tilosina por foto-Fenton

**Diretório sugerido:** `casos_de_estudo/tylosin-photo-fenton/fonte.md`

```
# Caso de estudo: Degradação de tilosina via reação foto-Fenton (CCD)

**Referência (ABNT):**
SARRAI, Abd Elaziz; HANINI, Salah; MERZOUK, Nachida Kasbadji;
TASSALIT, Djilali; SZABÓ, Tibor; HERNÁDI, Klára; NAGY, László. Using
Central Composite Experimental Design to Optimize the Degradation of
Tylosin from Aqueous Solution by Photo-Fenton Reaction. Materials,
Basel, v. 9, n. 6, art. 428, 2016.

**DOI:** https://doi.org/10.3390/ma9060428
**Mirror de acesso aberto verificado:** https://pmc.ncbi.nlm.nih.gov/articles/PMC5456803/

## Tipo de planejamento
CCD ortogonal rotacional, 3 fatores em 5 níveis (-α, -1, 0, +1, +α),
α=1,68; 20 ensaios no total.

## Fatores e níveis
- x1: H2O2
- x2: pH
- x3: Fe2+
- Resposta: remoção de TOC (%)

## Modelo ajustado (notação EnsaIA)
Y = 88,2 − 2,2 x1 − 11,9 x2 + 10,2 x3 − 4,2 x1:x2 + 4,4 x1:x3 + 0,5 x2:x3
    − 0,3 x1^2 − 16,4 x2^2 − 3,2 x3^2

## O que foi verificado
- Título, autores e periódico conferem exatamente com PMC5456803.
- Tabela 2 (20 ensaios, observado x previsto): ensaio 6 = 96,04%
  conferido diretamente no texto.
- Tabela 3 (ANOVA completa): SQ=7698,9, GL=9, QM=855,4, F=75,7,
  p<0,001; R²=0,986; R²aj=0,973. Conferido termo a termo.
- Equação do modelo conferida coeficiente a coeficiente.
- Condição ótima (Tabela 4): H2O2=0,4 g/L, pH=2,6, Fe2+=6 mg/L,
  remoção prevista 100%, confirmação experimental 97,1%.

## Alertas para revisão humana antes do referencia.yaml
Nenhum alerta crítico. É o candidato mais limpo do lote: modelo
quadrático completo com todos os termos e coeficientes publicados
diretamente no corpo do texto, ANOVA clássica completa, condição
ótima com confirmação experimental. Bom candidato "principal" de CCD
para os critérios (a)-(d) do §4.3.
```

### Outras opções sólidas em CCD (também confiabilidade alta)

- **Fenton vs. Taguchi** (Asghar; Abdul Raman; Wan Daud, 2014, *The Scientific World Journal* 2014:869120, DOI 10.1155/2014/869120). CCD com 30 ensaios, **4 fatores** (concentração do corante, H2O2:Fe2+, corante:Fe2+, pH), 2 respostas (DQO e descoloração). ANOVA e condição ótima (desejabilidade 0,972) conferidas. Interessante porque compara CCD contra Taguchi no mesmo processo — pode virar discussão metodológica no TCC. Único ponto não 100% conferido: a equação quadrática completa (só o início foi checado literalmente).
- **Transesterificação de óleo de girassol** (KoohiKamali; Tan; Ling, 2012, *The Scientific World Journal* 2012:475027, DOI 10.1100/2012/475027). CCD com 20 ensaios, 3 fatores, 6 pontos centrais. Modelo reduzido simples (Y=96,38−0,794x1+0,733x3+0,528x2²), ANOVA com F e p por termo conferida. É o processo mais "clássico" de engenharia química do lote (transesterificação/biodiesel), bom se quiser variar o domínio de aplicação. Pequena divergência de arredondamento no R² (0,88 vs 0,889 citado) não compromete a referência, mas vale conferir o valor exato na Tabela 3 do PDF.
- **Zeólita 4A para efluente multicatiônico** (Nseke; Baloyi, 2024, *Heliyon* 10(15):e35176, DOI 10.1016/j.heliyon.2024.e35176). CCD com 29 ensaios, **4 fatores**, mas com **3 respostas simultâneas** (Cd²⁺, Cu²⁺, Zn²⁺) — três ANOVAs completas e três equações quadráticas, todas conferidas com R² entre 0,9917 e 0,9983. É o único caso com desejabilidade genuinamente multirresposta; útil se o TCC quiser testar o EnsaIA nesse cenário, mas aumenta a complexidade de validação (3 modelos em vez de 1).

---

## 3. Box-Behnken

### Recomendado principal — Carvão ativado de resíduos de manga (adsorção de azul de metileno)

**Diretório sugerido:** `casos_de_estudo/mango-peels-carvao-ativado/fonte.md`

```
# Caso de estudo: Carvão ativado de cascas/sementes de manga para adsorção de azul de metileno (BBD)

**Referência (ABNT):**
RAZALI, Nur Shahirah et al. High-Surface-Area-Activated Carbon
Derived from Mango Peels and Seeds Wastes via Microwave-Induced
ZnCl2 Activation for Adsorption of Methylene Blue Dye Molecules:
Statistical Optimization and Mechanism. Molecules, Basel, v. 27,
n. 20, art. 6947, 2022.

**DOI:** https://doi.org/10.3390/molecules27206947
**Mirror de acesso aberto verificado:** https://pmc.ncbi.nlm.nih.gov/articles/PMC9607410/

## Tipo de planejamento
Box-Behnken (RSM), 3 fatores x 3 níveis, 17 ensaios (12 pontos
fatoriais + 5 pontos centrais, ensaios 13-17).

## Fatores e níveis
- x1 (A): dose de adsorvente MSMPAC, 0,02-0,1 g
- x2 (B): pH, 4-10
- x3 (C): tempo, 5-15 min
- Resposta: remoção de azul de metileno (%)

## Modelo reduzido (termos não significativos já removidos, notação EnsaIA)
Y = 76,80 + 10,41 x1 + 2,54 x2 + 4,03 x3 + 2,52 x1:x2 + 2,65 x1:x3 + 4,66 x1^2

## O que foi verificado
- Título completo real tem subtítulo ("... Molecules: Statistical
  Optimization and Mechanism") que o candidato original omitiu — o
  DOI e o conteúdo batem, é só truncamento do título, não erro de
  fonte.
- Tabela 2 (matriz BBD completa, 17 ensaios, no corpo do texto, não
  em suplementar) conferida.
- Tabela 4 (ANOVA clássica completa: SQ, GL, QM, F, p por termo,
  incluindo falta de ajuste p=0,4143) conferida no texto.
- Equação do modelo reduzido conferida idêntica.
- R²=0,97 conferido textualmente.
- Condição ótima confirmada: dose 0,09 g, pH 8,7, tempo 14,8 min →
  98,1% de remoção, desirability=1,0.

## Alertas para revisão humana antes do referencia.yaml
- Lista de autores incompleta: nem o candidato original nem a
  verificação extraíram a lista completa dos coautores (só "Nur
  Shahirah Razali et al." foi confirmado). Antes de gerar a
  referencia.yaml, abrir o PDF/PMC e copiar a lista completa de
  autores para a citação ABNT ficar completa.
- R² ajustado não foi localizado no texto extraído — se o §4.3
  critério (c) exigir R² ajustado, confirmar se ele aparece em algum
  material suplementar antes de assumir que não existe.
```

### Alternativa sólida — Biodiesel de macroalga *Chara vulgaris*

**Diretório sugerido:** `casos_de_estudo/chara-vulgaris-biodiesel/fonte.md`

```
# Caso de estudo: Biodiesel de macroalga costeira Chara vulgaris (BBD)

**Referência (ABNT):**
SIDDIQUA, Shaila; ABDULLAH AL MAMUN; BABAR, Sheikh Md Enayetul.
Production of biodiesel from coastal macroalgae (Chara vulgaris)
and optimization of process parameters using Box-Behnken design.
SpringerPlus, v. 4, art. 720, 2015.

**DOI:** https://doi.org/10.1186/s40064-015-1518-1
**Mirror de acesso aberto verificado:** https://pmc.ncbi.nlm.nih.gov/articles/PMC4656264/

## Tipo de planejamento
Box-Behnken (RSM), 3 fatores x 3 níveis, 15 ensaios (12 pontos
fatoriais + 3 pontos centrais).

## Fatores e níveis
- x1: volume de clorofórmio, mL
- x2: % de NaCl
- x3: temperatura, °C
- Respostas: extrato lipídico, poder calorífico, rendimento

## O que foi verificado
- Matriz completa dos 15 ensaios conferida linha a linha (ex.:
  ensaio 1: 118,8 mL / 0,70% / 60 °C → extrato 14 mL, PC=9167,173
  kcal/kg, rendimento 3,0 mL; ensaio 8: 198 mL / 0,75% / 65 °C →
  extrato 19 mL, PC=9255,106 kcal/kg, rendimento 3,5 mL).
- Equações 2 e 3 (modelos quadráticos completos) conferidas.
- R²=0,947995 (PC) e R²=0,976573 (rendimento) conferidos exatamente.
- Condição ótima confirmada: 198 mL clorofórmio, 0,75% NaCl, 65 °C →
  PC=9255,106 kcal/kg, rendimento 3,6 mL previsto.

## Alertas para revisão humana antes do referencia.yaml
- O artigo NÃO publica R² ajustado nem tabela ANOVA formal
  (SQ/GL/QM/F) — só coeficiente de regressão + p-valor por termo na
  Tabela 4. Se o §4.3 critério (c) exigir R² ajustado explícito, este
  caso não atende sem cálculo manual a partir de n=15 e do número de
  parâmetros do modelo.
- Grafia do segundo autor varia entre fontes ("Abdullah-Al-Mamun" no
  candidato original vs. "Abdullah Al Mamun" sem hífen no texto
  original) — usar a grafia sem hífen na referência final.
```

### Não recomendadas sem correção (confiabilidade média)

- **Nanocompósito magnético para múltiplos contaminantes** (Buenaño; Ali; Jafer et al., 2024, *Scientific Reports* 14:6950, DOI 10.1038/s41598-024-57616-8). BBD com 4 fatores, 27 ensaios, 3 respostas simultâneas, ANOVA e R²/R²aj completos — estruturalmente é o candidato mais rico do lote. Mas a verificação encontrou **erro factual real**: os intervalos de pH e tempo de contato citados (pH 3-10, tempo 10-30 min) não batem com a Tabela 1 do artigo, que traz pH 4-10 e tempo 5-15 min. Usável, mas só depois de corrigir esses dois intervalos.
- **Carvão ativado de *Ceratophyllum demersum*** (A. Taouda et al., 2026, *Water Environment Research* 98(7):e70510, DOI 10.1002/wer.70510). BBD com 3 fatores, 15 ensaios, ANOVA completa e equação reduzida conferidas. Tem erro de autoria (candidato citou "H. Taouda", correto é "Amal Taouda") e dois valores pontuais da tabela de ensaios (36,186 mg/g e 270,186 mg/g) não puderam ser confirmados célula a célula — não estão contraditados, mas também não estão confirmados. Corrigir o nome do autor e reconferir esses dois valores antes de citar.

---

## Cobertura dos três tipos de planejamento

| Tipo | Candidato(s) confiabilidade alta disponível(is)? | Recomendação principal |
|---|---|---|
| Fatorial 2^k | Sim, 1 (Crataegus monogyna) | Crataegus, **com a ressalva de que é um híbrido 2³ + 4 pontos centrais**, não um 2³ fechado puro |
| CCD | Sim, 4 (Tylosin, Fenton/Taguchi, Sunflower oil, Zeolite 4A) | Tylosin como principal; os outros três são reservas igualmente confiáveis |
| Box-Behnken | Sim, 2 (Mango peels, Chara vulgaris) | Mango peels como principal (ANOVA clássica completa); Chara vulgaris como reserva |

Os três tipos de planejamento têm pelo menos um candidato de confiabilidade alta, então não é necessário forçar nenhuma recomendação fraca. A única ressalva relevante é no fatorial 2^k: não há, entre os candidatos de confiabilidade alta, um 2³ **fechado e puro** (8 ensaios, sem réplica nem ponto central) — o único de confiabilidade alta (Crataegus) mistura vértices com pontos centrais, e os dois candidatos que são de fato 2³ puros (MoO3 e Elyonurus) caíram em confiabilidade média por problemas específicos (tipo de réplica mal descrito e equação corrompida no MoO3; ausência de ANOVA e erro de autoria no Elyonurus). Se o TCC exigir estritamente um 2³ fechado sem adaptação, recomendo tratar essa lacuna como pendência de busca — não usar MoO3/Elyonurus como estão, nem forçar o Crataegus como se fosse um 2³ puro sem deixar essa adaptação documentada no `referencia.yaml`.