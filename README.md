# EnsaIA

Sistema web gratuito e didático para analisar experimentos químicos planejados
por **delineamento composto central rotacional (DCCR)**, feito em Python.

> **TCC — Universidade Federal Rural da Amazônia (UFRA)**
> Instituto da Saúde e Produção Animal · Curso de Graduação em Sistemas de Informação
>
> *Abordagem acessível para delineamento experimental e análise de dados químicos com modelos preditivos*
>
> Gabriel Henrique Lemos de Athayde · Gustavo Neves da Paz Rafael
> Orientadora: Profa. Dra. Luiza Helena da Silva Martins

---

## O problema

O planejamento de experimentos (DOE), e o DCCR em particular, é uma das
ferramentas mais usadas para otimizar processos químicos. Na prática, a
análise depende de softwares pagos (Statistica, Minitab, Design-Expert,
Protimiza), e ler a saída deles exige uma formação em estatística que muitos
estudantes e profissionais de química não têm.

O EnsaIA faz a análise completa de um DCCR pelo navegador, sem instalar nada e
sem guardar os dados, e explica cada número na própria tela.

## O que o sistema faz

1. **Enviar e conferir.** Recebe CSV, TSV, TXT, XLSX, XLS ou ODS (até 5 MB) e
   mostra uma prévia. Também abre exemplos publicados e oferece uma
   planilha-modelo de DCCR.
2. **Mapear colunas.** Sugere o papel de cada coluna (fator, resposta, bloco ou
   não usar), com arrastar e soltar.
3. **Reconhecer o DCCR.** Codifica os fatores em −α, −1, 0, +1, +α e confere a
   parte fatorial, os pontos axiais, os pontos centrais e o α rotacional. Se não
   for um DCCR, explica o que falta.
4. **Analisar.** Modelo quadrático, coeficientes com Pareto, ANOVA da regressão
   com F calculado / F tabelado, R², R² máximo, falta de ajuste, diagnóstico
   dos resíduos, equação, superfície de resposta, ponto estacionário, melhor
   condição e desejabilidade. Ensaios feitos em blocos (dias, lotes) também são
   aceitos: a diferença entre blocos sai do erro.
5. **Explicar e baixar.** Lâmpadas de dica em cada número, glossário, texto do
   relatório e download em PDF e JSON.

O texto do relatório pode ser escrito de quatro jeitos, escolhidos na tela:

| Modo | Como funciona |
|---|---|
| Sem IA | Texto montado a partir dos resultados; sempre disponível, offline. |
| Copiar para a sua IA | O EnsaIA monta o pedido, você cola no ChatGPT, Gemini etc. e traz a resposta de volta. |
| IA local | Ollama aberto no computador onde o EnsaIA está rodando. |
| IA em nuvem | Gemini, Groq ou OpenAI com a sua chave, ou a IA que o servidor oferecer. |

Com IA, cada número do texto é conferido contra os resultados e o que não bate
fica marcado em amarelo.

## A ideia central da arquitetura

```
      planilha do experimento
                 │
                 ▼
    ┌────────────────────────────┐
    │   NÚCLEO DETERMINÍSTICO    │   sem rede, sem IA, sem aleatoriedade
    │   ensaia/core              │   mesmo dado → mesmo resultado, sempre
    │                            │
    │   DCCR → OLS → ANOVA       │
    │   → superfície → ótimo     │
    └────────────┬───────────────┘
                 │
                 ▼
         ╔═══════════════╗
         ║ AnalysisResult ║   ◄── a fronteira: congelado, serializável em JSON
         ╚═══════╤═══════╝
                 │
     ┌───────────┼───────────┬──────────────┐
     ▼           ▼           ▼              ▼
   ui/        report/       ai/       mcp_server/
  (tela)       (PDF)    (só escreve)  (assistentes)
```

**A IA escreve, mas não calcula.** Toda conta acontece no núcleo; a tela, o PDF,
a IA e o servidor MCP só leem o `AnalysisResult`. Isso é conferido por teste
automático em [`tests/test_arquitetura.py`](tests/test_arquitetura.py) — ver
[ADR 0001](docs/decisoes/0001-fronteira-deterministica-llm.md).

## Como rodar

