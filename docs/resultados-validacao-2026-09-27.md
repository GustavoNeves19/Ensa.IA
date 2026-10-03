# Registro de resultados de validação: 27 de setembro de 2026

## Finalidade

Este documento registra os resultados obtidos na reprodução manual de casos de
estudo publicados. Ele é evidência de trabalho exploratório e de conferência
numérica. Não substitui a validação automatizada oficial pelo comando
`ensaia-validar`, que ainda não está implementada neste checkout.

O objetivo é preservar uma distinção verificável entre: (1) resultados
reproduzidos pelo núcleo estatístico, (2) referências transcritas da fonte e
(3) validações que poderão ser executadas de ponta a ponta pelo produto.

## Casos formalizados

| Caso | Planejamento e modelo publicado | Status em 27/09/2026 |
|---|---|---|
| `mazloomi-2023-zif67-metronidazol` | Box-Behnken, 3 fatores, modelo quadrático completo | Reprodução manual concluída |
| `go-2022-levofloxacino-hidroxiapatita-bbd` | Box-Behnken, 3 fatores, modelo 2FI | Reprodução manual concluída |

Os dois casos têm a estrutura definida no ADR 0004: `dados.csv`,
`referencia.yaml` e `fonte.md`. Os arquivos de resultado em `resultados/`
somente devem ser gerados quando o pipeline oficial estiver implementado.

## Resultado novo: Go et al. (2022)

O caso `go-2022-levofloxacino-hidroxiapatita-bbd` foi cadastrado a partir da
planilha suplementar oficial do estudo de Go et al. (2022), disponível também
no acervo local. O estudo declara o uso do MINITAB 17 para o modelo de
superfície de resposta e a ANOVA.

O planejamento tem 15 ensaios, três fatores e três repetições no ponto central:

- dose de catalisador, de 0,5 a 1,5 g/L;
- concentração de levofloxacino, de 4 a 10 ppm;
- pH, de 4 a 10.

### Modelo comparado

Embora o delineamento seja Box-Behnken, a publicação selecionou um modelo
**2FI**, e não o modelo quadrático completo. Portanto, a reprodução usou
exatamente sete parâmetros: intercepto, três termos lineares e três interações
de dois fatores. Termos quadráticos não foram inseridos na comparação.

Essa escolha é metodologicamente necessária: comparar um quadrático completo
do EnsaIA contra um 2FI publicado mudaria R², coeficientes e testes de
significância por efeito da seleção de modelo, não por divergência de cálculo.

### Comparação numérica

| Métrica ou coeficiente | EnsaIA, reprodução manual | Estudo / MINITAB 17 |
|---|---:|---:|
| R² | 0,9708 | 0,9708 |
| R² ajustado | 0,9489 | 0,9489 |
| Soma de quadrados residual | 38,90 | 38,90 |
| Intercepto | 53,349 | 53,349 |
| Dose de catalisador | 7,025 | 7,025 |
| Concentração de levofloxacino | -7,538 | -7,538 |
| pH | 3,870 | 3,870 |
| Dose × concentração | 5,225 | 5,230 |
| Dose × pH | 7,060 | 7,060 |
| Concentração × pH | 2,025 | 2,030 |

R², R² ajustado e soma de quadrados residual coincidem com a precisão
publicada. As diferenças máximas de 0,005 nos coeficientes de interação são
compatíveis com o arredondamento apresentado na fonte.

A referência também registra falta de ajuste não significativa: SQ = 17,72,
GL = 6, F = 0,28 e p = 0,906. O p-valor do intercepto não foi publicado e
permanece `null`, sem inferência.

### Rastreabilidade e pendência de conferência

A procedência de cada bloco está descrita em
`casos_de_estudo/go-2022-levofloxacino-hidroxiapatita-bbd/fonte.md`, incluindo
abas e linhas da planilha. A transcrição ainda exige conferência dupla humana
antes de ser utilizada como evidência final para a banca.

## Resultado anterior: Mazloomi et al. (2023)

