# 0002 — Generalizar de 3 fatores fixos para k fatores

**Status:** Aceita · **Data:** 2026-08-23

## Contexto

O protótipo do EnsaIA foi escrito para exatamente três variáveis independentes.
O número 3 aparece espalhado pelo código: na construção do modelo polinomial,
na malha de otimização, na interface.

O pré-projeto assinado promete outra coisa. O §4.2, critério 2, exige
"cobertura de diferentes tipos de planejamento experimental (ex.: fatorial
completo 2^k, delineamento composto central, Box-Behnken), de modo a testar o
EnsaIA em cenários de complexidade crescente".

Um 2^k com k fixo em 3 não é 2^k. Os casos de estudo publicados que servem de
referência têm 2, 3, 4 fatores conforme o experimento — travar em 3 reduz
drasticamente o conjunto de casos elegíveis e enfraquece a validação.

## Decisão

O número de fatores é dado de entrada, não constante de código.

- `Planejamento` guarda uma lista de `Fator` de tamanho arbitrário.
- `termos_do_modelo(nomes, ...)` gera os termos combinatoriamente a partir da
  lista.
- A notação dos termos é canônica e estável (`"x1"`, `"x1^2"`, `"x1:x2"`), com
  os fatores de uma interação sempre na ordem em que foram declarados.

Essa última parte parece detalhe e não é. A validação do §4.3(a) casa os
coeficientes do EnsaIA com os publicados **por nome**. Se a notação variar entre
execuções, o termo aparece como "ausente na referência" e a métrica degrada
sem erro nenhum aparecer.

## Consequências

- A malha de otimização cresce com `pontos_por_fator^k`. Com 15 pontos e k=3
  são 3.375 avaliações; com k=5, 759.375. Acima de k=4 é preciso trocar a
  malha por amostragem por hipercubo latino — registrado como TODO em
  `desirability.py`.
- A interface não pode mais ter três campos fixos: precisa gerar os campos a
  partir dos dados carregados.
- Nem todo modelo é estimável para todo k: um fatorial 2^k puro não tem graus
  de liberdade para termos quadráticos. Daí o parâmetro
  `incluir_quadraticos`, e daí a verificação de posto antes do ajuste.

## Relacionadas

Planejamento de misturas (simplex, modelos de Scheffé) **não** está no escopo
do pré-projeto assinado, e a decisão de deixá-lo de fora foi tomada em
julho/2026. Fica registrado que ele exige tratamento diferente — a restrição
de soma unitária torna o intercepto colinear e o modelo de Scheffé não tem
termo independente. Não é uma extensão trivial de k fatores. Assunto para
trabalhos futuros.
