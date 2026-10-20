# Registro de resultados de validação: 27 de setembro de 2026

> **Nota de 2026-10-20 ([ADR 0013](decisoes/0013-restricao-a-dccr.md)):** os
> dois casos originalmente documentados aqui — `mazloomi-2023-zif67-
> metronidazol` e `go-2022-levofloxacino-hidroxiapatita-bbd` — eram
> Box-Behnken e saíram de escopo quando o EnsaIA passou a reconhecer só o
> DCCR. As seções específicas a eles foram removidas deste registro; o que
> resta é o que continua valendo independentemente do tipo de planejamento.

## Finalidade

Este documento registra os resultados obtidos na reprodução manual de casos de
estudo publicados. Ele é evidência de trabalho exploratório e de conferência
numérica. Não substitui a validação automatizada oficial pelo comando
`ensaia-validar`.

O objetivo é preservar uma distinção verificável entre: (1) resultados
reproduzidos pelo núcleo estatístico, (2) referências transcritas da fonte e
(3) validações que poderão ser executadas de ponta a ponta pelo produto.

## Próximo passo técnico aprovado

Caminho oficial de validação:

1. implementar `ensaia.io.readers.ler_dados` para carregar os CSVs dos casos;
2. implementar `ensaia.validation.runner.validar_caso`;
3. fazer o runner respeitar `termos_modelo` quando houver modelo reduzido
   (reproduz exatamente o modelo publicado, mesmo quando ele não é o
   quadrático completo);
4. aplicar as métricas do protocolo, preservando valores `null` não
   publicados;
5. gerar, por caso, `resultados/analysis_result.json` e
   `resultados/metricas_validacao.json`;
6. executar e registrar os casos pelo comando `uv run ensaia-validar`;
7. só então realizar a conferência dupla humana e usar os artefatos gerados
   como evidência final do capítulo de resultados.

O caso de estudo deve ser um DCCR com dados, ANOVA e resultados publicados
comparáveis (ver `docs/pesquisa/casos-de-estudo-candidatos.md`, seção CCD).
Dados de misturas não devem ser usados como caso comum de RSM antes de uma
extensão formal baseada em modelos de Scheffé ou pseudocomponentes.

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
3. O runner usa `termos_modelo` quando o caso o declara, reproduzindo o
   modelo exatamente como publicado em vez do quadrático completo padrão.

O diretório `tylosin-photo-fenton` recebeu o estado explícito `rascunho` e é
excluído da execução automática. Ele não possui ensaios reais transcritos e
não pode ser apresentado como caso validado.

Os próximos passos continuam sendo as métricas do protocolo e a geração dos
JSONs de evidência.