O caso `mazloomi-2023-zif67-metronidazol` também foi formalizado com 15
ensaios Box-Behnken e modelo quadrático completo de três fatores. A reprodução
manual obteve:

| Métrica | EnsaIA, reprodução manual | Artigo |
|---|---:|---:|
| R² | 0,985314 | 0,9853 |
| R² ajustado | 0,958879 | 0,9589 |
| Soma de quadrados residual | 44,0342 | 44,03 |

Coeficientes e ANOVA ficaram compatíveis com o arredondamento da publicação.
A falta de ajuste reportada no artigo é SQ = 39,37, GL = 3, F = 5,62 e
p = 0,1547. O p-valor do intercepto continua `null` porque não foi reportado.

## Interpretação para o TCC

Os dois casos fornecem evidência de que o núcleo estatístico do EnsaIA consegue
reproduzir indicadores e coeficientes publicados de experimentos químicos
reais. O caso Go et al. adiciona uma comparação direta com resultados gerados
no MINITAB 17, um software comercial, enquanto o caso Mazloomi et al. cobre o
modelo quadrático completo.

Ainda não é correto afirmar que a validação está automatizada ou finalizada.
O resultado atual deve ser descrito como **reprodução manual do núcleo
estatístico, com fontes rastreáveis e conferência dupla pendente**.

## Próximo passo técnico aprovado

Implementar o caminho oficial de validação nesta ordem:

1. implementar `ensaia.io.readers.ler_dados` para carregar os CSVs dos casos;
2. implementar `ensaia.validation.runner.validar_caso`;
3. fazer o runner respeitar `termos_modelo` quando houver modelo reduzido,
   especialmente o 2FI de Go et al.;
4. aplicar as métricas do protocolo, preservando valores `null` não
   publicados;
5. gerar, por caso, `resultados/analysis_result.json` e
   `resultados/metricas_validacao.json`;
6. executar e registrar os dois casos pelo comando `uv run ensaia-validar`;
7. só então realizar a conferência dupla humana e usar os artefatos gerados
   como evidência final do capítulo de resultados.

O terceiro caso deve ser escolhido depois dessa automação, priorizando um CCD
com dados, ANOVA e resultados publicados comparáveis. Dados de misturas não
devem ser usados como caso comum de RSM antes de uma extensão formal baseada em
modelos de Scheffé ou pseudocomponentes.

## Estado do repositório nesta data

O leitor `ler_dados` e o runner `validar_caso` ainda lançam
`NotImplementedError`. Por isso, esta documentação não declara os comandos de
validação como executados, nem cria JSONs que poderiam ser confundidos com
saída oficial do produto.

## Atualização de implementação: 28 de setembro de 2026

Os três primeiros passos do caminho oficial foram implementados e verificados:

1. `ensaia.io.readers.ler_dados` lê CSV, XLSX e XLS, ignora comentários de CSV,
   detecta separador comum e aceita CSV brasileiro com `;` e vírgula decimal.
2. `ensaia.validation.runner.validar_caso` agora lê a referência, constrói o
   planejamento e ajusta cada resposta pelo núcleo OLS determinístico.
3. O runner usa `termos_modelo` quando o caso o declara. Assim, o caso Go et
   al. é executado como 2FI, com sete parâmetros, e não como quadrático
   completo. Na ausência desse campo, o modelo quadrático padrão é gerado.

O comando `uv run ensaia-validar` executa os dois casos aptos neste momento:

| Caso | R² calculado | R² ajustado calculado | SSR calculada |
|---|---:|---:|---:|
| Go et al. (2022) | 0,9708 | 0,9489 | 38,8985 |
| Mazloomi et al. (2023) | 0,9853 | 0,9589 | 44,0342 |

O diretório `tylosin-photo-fenton` recebeu o estado explícito `rascunho` e é
excluído da execução automática. Ele não possui ensaios reais transcritos e
não pode ser apresentado como caso validado.

Os próximos passos continuam sendo as métricas do protocolo e a geração dos
JSONs de evidência. Eles ainda não foram implementados nesta atualização.