Requer Python 3.11+ e o [uv](https://docs.astral.sh/uv/).

```bash
# instalar o uv (uma vez só)
curl -LsSf https://astral.sh/uv/install.sh | sh                # Linux/macOS
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"     # Windows

# clonar e instalar (--all-extras traz interface, relatório, IA, MCP e dev)
git clone https://github.com/GustavoNeves19/Ensa.IA.git
cd Ensa.IA
uv sync --all-extras

# rodar os testes
uv run pytest

# subir a interface web → http://127.0.0.1:8080
uv run ensaia-ui
```

Para abrir de outro computador ou celular na mesma rede, suba escutando em
todos os endereços e acesse pelo IP da máquina (ex.: `http://192.168.0.10:8080`):

```bash
uv run uvicorn ensaia.app.main:app --host 0.0.0.0 --port 8080
```

O firewall do Windows pode pedir permissão na primeira vez.

**IA local.** Instale o [Ollama](https://ollama.com), baixe um modelo pequeno
(`ollama pull qwen3:4b`, por exemplo) e deixe-o aberto na mesma máquina do
EnsaIA. O endereço pode ser trocado na tela.

**IA oferecida pelo servidor.** Copie `.env.example` para `.env` e preencha
`ENSAIA_IA_CHAVE` (e, se quiser, `ENSAIA_IA_URL` e `ENSAIA_IA_MODELO`).
**O `.env` nunca vai para o repositório.**

O núcleo estatístico funciona sem chave nenhuma e sem internet.

## Rodar com Docker

```bash
docker compose up --build        # abre em http://localhost:8080
```

- Um único processo (Uvicorn, 1 worker) na porta **8080**, limitado a 512 MB
  de RAM, o mesmo orçamento da hospedagem.
- `GET /health` responde `{"status": "ok"}` quando o servidor está de pé.
- A IA oferecida pelo servidor vem do `.env`, se ele existir; sem ele, os modos
  sem IA, copiar e chave própria continuam disponíveis.

### Publicar no EasyPanel

1. Crie um serviço do tipo **App** apontando para este repositório (branch
   `main`).
2. Em **Build**, escolha **Dockerfile**.
3. Em **Domains**, aponte o domínio para a porta **8080** do contêiner.
4. Em **Environment**, opcionalmente, defina `ENSAIA_IA_CHAVE` (com
   `ENSAIA_IA_URL` e `ENSAIA_IA_MODELO`) para oferecer uma IA pronta.
5. Para assistentes de IA usarem o MCP pela internet, defina `ENSAIA_HOSTS` com
   o domínio público (vários, separados por vírgula).
6. Faça o deploy e confira `https://<seu-domínio>/health`.

Não é preciso volume: o app não grava nada em disco.

## Usar com assistentes de IA (MCP)

O EnsaIA também é um servidor **MCP** (*Model Context Protocol*): assistentes
como Claude, ChatGPT e LM Studio usam as análises como ferramentas, com os
mesmos números da tela.

- **Ferramentas:** `read_table`, `detect_design`, `fit_model`,
  `compute_effects` (Pareto), `check_residuals`, `find_stationary_point`,
  `optimize`, `run_full_analysis` (aceita coluna de bloco), `render_pdf` e
  `verify_text`.
- **Recursos:** `doe://glossario`, `doe://guia-interpretacao`,
  `doe://catalogo` e `doe://exemplos/{nome}`.

**Local (stdio):**

```json
{ "mcpServers": { "ensaia": { "command": "uvx", "args": ["--from", "ensaia[mcp,report]", "ensaia-mcp"] } } }
```

Num clone deste repositório: `uv run --extra mcp --extra report ensaia-mcp`.

**Pela internet (HTTP):** o servidor web atende em `https://<seu-domínio>/api/mcp`
(sem estado, carregado só na primeira chamada). Configure `ENSAIA_HOSTS`.

## Estrutura

```
src/ensaia/
├── core/          Núcleo estatístico determinístico (numpy e scipy, sem pandas)
│   ├── identificacao.py  Codificação dos fatores e reconhecimento do DCCR
│   ├── termos.py         Termos do modelo, confundimento e redução backward
│   ├── model.py          Matriz do modelo e ajuste OLS (com ANOVA Tipo II)
│   ├── anova.py          ANOVA da regressão, erro puro e falta de ajuste
│   ├── blocos.py         Ensaios em blocos (dias, lotes)
│   ├── surface.py        Superfície, previsão e ponto estacionário
│   ├── desirability.py   Melhor condição e desejabilidade (Derringer-Suich)
│   ├── pipeline.py       Fim a fim: dados → AnalysisResult
│   ├── fluxo.py          Caminho comum da tela e do MCP
│   ├── facts.py          Fatos verificados (texto sem IA)
│   └── results.py        ★ AnalysisResult — o contrato da fronteira
├── io/            Leitura de planilhas (→ Table), planilha-modelo e CSV
├── ui/            Interface web em NiceGUI (envio, mapeamento, resultados, texto)
├── report/        Relatório PDF (fpdf2 + matplotlib)
├── ai/            Texto com IA e checagem de fidelidade (HTTP direto, sem LangChain)
├── mcp_server/    Ferramentas para assistentes de IA
├── validation/    Métricas de validação e o comando ensaia-validar
├── conteudo/      Glossário e guia de leitura
├── exemplos/      Exemplos públicos de DCCR
└── app/           Processo único (FastAPI + Uvicorn); comando ensaia-ui

casos_de_estudo/   Um diretório por artigo: dados + valores publicados + fonte
docs/decisoes/     ADRs — por que cada decisão foi tomada
docs/pesquisa/     Material de apoio (resumo do livro de DOE, IHC, candidatos)
tests/             Unitários, arquitetura e regressão contra valores publicados
```

Cada arquivo de `src/ensaia` começa com um resumo de duas linhas, e cada função
tem uma linha dizendo o que faz.

## Validação numérica

A correção dos números é testada contra duas referências:

| Referência | O que é conferido | Onde |
|---|---|---|
| statsmodels (só nos testes) | Coeficientes, erros-padrão, t e p (até 1e-7) e ANOVA Tipo II | `tests/unit/test_oraculo_statsmodels.py` |
| Barros Neto, Scarminio e Bruns (2010), cap. 6 | 5 exemplos de DCCR: coeficientes, ANOVA, R², R² máximo, falta de ajuste, F/F tabelado e ponto ótimo | `tests/unit/test_barros_neto_dccr.py` |

Os artigos de DCCR usados como casos de estudo ficam em
[`casos_de_estudo/`](casos_de_estudo/README.md), cada um com `dados.csv`,
`referencia.yaml` (valores publicados) e `fonte.md` (procedência e ressalvas).
Os critérios do §4.3 do pré-projeto:

| | Métrica | Critério |
|---|---|---|
| (a) | Erro relativo dos coeficientes | ≤ 5% |
| (b) | Concordância de significância | α = 0,05 |
| (c) | Diferença de R² e R² ajustado | ≤ 0,01 |
| (d) | Diferença na condição ótima | absoluta e % da faixa |

```bash
uv run ensaia-validar                      # roda os casos prontos
uv run ensaia-validar --caso nome-do-caso  # roda um só
```

O comando só roda casos que já passaram pela dupla conferência humana. Hoje
todos estão em rascunho, então ele não roda nenhum. Ver
[`docs/protocolo-validacao.md`](docs/protocolo-validacao.md).

## Idioma

Identificadores, docstrings, documentação e mensagens de commit em
**português**: a banca e a orientadora leem este código. Termos estatísticos
consagrados ficam como são (`OLS`, `ANOVA`, `R²`, `p-valor`).

## Estado atual

- **Escopo:** só DCCR ([ADR 0013](docs/decisoes/0013-restricao-a-dccr.md) e
  [ADR 0015](docs/decisoes/0015-sistema-so-dccr-de-ponta-a-ponta.md)). As
  análises de fatoriais de triagem continuam no núcleo, mas não aparecem na
  tela nem no PDF; outros planejamentos são trabalho futuro.
- **Pronto:** leitura, mapeamento, reconhecimento do DCCR, modelo, ANOVA,
  diagnóstico, superfície, otimização, blocos, texto (sem IA e com IA), PDF,
  JSON e servidor MCP.
- **IA e MCP:** continuam no sistema, mas estão fora do escopo do TCC
  (especificação v0.6).
- **Pendente:** escolha dos artigos de referência do TCC; dupla conferência
  humana dos casos de estudo; catálogo de indicadores com fonte de cada
  limiar; modos Iniciante e Avançado; teste com usuários.

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para o fluxo de trabalho.

## Licença

MIT — ver [LICENSE](LICENSE).
