# EnsaIA

Análise e otimização de experimentos químicos (DOE) em Python, com uma camada
de interpretação por modelo de linguagem.

> **TCC — Universidade Federal Rural da Amazônia (UFRA)**
> Instituto da Saúde e Produção Animal · Curso de Graduação em Sistemas de Informação
>
> *Abordagem acessível para delineamento experimental e análise de dados químicos com modelos preditivos*
>
> Gabriel Henrique Lemos de Athayde · Gustavo Neves da Paz Rafael
> Orientadora: Profa. Dra. Luiza Helena da Silva Martins

---

## O problema

O Planejamento de Experimentos (DOE) é uma das ferramentas mais eficazes para
otimizar processos químicos, mas seu uso esbarra em duas barreiras: os
softwares consolidados (Statistica, MiniTab) têm custo de licenciamento alto,
e interpretar a saída deles exige formação em estatística que boa parte dos
profissionais e estudantes de química não tem.

O EnsaIA ataca as duas: um pipeline estatístico determinístico em Python, de
código aberto, e uma camada de linguagem que traduz o resultado numérico em
texto compreensível.

## A ideia central da arquitetura

```
      dados experimentais (CSV)
                 │
                 ▼
    ┌────────────────────────────┐
    │   NÚCLEO DETERMINÍSTICO    │   sem rede, sem LLM, sem aleatoriedade
    │   ensaia/core              │   mesmo dado → mesmo resultado, sempre
    │                            │
    │   OLS → ANOVA → efeitos    │
    │       → desejabilidade     │
    └────────────┬───────────────┘
                 │
                 ▼
         ╔═══════════════╗
         ║ AnalysisResult ║   ◄── a fronteira. frozen, serializável em JSON
         ╚═══════╤═══════╝
                 │
         ┌───────┴───────────────┐
         ▼                       ▼
┌──────────────────┐   ┌───────────────────┐
│    ensaia/ai     │   │ ensaia/validation │
│   (LLM narra)    │   │   (§4.3 mede)     │
│   não calcula    │   │                   │
└──────────────────┘   └───────────────────┘
```

**O LLM narra, mas não calcula.** Essa é a decisão que sustenta a hipótese do
trabalho — não adianta afirmar equivalência estatística com software pago se o
modelo de linguagem puder alterar um número no caminho. A camada narrativa
recebe um `AnalysisResult` congelado e nada mais.

Isso não é convenção de código: está travado por teste automatizado em
[`tests/test_arquitetura.py`](tests/test_arquitetura.py), que falha o CI se
alguém importar `numpy` dentro de `ai/` ou `langchain` dentro de
`core/`. Ver [ADR 0001](docs/decisoes/0001-fronteira-deterministica-llm.md).

## Como rodar

