# Protocolo de validação

Como os números do capítulo de resultados do TCC são produzidos. Documento
operacional: seguindo isto, qualquer pessoa reproduz as tabelas da monografia
a partir do repositório.

Base normativa: §4.3 do pré-projeto assinado.

## Os cinco critérios

| | O que mede | Critério de aceitação | Onde está implementado |
|---|---|---|---|
| (a) | Erro relativo dos coeficientes | ≤ 5% | `validation/metrics.erro_relativo_coeficientes` |
| (b) | Concordância de significância | α = 0,05 | `validation/metrics.concordancia_significancia` |
| (c) | Diferença de R² e R² ajustado | ≤ 0,01 | `validation/metrics.comparacao_r2` |
| (d) | Diferença na condição ótima | absoluta e % da faixa | `validation/metrics.diferenca_condicao_otima` |
| (e) | Fidelidade do relatório do LLM | classificação manual | `validation/fidelity` |

**Estes limiares vêm do documento entregue à orientadora.** Não são parâmetros
de ajuste. Alterar qualquer um exige alterar o pré-projeto — ver
[CONTRIBUTING](../CONTRIBUTING.md), regra 2.

## Procedimento por caso de estudo

1. **Cadastrar o caso.** `casos_de_estudo/<nome>/` com `dados.csv`,
   `referencia.yaml`, `fonte.md`. Transcrição conferida por quem não
   transcreveu.

2. **Rodar o pipeline determinístico.**
   ```bash
   uv run lyra-validar --caso <nome>
   ```
   Gera `<caso>/resultados/analysis_result.json` e a tabela comparativa
   das métricas (a)–(d).

3. **Gerar o relatório do LLM.** Com `LYRA_TEMPERATURA=0.0`. Registrar modelo
   e `PROMPT_VERSION`.

4. **Pré-checagem aritmética.** `validation.fidelity.prechecar_numeros`
   sinaliza números do texto sem correspondência no `AnalysisResult`. É
   triagem, não veredito.

5. **Classificação manual (§4.3e).** Cada afirmação vira `correta`,
   `imprecisa` ou `nao_sustentada`, com justificativa. A planilha preenchida
   é dado bruto do TCC e vai versionada em `<caso>/resultados/`.

6. **Analisar divergências.** Toda métrica fora da tolerância precisa de uma
   explicação escrita no `fonte.md` do caso. Divergência sem explicação é
   resultado incompleto — e a explicação costuma ser mais interessante que a
   concordância.

## Por que a classificação de fidelidade é manual

Seria mais rápido pedir a um LLM que classificasse as afirmações de outro LLM.
Seria também circular: a taxa de alucinação medida passaria a depender da
mesma tecnologia sob avaliação, e a banca teria razão em não aceitar o número.

O §4.3(e) foi escrito como "checagem manual, item a item" de propósito. A
pré-checagem aritmética existe para poupar tempo do avaliador humano — nunca
para substituí-lo, e por isso `prechecar_numeros` não atribui classificação
nenhuma.

## O que invalida uma coleta

Se qualquer um destes mudar, os relatórios já coletados **não podem ser
misturados** com os novos — refaça a coleta dos casos afetados:

- o prompt (`narrative/prompts/relatorio_tecnico.md`)
- o modelo de linguagem ou sua versão
- a temperatura
- a estrutura do `AnalysisResult` (`SCHEMA_VERSION`)

Daí `PROMPT_VERSION` e `SCHEMA_VERSION` serem registrados em toda execução: sem
etiqueta, não há como saber depois qual configuração gerou qual número.

## Registro de mudanças no protocolo

| Data | O que mudou | Casos a reprocessar |
|------|-------------|---------------------|
| 2026-08-23 | Versão inicial. α = 0,05 (ADR 0003). | — |
