# Casos de estudo

Cada subdiretório é um caso de estudo tirado da literatura, com os dados
experimentais e os resultados publicados que servem de *ground truth*.

O §4.2 do pré-projeto define os critérios de seleção:

1. **Disponibilidade pública** dos dados experimentais (fatores, níveis,
   respostas) *e* dos resultados estatísticos originais, permitindo comparação
   direta.
2. **Cobertura de diferentes tipos de planejamento** — fatorial completo 2^k,
   composto central, Box-Behnken — para testar complexidade crescente.
3. **Origem** em monografias, artigos ou publicações técnicas de química ou
   engenharia química.

Meta: de três a cinco casos.

## Estrutura de um caso

```
<nome-do-caso>/
├── dados.csv        Um ensaio por linha
├── referencia.yaml  O que o artigo publicou
├── fonte.md         Citação ABNT, DOI, e de onde saiu cada número
└── resultados/      Gerado pelo EnsaIA (versionado — é evidência do TCC)
```

Use `_template/` como ponto de partida:

```bash
cp -r casos_de_estudo/_template casos_de_estudo/meu-caso
```

## Ao transcrever os valores de referência

Esta é a parte mais chata e a mais perigosa do trabalho. Um dígito errado no
`referencia.yaml` não gera erro nenhum — gera um resultado de validação
plausível e falso, que pode ir parar na monografia.

Por isso:

- **Confiram a transcrição em dupla.** Um transcreve, o outro confere contra
  o PDF. Registrem no `fonte.md` quem fez cada parte.
- **Anotem a tabela/página** de onde cada bloco de valores veio.
- **Não convertam nada de cabeça.** Se o artigo publica coeficientes em
  unidades reais e o EnsaIA trabalha em codificadas, registrem o valor como
  publicado e anotem em `observacoes` — a conversão é responsabilidade do
  runner, e precisa estar visível.
- **Não preencham o que não está no artigo.** Campo ausente fica `null`. As
  métricas do §4.3 lidam com referência ausente; o que elas não têm como
  detectar é um valor inventado.
- **Cuidado com efeito × coeficiente.** Parte da literatura publica o *efeito*
  (variação do nível −1 ao +1), parte publica o *coeficiente* (do centro ao
  +1). Diferem por um fator de 2. Confundir os dois gera erro relativo de 100%
  em toda a tabela — anotem qual dos dois o artigo reporta.

## Rodando a validação

```bash
uv run ensaia-validar                  # todos os casos
uv run ensaia-validar --caso meu-caso  # um só
```
