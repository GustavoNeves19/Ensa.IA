# Como trabalhar neste repositório

Combinados da dupla. Nada aqui é burocracia por burocracia — cada regra existe
porque quebrá-la custa caro num TCC com prazo.

## Preparando o ambiente

```bash
uv sync --all-extras
uv run pre-commit install    # roda o lint antes de cada commit
cp .env.example .env         # e preencha a chave da API
uv run pytest                # confirma que está tudo de pé
```

## Branches

```
main       sempre funcionando. Nunca commitar direto.
develop    integração do trabalho em andamento.
feat/xxx   uma feature, um branch.
fix/xxx    correção.
```

Trabalho novo sai de `develop`, volta por Pull Request. `main` recebe de
`develop` quando há algo estável — em geral no fim de cada etapa do
cronograma.

Por que não commitar direto na `main`: quando a monografia citar um número, é
preciso poder apontar um commit da `main` que o produz. Se a `main` for
histórico de trabalho em andamento, essa rastreabilidade some.

## Commits

Formato: `tipo: descrição no imperativo, em português`

```
feat: implementar matriz de modelo para k fatores
fix: corrigir notação de termo quadrático em extrair_coeficientes
test: cobrir caso de referência com coeficiente zero
docs: registrar ADR 0005 sobre pseudocomponentes
refactor: extrair codificação de fator para design.Fator
```

Nada de "ajustes", "wip", "commit". Daqui a dois meses um desses no `git log`
custa meia hora de arqueologia.

## Pull Requests

Preencha o template. Peça revisão do outro — sempre, inclusive em PR pequeno.
Revisão em dupla não é formalidade: neste projeto, o revisor é a única
verificação humana entre um erro de sinal num coeficiente e a monografia
impressa.

O PR só entra com o CI verde.

## Divisão de trabalho

Combinar por **issue**, não por arquivo. Duas pessoas mexendo em `core/` ao
mesmo tempo é normal; duas pessoas mexendo em `core/model.py` ao mesmo tempo é
conflito garantido.

Abriu para trabalhar? Assine a issue (assign) antes de começar.

## Três regras que não são negociáveis

### 1. Não afrouxe a fronteira núcleo/LLM

Se `tests/test_arquitetura.py` falhar, o conserto é no código — nunca no
teste. A hipótese inteira do TCC depende dessa separação. Ver
[ADR 0001](docs/decisoes/0001-fronteira-deterministica-llm.md).

### 2. Mexeu num limiar do §4.3, mexeu no documento

Os valores de 5%, α = 0,05 e 0,01 estão no pré-projeto **assinado**. Mudar no
código sem mudar o documento cria divergência entre o que o TCC promete e o
que o sistema faz — e é o tipo de coisa que a banca encontra.

Mudança de limiar passa por: conversar com a orientadora → corrigir o
documento → mudar o código → registrar em ADR.

### 3. Nunca commite `.env`

O `.gitignore` cobre, e o `pre-commit` tem `detect-private-key`. Ainda assim,
confira antes de `git add .`. Chave vazada em repositório, mesmo privado, é
chave a revogar.

## Adicionando um caso de estudo

Ver [`casos_de_estudo/README.md`](casos_de_estudo/README.md). Resumo: quem
transcreve não é quem confere.

## Quando a decisão for de arquitetura

Abra um ADR em `docs/decisoes/`. Numere na sequência, siga o formato dos
existentes (contexto → decisão → consequências, incluindo as ruins).

O critério prático: se a decisão for difícil de reverter depois, ou se alguém
vier a perguntar "por que assim?" na defesa, ela merece um ADR.