Requer Python 3.11+. Usamos [uv](https://docs.astral.sh/uv/) — mais rápido que
pip e resolve o lockfile sozinho.

```bash
# instalar o uv (uma vez só)
curl -LsSf https://astral.sh/uv/install.sh | sh      # Linux/macOS
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows

# clonar e instalar (--all-extras traz interface, relatório, LLM e dev)
git clone git@github.com:<org>/ensaia.git
cd ensaia
uv sync --all-extras

# rodar os testes
uv run pytest

# subir a interface web → abre em http://127.0.0.1:8080
uv run ensaia-ui
```

A interface é **NiceGUI sobre FastAPI**, servida por um único processo Uvicorn
(spec seção 7.2; ver [ADR 0011](docs/decisoes/0011-interface-nicegui-processo-unico.md)).
O entrypoint é `ensaia.app.main:main`, exposto como o script `ensaia-ui`.

Ela depende do extra **`ui`**: o `uv sync --all-extras` acima já o instala. Se
tiver sincronizado só o núcleo, `uv run ensaia-ui` falha com
`ModuleNotFoundError: No module named 'fastapi'` — rode `uv sync --extra ui`
(ou `--all-extras`) antes. Para parar o servidor, `Ctrl+C` no terminal.

O texto do relatório pode ser escrito de quatro jeitos, escolhidos na tela:
sem IA (sempre disponível), copiando o pedido para qualquer IA e colando a
resposta de volta, com o Ollama local (só quando o EnsaIA roda no seu
computador) ou com uma IA em nuvem usando a chave do próprio usuário (Gemini,
Groq, OpenAI). Em todos os casos com IA, cada número do texto é conferido contra
os resultados e o que não bate fica marcado em amarelo.

Quem hospeda pode oferecer uma IA pronta, sem o usuário precisar de chave:
copie `.env.example` para `.env` e preencha `ENSAIA_IA_CHAVE`. **O `.env` nunca
vai para o repositório.**

O núcleo estatístico funciona sem chave nenhuma e sem internet — isso é
proposital e é testado.

## Rodar com Docker

A imagem traz o que o app usa em produção (interface, relatório PDF e camada de
IA) e sobe **um único processo**: o Uvicorn com 1 worker, na porta **8080**.

```bash
docker compose up --build        # abre em http://localhost:8080
```

- `GET /health` responde `{"status": "ok"}` quando o servidor está de pé. É a
  sonda que o `HEALTHCHECK` da imagem e o painel de hospedagem usam para saber
  se o app já pode receber acessos.
- A IA oferecida pelo servidor lê `ENSAIA_IA_CHAVE` (ou `OPENAI_API_KEY`). No
  `docker compose` ela vem do `.env`, se ele existir; sem a chave, o app
  funciona normalmente: o texto sem IA, o "copiar para a sua IA" e a chave do
  próprio usuário continuam disponíveis.
- O `docker-compose.yml` limita o contêiner a 512 MB de RAM, o mesmo orçamento
  da hospedagem (spec §16), e traz comentado um serviço `ollama` para IA local.

### Publicar no EasyPanel

O EasyPanel é um painel para VPS que constrói e roda contêineres Docker. Como o
app é um processo só, basta um serviço:

1. Crie um serviço do tipo **App** apontando para este repositório (branch
   `main`).
2. Em **Build**, escolha **Dockerfile** (o arquivo `Dockerfile` da raiz).
3. Em **Domains**, aponte o domínio para a porta **8080** do contêiner. Se o
   painel definir a variável `PORT`, o app escuta nela.
4. Em **Environment**, opcionalmente, defina `ENSAIA_IA_CHAVE` para oferecer
   uma IA pronta aos usuários (com `ENSAIA_IA_URL` e `ENSAIA_IA_MODELO`; o
   padrão é a OpenAI com `gpt-4o-mini`). Sem ela, cada usuário usa a própria
   chave ou copia o pedido para a IA que preferir.
5. Faça o deploy e confira `https://<seu-domínio>/health`.

Não é preciso volume: o app não grava nada em disco; a planilha enviada fica só
na memória da sessão.

## Estrutura

```
src/ensaia/
├── core/          Núcleo determinístico. Offline, reprodutível.
│   ├── design.py       Fatores, codificação [-1,+1], termos do modelo
│   ├── model.py        Matriz de modelo e ajuste OLS
│   ├── anova.py        ANOVA tipo II, seleção de termos, falta de ajuste
│   ├── effects.py      Coeficientes, efeitos, intervalos de confiança
│   ├── desirability.py Otimização de Derringer-Suich
│   ├── table.py        Tabela de dados leve, em numpy, sem pandas (ADR 0008)
│   ├── facts.py        Fatos interpretativos verificados a partir do ajuste
│   ├── numeros.py      Extração/rastreio de números em português (utilidade)
│   └── results.py      ★ AnalysisResult — o contrato da fronteira
├── ai/            Camada de LLM (HTTP direto, sem LangChain — ADR 0006). Consome AnalysisResult, produz texto.
├── validation/    Métricas do §4.3 do pré-projeto. É o instrumento de medida do TCC.
├── report/        Relatório PDF (fpdf2 + matplotlib) a partir do resultado + texto (ADR 0010).
├── io/            Leitura (CSV/XLSX → Table) e validação dos dados de entrada
├── ui/            Interface web em NiceGUI: home, tema, upload
└── app/           Processo único ASGI (FastAPI + Uvicorn). Entrypoint `ensaia-ui` (ADR 0011).

casos_de_estudo/   Um diretório por caso, com dados + valores publicados
docs/decisoes/     ADRs — por que cada decisão de arquitetura foi tomada
tests/             Unitários, integração, e regressão contra valores publicados
```

## Casos de estudo e validação

O capítulo de resultados do TCC sai daqui. Cada caso de estudo é uma pasta com
os dados experimentais, os valores publicados no artigo original, e a citação
da fonte — ver [`casos_de_estudo/README.md`](casos_de_estudo/README.md).

```bash
uv run ensaia-validar                      # roda todos os casos
uv run ensaia-validar --caso nome-do-caso  # roda um só
```

As métricas são as cinco fixadas no §4.3 do pré-projeto assinado:

| | Métrica | Critério |
|---|---|---|
| (a) | Erro relativo dos coeficientes | ≤ 5% |
| (b) | Concordância de significância | α = 0,05 |
| (c) | Diferença de R² e R² ajustado | ≤ 0,01 |
| (d) | Diferença na condição ótima | absoluta e % da faixa |
| (e) | Fidelidade do relatório do LLM | classificação manual, item a item |

Os limiares vêm do documento entregue à orientadora. Mudar um número aqui
significa mudar o documento também — ver
[`docs/protocolo-validacao.md`](docs/protocolo-validacao.md).

## Idioma

Identificadores, docstrings, documentação e mensagens de commit em
**português**. A banca e a orientadora leem este código, e ela é do domínio de
química, não de software — clareza para quem avalia vale mais que aderência à
convenção anglófona.

Exceção: termos estatísticos consagrados ficam como são (`OLS`, `ANOVA`, `R²`,
`p-valor`), e nomes vindos de bibliotecas externas não são traduzidos.

## Estado atual

Fase de implementação do pipeline (cronograma: ago–set/2026). O contrato
`AnalysisResult`, as métricas de validação e os testes de arquitetura estão
prontos; o núcleo estatístico está com as assinaturas definidas e as
implementações marcadas com `TODO(#n)` apontando para as issues.

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para o fluxo de trabalho.

## Licença

MIT — ver [LICENSE](LICENSE).
