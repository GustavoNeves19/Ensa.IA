# LYRA

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

O LYRA ataca as duas: um pipeline estatístico determinístico em Python, de
código aberto, e uma camada de linguagem que traduz o resultado numérico em
texto compreensível.

## A ideia central da arquitetura

```
      dados experimentais (CSV)
                 │
                 ▼
    ┌────────────────────────────┐
    │   NÚCLEO DETERMINÍSTICO    │   sem rede, sem LLM, sem aleatoriedade
    │   lyra/core                │   mesmo dado → mesmo resultado, sempre
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
        ┌────────┴─────────┐
        ▼                  ▼
┌───────────────┐   ┌──────────────┐
│ lyra/narrative│   │lyra/validation│
│  (LLM narra)  │   │ (§4.3 mede)   │
│  não calcula  │   │              │
└───────────────┘   └──────────────┘
```

**O LLM narra, mas não calcula.** Essa é a decisão que sustenta a hipótese do
trabalho — não adianta afirmar equivalência estatística com software pago se o
modelo de linguagem puder alterar um número no caminho. A camada narrativa
recebe um `AnalysisResult` congelado e nada mais.

Isso não é convenção de código: está travado por teste automatizado em
[`tests/test_arquitetura.py`](tests/test_arquitetura.py), que falha o CI se
alguém importar `numpy` dentro de `narrative/` ou `langchain` dentro de
`core/`. Ver [ADR 0001](docs/decisoes/0001-fronteira-deterministica-llm.md).

## Como rodar

Requer Python 3.11+. Usamos [uv](https://docs.astral.sh/uv/) — mais rápido que
pip e resolve o lockfile sozinho.

```bash
# instalar o uv (uma vez só)
curl -LsSf https://astral.sh/uv/install.sh | sh      # Linux/macOS
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows

# clonar e instalar
git clone git@github.com:<org>/lyra.git
cd lyra
uv sync --all-extras

# rodar os testes
uv run pytest

# subir a interface
uv run streamlit run src/lyra/ui/app.py
```

Para usar a camada de LLM, copie `.env.example` para `.env` e preencha a
chave. **O `.env` nunca vai para o repositório.**

O núcleo estatístico funciona sem chave nenhuma e sem internet — isso é
proposital e é testado.

## Estrutura

```
src/lyra/
├── core/          Núcleo determinístico. Offline, reprodutível.
│   ├── design.py       Fatores, codificação [-1,+1], termos do modelo
│   ├── model.py        Matriz de modelo e ajuste OLS
│   ├── anova.py        ANOVA tipo II, seleção de termos, falta de ajuste
│   ├── effects.py      Coeficientes, efeitos, intervalos de confiança
│   ├── desirability.py Otimização de Derringer-Suich
│   └── results.py      ★ AnalysisResult — o contrato da fronteira
├── narrative/     Camada de LLM. Consome AnalysisResult, produz texto.
├── validation/    Métricas do §4.3 do pré-projeto. É o instrumento de medida do TCC.
├── io/            Leitura e validação dos dados de entrada
└── ui/            Interface Streamlit

casos_de_estudo/   Um diretório por caso, com dados + valores publicados
docs/decisoes/     ADRs — por que cada decisão de arquitetura foi tomada
tests/             Unitários, integração, e regressão contra valores publicados
```

## Casos de estudo e validação

O capítulo de resultados do TCC sai daqui. Cada caso de estudo é uma pasta com
os dados experimentais, os valores publicados no artigo original, e a citação
da fonte — ver [`casos_de_estudo/README.md`](casos_de_estudo/README.md).

```bash
uv run lyra-validar                      # roda todos os casos
uv run lyra-validar --caso nome-do-caso  # roda um só
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
