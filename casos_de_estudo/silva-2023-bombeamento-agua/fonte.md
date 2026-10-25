# Fonte do caso de estudo: consumo de energia de um sistema de bombeamento (R2)

Artigo de referência R2 da especificação v0.6 (§14.3).

## Citação (ABNT)

> SILVA, Alcione Batista da; PEREIRA, José Almir Rodrigues; ALMEIDA, Aline
> Christian Pimentel. Desenvolver modelo matemático para otimização de sistema
> de bombeamento de água. **Research, Society and Development**, v. 12, n. 8,
> e3512842839, 2023. DOI: 10.33448/rsd-v12i8.42839.

- **DOI / URL:** https://doi.org/10.33448/rsd-v12i8.42839
- **PDF:** https://rsdjournal.org/rsd/article/download/42839/34550
- **Licença:** CC BY 4.0.
- **Acesso em:** 2026-10-25.
- **Tipo de planejamento:** DCCR, 3 fatores (rendimento do conjunto
  motor-bomba, volume do reservatório elevado e altura geométrica), 8
  fatoriais + 6 axiais + 1 central. Os "ensaios" são simulações no Epanet.
- **Nº de ensaios:** 15.
- **Software do artigo:** Protimiza.

## Procedência dos dados

O texto foi extraído do PDF oficial com `pypdf` e transcrito tabela por tabela.
Com os dados abaixo, o pipeline do EnsaIA reproduz a Tabela 11 até a última
casa publicada (coeficientes, erros-padrão e p-valores). Ainda falta a dupla
conferência humana que `casos_de_estudo/README.md` exige.

| Conteúdo | Origem no artigo | Transcrito por | Conferido por |
|---|---|---|---|
| Matriz codificada e real (`dados.csv`) | Tabelas 6 e 7, p. 14–15 | IA (pypdf, 2026-10-25) | |
| Consumo de energia elétrica | Tabela 13, coluna "Simulados", p. 23 | IA (pypdf, 2026-10-25) | |
| Coeficientes, erros-padrão e p | Tabela 11, p. 21 | IA (pypdf, 2026-10-25) | |
| Modelo reduzido e ANOVA | Equação 18 e Tabela 12, p. 22 | IA (pypdf, 2026-10-25) | |
| Condição ótima | Tabelas 14 e 15, p. 26 | IA (pypdf, 2026-10-25) | |

## Ressalvas

- **Duas tabelas de consumo divergem.** A Tabela 10 repete no ensaio 3 o
  valor do ensaio 2 (4.501,20) e dá 6.612,30 no ponto central. A Tabela 13
  ("Simulados") dá 9.995,10 e 6.212,30. Só os valores da Tabela 13 reproduzem
  a Tabela 11 (com os da Tabela 10, R² = 0,909 e os coeficientes não batem).
  `dados.csv` usa a Tabela 13.
- **Ordem dos fatores.** A Tabela 5 lista a altura geométrica como x₂ e o
  volume como x₃, mas as Tabelas 4, 6, 7 e 11 usam x₂ = volume e x₃ = altura.
  Vale a ordem das Tabelas 7 e 11.
- **Matriz codificada e α exato.** Os valores reais dos axiais estão
  arredondados (por exemplo, volume 1.347 e 23.583 m³ na Tabela 7, contra
  1.335 e 23.570 na Tabela 6). `dados.csv` usa os códigos com α = 8^(1/4) =
  1,68179, que reproduzem a Tabela 11 exatamente. Níveis reais (−1 / 0 / +1):
  rendimento 40 / 60 / 80%; volume 3.706 / 11.118 / 18.530 m³; altura
  18 / 28 / 38 m.
- **"Efeito" é coeficiente.** A Tabela 11 chama a coluna de "Efeito", mas os
  valores são os coeficientes codificados (os lineares são os mesmos da
  Equação 18).
- **Termo de erro: resíduo.** Há um só ponto central (simulação
  determinística), então não existe erro puro.
- **Modelo reduzido reajustado.** A Equação 18 tira os termos não
  significativos e reajusta: o intercepto passa de 6.178,45 para 6.128,94 e os
  quadráticos mudam, como faz o EnsaIA (ADR 0014). O R² publicado (99,27%) e a
  ANOVA da Tabela 12 são desse modelo reduzido; por isso `r2` do modelo
  completo fica `null`, e o reduzido é conferido no teste unitário.
- **Condição ótima escolhida a olho.** Os autores escolheram (83%; 1.347 m³;
  19,2 m), codificada (+1,15; −1,32; −0,58), olhando as superfícies do modelo
  reduzido. O otimizador do EnsaIA (modelo completo, região ±α) dá (1,01;
  −1,68; −0,35). Ao minimizar, a desejabilidade satura em d = 1 abaixo do
  menor consumo observado, e toda condição nessa região empata. A diferença
  (7% a 18% da faixa) vai para a discussão, sem tolerância fixada (§4.3 d).

## Conferência numérica (2026-10-25)

- (a) coeficientes: 10/10 dentro de 5% (maior erro 0,01%).
- (b) significância: 10/10.
- Modelo reduzido da Equação 18: coeficientes, R² = 99,27% e F = 180,7
  reproduzidos (ver o teste unitário).
