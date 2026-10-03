# Fonte do caso de estudo: remocao de metronidazol por ZIF-67-SO4

## Citacao

> MAZLOOMI, Sajad et al. Parametric study and process modeling for
> metronidazole removal by rhombic dodecahedron ZIF-67 crystals. *Scientific
> Reports*, v. 13, art. 14654, 2023. DOI: 10.1038/s41598-023-41724-y.

- **DOI:** https://doi.org/10.1038/s41598-023-41724-y
- **Texto integral local:**
  `datasets_candidatos/07-box-behnken/mazloomi-2023-zif67-metronidazol/PMC10480145_texto_completo_jats.xml`
- **Licenca:** Creative Commons Attribution 4.0 International, conforme XML
  integral salvo localmente.
- **Tipo de planejamento:** Box-Behnken, tres fatores e tres niveis.
- **Numero de ensaios:** 15, incluindo tres repeticoes no ponto central.

## Procedencia da transcricao

| Conteudo | Origem publicada | Arquivo local de apoio | Status |
|---|---|---|---|
| Matriz, fatores e resposta | Tabela 2 | `tabelas/table-2.csv` | Transcrito para `dados.csv` |
| Soma de quadrados, p-valores, R2 e R2 ajustado | Tabela 3 | `tabelas/table-3.csv` | Transcrito para `referencia.yaml` |
| Coeficientes codificados | Tabela 4 | `tabelas/table-4.csv` | Transcrito para `referencia.yaml` |
| Condicao de maior remocao | Resumo e conclusao | `PMC10480145_texto_completo_jats.xml` | Transcrito com precisao publicada |

## Conferencia necessaria

As tabelas locais foram extraidas do XML JATS do artigo. Antes de classificar
o caso como validado no texto final do TCC, Gabriel e Gustavo devem conferir a
matriz, a Tabela 3 e a Tabela 4 contra a versao renderizada do artigo. A
conferencia deve registrar nomes e data neste arquivo.

| Parte | Transcrito por | Conferido por | Data |
|---|---|---|---|
| Tabela 2 | Codex, a partir do XML local | Pendente | |
| Tabela 3 | Codex, a partir do XML local | Pendente | |
| Tabela 4 | Codex, a partir do XML local | Pendente | |

## Ressalvas metodologicas

- O valor de 97% para a condicao de maior remocao aparece arredondado no
  resumo e na conclusao. Ele serve para a comparacao de condicao otima, mas a
  precisao limitada deve aparecer no relatorio.
- A Tabela 3 nao apresenta p-valor para o intercepto. Ele permanece `null` e
  nao deve entrar no denominador da metrica de concordancia de significancia.
- A falta de ajuste publicada e nao significativa: SQ = 39,37, GL = 3,
  F = 5,62 e p = 0,1547. O runner devera reproduzir esse teste a partir das
  tres repeticoes do ponto central.
