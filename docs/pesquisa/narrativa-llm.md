# Guia de implementação — issue #7 (`narrative/chain`)

## 0. O que já existe no repositório (não é do zero)

Antes de desenhar qualquer coisa, vale registrar o que já está pronto, porque muda o escopo real da issue #7:

| Arquivo | Estado |
|---|---|
| `src/lyra/core/results.py` | ✅ Pronto — `AnalysisResult` é o contrato, `frozen`, com `to_json()`. |
| `src/lyra/narrative/schema.py` | ✅ Pronto — `NarrativeReport` (`secoes`, `modelo_usado`, `prompt_version`, `avisos`). |
| `src/lyra/narrative/prompts/relatorio_tecnico.md` | ✅ Escrito, com regras invioláveis e placeholder `{analysis_result_json}`. |
| `src/lyra/narrative/chain.py` | 🔴 Esqueleto — assinatura e docstring prontas, `raise NotImplementedError`. **É isto que a #7 fecha.** |
| `src/lyra/validation/fidelity.py` | ✅ Pronto e testado (`prechecar_numeros`, `segmentar_afirmacoes`, `exportar_planilha_classificacao`). **Não é escopo da #7** — mas falta uma peça de fiação para fechar o ciclo (ver §5). |
| `tests/test_arquitetura.py` | ✅ Pronto — já bloqueia `numpy/pandas/statsmodels/scipy/sklearn` em `narrative/`. Vai continuar passando depois da #7, contanto que o código respeite a fronteira abaixo. |

Ou seja: a #7 é escrever `gerar_relatorio()` em `chain.py`. `fidelity.py` já faz sua parte — o trabalho aqui é garantir que a saída de `chain.py` se encaixa bem nela.

---

## 1. A fronteira do ADR 0001, aplicada a este arquivo especificamente

`tests/test_arquitetura.py` define `PROIBIDOS_EM_NARRATIVE = {numpy, pandas, statsmodels, scipy, sklearn}`. Isso **permite** `langchain`, `langchain_core`, `langchain_google_genai` e `pydantic` em `narrative/` — não há conflito em importá-los.

Duas coisas importantes que esse teste **não** cobre, e que ficam por sua conta na revisão de código:

1. **O teste só lê os imports literais dos arquivos de `narrative/`, não a árvore de dependências transitivas.** Ele garante que *o código do LYRA* não calcula — não garante nada sobre o que acontece dentro do `langchain_google_genai` ou da API do Gemini. Isso é intencional e suficiente: a hipótese do TCC é sobre o LYRA não delegar cálculo ao LLM, não sobre "nenhum float existir em nenhuma dependência".

2. **Habilitar uma ferramenta de cálculo no próprio modelo (function calling / code execution do Gemini) não dispara nenhum import proibido**, porque isso é configuração do objeto `ChatGoogleGenerativeAI`, não um `import numpy`. O ADR 0001 já descartou explicitamente essa alternativa ("Dar ao LLM acesso a uma ferramenta de cálculo... reintroduz variabilidade... é o oposto do que o trabalho precisa provar"). **Regra de implementação, não coberta por CI:** em `chain.py`, o `ChatGoogleGenerativeAI` nunca recebe `bind_tools(...)`, nunca é envolvido em `create_agent`, e a API do Gemini não deve receber `code_execution` nem `google_search_retrieval` habilitados. Vale a pena deixar isso registrado como comentário no próprio código, porque é o único ponto onde a garantia depende de disciplina humana e não de teste automático.

---

## 2. Desenho da chain

### 2.1 Dependências — ajuste recomendado no `pyproject.toml`

Hoje:
```toml
llm = [
    "langchain>=0.3",
    "langchain-core>=0.3",
    "langchain-google-genai>=2.0",
]
```

`langchain-google-genai>=2.0` é um piso solto demais. Há dois bugs históricos documentados e já corrigidos no pacote — `temperature=0` sendo descartado por ser "falsy" em Python (issue #49 → PR #51) e validação client-side limitando `temperature` a `[0,1]` em vez de `[0,2]` (issue #781 → PR #780). Um `>=2.0` deixa o resolvedor livre para trazer uma versão anterior à correção. Recomendo apertar o piso:

```toml
llm = [
    "langchain-core>=1.6",
    "langchain-google-genai>=4.3",
]
```

(`langchain` genérico pode sair — só se usa `langchain-core` e `langchain-google-genai` aqui; menos superfície de dependência.)

### 2.2 Serializar o `AnalysisResult`

`resultado.to_json()` já existe e é determinístico o suficiente: `asdict()` preserva a ordem de declaração dos campos do dataclass (não depende de hash de dict), e `json.dumps` usa a representação `repr`-based do Python para float, que é estável e faz round-trip exato. Não é preciso adicionar `sort_keys=True` para ganhar determinismo — já existe. Use `resultado.to_json()` como está.

### 2.3 Corrigir um problema real no prompt antes de usá-lo

`prompts/relatorio_tecnico.md` abre com um comentário HTML:

```markdown
<!--
Prompt de geração do relatório técnico do LYRA.
Versão: 2026.08.1  (manter sincronizado com PROMPT_VERSION em chain.py)

Ao editar este arquivo, incremente a versão em chain.py E registre a mudança
em docs/protocolo-validacao.md. ...
-->
```

Se `chain.py` ler o arquivo inteiro e usar como texto do prompt, **esse comentário vai para o Gemini como se fosse contexto** — LLMs não têm noção especial de comentário HTML, é só texto que o modelo lê. O modelo receberia instruções de engenharia de repositório ("incremente a versão em chain.py") junto com a tarefa de narrar estatística, o que é ruído e desperdício de tokens na melhor hipótese.

Solução simples — remover o comentário antes de montar o template:

```python
import re
from pathlib import Path

_PROMPT_PATH = Path(__file__).parent / "prompts" / "relatorio_tecnico.md"


def _carregar_prompt_sistema() -> str:
    bruto = _PROMPT_PATH.read_text(encoding="utf-8")
    return re.sub(r"^<!--.*?-->\s*", "", bruto, count=1, flags=re.DOTALL)
```

### 2.4 Saída estruturada — schema por seção, não texto livre

O prompt já pede "exatamente estas seções, nesta ordem": Visão geral, Qualidade do modelo, Fatores que importam, Condição recomendada, Ressalvas. `NarrativeReport.secoes` já modela isso como lista de `SecaoRelatorio(titulo, texto)`. O jeito certo de fechar esse contrato é `with_structured_output` com um schema Pydantic de 5 campos, um por seção — não pedir texto livre e recortar por regex depois.

Isso não é só estética: é o que dá ao §4.3(e) uma âncora clara ("essa afirmação veio da seção Qualidade do modelo") em vez de o avaliador ter que adivinhar de onde veio cada frase num bloco de texto corrido.

```python
from pydantic import BaseModel, Field


class _RelatorioEstruturado(BaseModel):
    visao_geral: str = Field(description="Experimento, ensaios, fatores e respostas.")
    qualidade_do_modelo: str = Field(description="R², R² ajustado, falta de ajuste.")
    fatores_que_importam: str = Field(description="Termos significativos e efeito prático.")
    condicao_recomendada: str = Field(description="Ponto ótimo e resposta prevista, se houver.")
    ressalvas: str = Field(description="Limitações e o que os resultados não permitem concluir.")


_TITULOS: dict[str, str] = {
    "visao_geral": "Visão geral",
    "qualidade_do_modelo": "Qualidade do modelo",
    "fatores_que_importam": "Fatores que importam",
    "condicao_recomendada": "Condição recomendada",
    "ressalvas": "Ressalvas",
}
```

Confirmei na documentação do `langchain-google-genai` (via Context7) que `with_structured_output(Schema, method="json_schema")` retorna a instância Pydantic já validada (não um dict cru), e que parâmetros como `thinking_level` sobrevivem à composição com `with_structured_output` — então não há surpresa de config sendo descartada silenciosamente nesse caminho.

### 2.5 Instanciar o modelo — `temperature` nunca omitido, nunca implícito

A mesma documentação confirma que o **default** de `temperature` em `ChatGoogleGenerativeAI` é `0.7`, não `0`. Isso reforça o que já está no docstring atual de `chain.py`: `temperatura=0.0` tem que ser passado explicitamente, sempre, como `float`.

Ponto de atenção específico da pesquisa: desde jul/2026 a linha Gemini 3.x Flash (`gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`) **ignora silenciosamente** `temperature`/`top_p`/`top_k` (retorna 200 OK, sem erro). O `.env.example` do projeto aponta `LYRA_MODELO_LLM=gemini-2.5-flash`, que **não** está nessa lista — hoje `temperature=0.0` é respeitado. Mas se algum dia trocarem o modelo padrão para a linha 3.x Flash sem revisitar isso, a suposição de reprodutibilidade quebra sem aviso nenhum no código. Vale blindar isso registrando o aviso no próprio `NarrativeReport`, já que o campo `avisos` existe exatamente para isso:

```python
import os

_MODELO_PADRAO = "gemini-2.5-flash"
_MODELOS_SEM_TEMPERATURA = {"gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"}
```

### 2.6 A chain completa

```python
from __future__ import annotations

import os
import re
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from lyra.core.results import AnalysisResult
from lyra.narrative.schema import NarrativeReport, SecaoRelatorio

PROMPT_VERSION = "2026.08.1"

_PROMPT_PATH = Path(__file__).parent / "prompts" / "relatorio_tecnico.md"
_MODELO_PADRAO = "gemini-2.5-flash"
_MODELOS_SEM_TEMPERATURA = {"gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"}


def _carregar_prompt_sistema() -> str:
    bruto = _PROMPT_PATH.read_text(encoding="utf-8")
    return re.sub(r"^<!--.*?-->\s*", "", bruto, count=1, flags=re.DOTALL)


class _RelatorioEstruturado(BaseModel):
    visao_geral: str = Field(description="Experimento, ensaios, fatores e respostas.")
    qualidade_do_modelo: str = Field(description="R², R² ajustado, falta de ajuste.")
    fatores_que_importam: str = Field(description="Termos significativos e efeito prático.")
    condicao_recomendada: str = Field(description="Ponto ótimo e resposta prevista, se houver.")
    ressalvas: str = Field(description="Limitações e o que os resultados não permitem concluir.")


_TITULOS: dict[str, str] = {
    "visao_geral": "Visão geral",
    "qualidade_do_modelo": "Qualidade do modelo",
    "fatores_que_importam": "Fatores que importam",
    "condicao_recomendada": "Condição recomendada",
    "ressalvas": "Ressalvas",
}


def gerar_relatorio(
    resultado: AnalysisResult,
    *,
    modelo: str | None = None,
    temperatura: float = 0.0,
) -> NarrativeReport:
    """Ver docstring já existente no arquivo — mantida como está."""
    modelo_resolvido = modelo or os.environ.get("LYRA_MODELO_LLM", _MODELO_PADRAO)

    avisos: list[str] = []
    if modelo_resolvido in _MODELOS_SEM_TEMPERATURA:
        avisos.append(
            f"Modelo {modelo_resolvido} ignora 'temperature' desde jul/2026 "
            "(depreciação de sampling parameters na linha Gemini 3.x Flash). "
            "A reprodutibilidade desta execução não pode ser atribuída a "
            "temperatura=0 — ver docs/decisoes/0001."
        )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _carregar_prompt_sistema()),
            ("human", "Gere o relatório técnico com base nos dados acima."),
        ]
    )

    llm = ChatGoogleGenerativeAI(model=modelo_resolvido, temperature=temperatura)
    cadeia = prompt | llm.with_structured_output(_RelatorioEstruturado, method="json_schema")

    saida: _RelatorioEstruturado = cadeia.invoke(
        {"analysis_result_json": resultado.to_json()}
    )

    secoes = [
        SecaoRelatorio(titulo=_TITULOS[campo], texto=getattr(saida, campo))
        for campo in _TITULOS
    ]

    return NarrativeReport(
        secoes=secoes,
        modelo_usado=modelo_resolvido,
        prompt_version=PROMPT_VERSION,
        avisos=avisos,
    )
```

Note que `ChatGoogleGenerativeAI` lê `GOOGLE_API_KEY` do ambiente automaticamente (é assim que `.env.example` já pressupõe) — não precisa passar a chave explicitamente aqui.

### 2.7 O que nunca deve entrar neste arquivo

- `bind_tools(...)` no `llm`.
- `create_agent(...)` envolvendo este modelo.
- Qualquer parâmetro de `code_execution` ou `google_search_retrieval` na config do Gemini.
- Qualquer lógica que "arredonde", "formate" ou "derive" um número a partir do JSON antes de repassar ao prompt — isso é trabalho do `core`, não de `narrative` (mesmo que pareça inofensivo, tipo formatar `0.947` como `"94,7%"`).

---

## 3. `PROMPT_VERSION` — política e um teste de sincronismo

O protocolo já documenta a regra (`docs/protocolo-validacao.md`): mudou o texto do prompt → incrementa `PROMPT_VERSION` → registra na tabela "Registro de mudanças no protocolo" → relatórios já coletados com a versão antiga não podem ser misturados com os novos.

O ponto frágil é que hoje isso depende de alguém lembrar de manter dois números sincronizados manualmente: o comentário no topo do `.md` e a constante em `chain.py`. Vale um teste barato que trava isso:

```python
# tests/unit/test_narrative_versao.py
import re
from pathlib import Path

from lyra.narrative.chain import PROMPT_VERSION

_PROMPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "src" / "lyra" / "narrative" / "prompts" / "relatorio_tecnico.md"
)


def test_prompt_version_sincronizada_com_o_arquivo() -> None:
    cabecalho = _PROMPT_PATH.read_text(encoding="utf-8")
    m = re.search(r"Versão:\s*(\S+)", cabecalho)
    assert m, "Cabeçalho do prompt não tem linha 'Versão: ...'"
    assert m.group(1) == PROMPT_VERSION, (
        "PROMPT_VERSION em chain.py e a versão no cabeçalho do .md "
        "divergiram. Se o texto do prompt mudou, siga o procedimento em "
        "docs/protocolo-validacao.md antes de seguir."
    )
```

Não precisa de LangSmith Prompt Hub nem infraestrutura externa para isso — a pesquisa confirma que versionamento por constante + arquivo versionado no git é prática aceita, e o projeto já não depende de infraestrutura externa em `core`.

---

## 4. Testes da issue #7

Dois níveis, e o `pyproject.toml` já tem o marcador certo (`llm: testes que chamam a API de um modelo de linguagem`):

**a) Testes de fiação, sem rede (rodam sempre, no CI normal).** Trocar `ChatGoogleGenerativeAI` por um dublê determinístico do LangChain (`langchain_core.language_models.fake_chat_models.FakeMessagesListChatModel` ou um `Runnable` escrito à mão que devolve um `_RelatorioEstruturado` fixo) para verificar: o prompt monta com o comentário HTML removido; `PROMPT_VERSION` chega no `NarrativeReport`; as 5 seções mapeiam para os títulos certos; o aviso de modelo-sem-temperatura aparece quando `modelo` é um dos três da lista.

**b) Testes reais, marcados `@pytest.mark.llm`.** Gastam dinheiro e precisam de `GOOGLE_API_KEY` — pular quando a chave não está no ambiente. Vale incluir aqui exatamente o teste que a pesquisa recomenda como evidência empírica de reprodutibilidade (2–3 chamadas idênticas com `temperature=0.0` sobre o mesmo `AnalysisResult`, comparando as saídas) — isso vira citável na seção de validação do TCC como evidência, não como formalidade assumida.

```python
@pytest.mark.llm
def test_mesma_entrada_produz_relatorio_estavel(resultado_fixo: AnalysisResult) -> None:
    if not os.environ.get("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY não configurada")
    r1 = gerar_relatorio(resultado_fixo, temperatura=0.0)
    r2 = gerar_relatorio(resultado_fixo, temperatura=0.0)
    # comparar texto ou pelo menos os números citados em cada seção
```

---

## 5. Operacionalizando o §4.3(e) em `validation/fidelity.py`

### 5.1 O que já está pronto — e o que isso já garante

`fidelity.py` está implementado e testado (`tests/unit/test_fidelity.py` passa). O fluxo que ele já cobre:

```
NarrativeReport (texto)
      │
      ▼
segmentar_afirmacoes()      ── quebra em sentenças
      │
      ▼
prechecar_numeros()         ── só aritmética: cada número citado tem
      │                        correspondência no AnalysisResult?
      ▼
RelatorioFidelidade          ── toda afirmação nasce com
  (classificacao="pendente")    classificacao = "pendente"
```

`test_nada_sai_classificado_automaticamente` já prova isso em código: depois de `prechecar_numeros`, `all(a.classificacao == "pendente" for a in rel.afirmacoes)`. **Não há caminho no código atual em que `prechecar_numeros` atribua `correta`/`imprecisa`/`nao_sustentada`** — só marca, por afirmação, quais números bateram (`numeros_encontrados_no_resultado`) e quais não (`numeros_sem_correspondencia`). Um número sem correspondência é candidato a alucinação, não veredito: o próprio docstring do módulo lista falsos positivos esperados (arredondamento, diferença derivada — "12 unidades a mais").

**Importante para não confundir dois números parecidos:** a tolerância de `prechecar_numeros` (`tolerancia_relativa=0.01`, ou seja 1%) não é a mesma coisa que a tolerância de 5% do §4.3(a) em `validation/metrics.erro_relativo_coeficientes`. São comparações diferentes:

| | Compara | Tolerância |
|---|---|---|
| `metrics.erro_relativo_coeficientes` (§4.3a) | coeficiente do LYRA × valor publicado no artigo de referência | 5% |
| `fidelity.prechecar_numeros` | número citado no texto do LLM × número que o próprio `AnalysisResult` contém | 1% |

O segundo mede se o LLM **transcreveu** corretamente o que o pipeline já calculou — não se o pipeline acertou contra a literatura.

### 5.2 O fluxo completo, do relatório gerado até o número final do TCC

```
1. gerar_relatorio(resultado)              → NarrativeReport            [issue #7]
2. prechecar_numeros_por_secao(...)        → RelatorioFidelidade        [já existe / extensão §5.4]
3. exportar_planilha_classificacao(...)    → list[dict] (CSV em memória)[já existe]
4. salvar CSV em <caso>/resultados/        → arquivo em disco           [FALTA — ver abaixo]
5. avaliador humano preenche classificacao + justificativa, offline     [manual, sempre]
6. ler CSV preenchido de volta             → RelatorioFidelidade final  [FALTA — ver abaixo]
7. relatorio_fidelidade.fidelidade_global  → número que entra no TCC
```

Os passos 1–3 e 7 já têm código. **Os passos 4 e 6 (salvar em disco e reler o CSV já preenchido pelo humano) ainda não existem em `fidelity.py`.** Sem eles, `exportar_planilha_classificacao` produz uma lista de dicts em memória que ninguém grava, e não há como recarregar uma planilha preenchida para recalcular `fidelidade_global` depois. Isso é o elo que falta para o §4.3(e) fechar de ponta a ponta — vale resolver junto com a #7 (é pequeno) ou deixar explicitamente registrado como pré-requisito da #8 (`validation/runner`, que é quem de fato vai gravar `<caso>/resultados/`).

Sugestão de duas funções pequenas, seguindo o mesmo estilo do módulo:

```python
import csv
from pathlib import Path


def salvar_planilha_classificacao(linhas: list[dict[str, object]], caminho: Path) -> None:
    """Grava o CSV que o avaliador humano vai preencher.

    Formato simples de propósito: qualquer pessoa abre em Excel/LibreOffice/
    Google Sheets sem depender de ferramenta nenhuma do LYRA.
    """
    if not linhas:
        raise ValueError("Nada para salvar — relatório sem afirmações segmentadas.")
    with caminho.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        writer.writeheader()
        writer.writerows(linhas)


def importar_classificacao(
    relatorio_fidelidade: RelatorioFidelidade,
    caminho: Path,
) -> RelatorioFidelidade:
    """Aplica de volta a classificação que o avaliador preencheu na planilha.

    Só transcreve o que já foi decidido manualmente — não reclassifica nada
    sozinha. É a contraparte de exportar_planilha_classificacao().
    """
    por_indice = {a.indice: a for a in relatorio_fidelidade.afirmacoes}
    with caminho.open(encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            indice = int(linha["indice"])
            classificacao = linha["classificacao"].strip()
            if classificacao not in {"correta", "imprecisa", "nao_sustentada"}:
                raise ValueError(
                    f"Linha {indice}: classificação {classificacao!r} inválida "
                    "ou não preenchida. Esperado correta / imprecisa / "
                    "nao_sustentada."
                )
            afirmacao = por_indice[indice]
            afirmacao.classificacao = classificacao  # type: ignore[assignment]
            afirmacao.justificativa = linha.get("justificativa", "")
    return relatorio_fidelidade
```

`importar_classificacao` valida que a coluna `classificacao` só recebe um dos três valores esperados — se vier vazia (planilha ainda não preenchida) ou com erro de digitação, falha alto e explícito em vez de deixar `fidelidade_global` calcular silenciosamente sobre dado incompleto.

### 5.3 Por que isso continua sendo manual — e onde isso é reforçado no código

`docs/protocolo-validacao.md` já é explícito: "Seria mais rápido pedir a um LLM que classificasse... Seria também circular." Isso bate com a literatura levantada na pesquisa (não é só uma preferência do projeto):

- **Self-preference bias** (Wataoka, Takahashi & Ri, 2024): LLM-juízes pontuam mais alto textos de baixa perplexidade — "familiares" ao próprio padrão de geração — independente de terem sido autogerados. O viés não desaparece só por usar um Gemini diferente para julgar; a distorção vem da distribuição de treino compartilhada.
- **Baixa concordância LLM-juiz × especialista humano** (Szymanski et al., ACM IUI 2025): 64–68% em tarefas de conhecimento especializado — não é substituto confiável de avaliação humana especializada, que é exatamente o caso aqui (estatística de DOE).
- **Questionamento formal de validade/confiabilidade do LLM-as-judge como constructo de medição** (Chehbouni et al., 2025).

Nenhuma dessas referências é sobre DOE/ANOVA especificamente — não existe, ao que a pesquisa encontrou, literatura tratando desse recorte exato. Mas todas sustentam diretamente a decisão já tomada no pré-projeto, então o argumento na monografia não precisa (e não deve) apoiar-se só em "achamos que seria injusto" — há citação primária para isso.

Na prática de código, isso significa: **nenhuma função em `fidelity.py` deve ganhar um parâmetro tipo `avaliador_llm: ChatGoogleGenerativeAI`**. Se alguém propuser isso depois (inclusive um futuro "eu" com prazo apertado), a resposta é não — e vale deixar essa frase como comentário perto de `Classificacao = Literal[...]` no topo do arquivo, do jeito que já está no docstring do módulo.

### 5.4 Rastreabilidade por seção (extensão recomendada, pequena)

Como a saída de `chain.py` agora vem estruturada em 5 seções nomeadas (§2.4), vale a pena que `RelatorioFidelidade` saiba de qual seção cada afirmação veio — poupa o avaliador de ter que caçar isso manualmente ao preencher a planilha. Duas mudanças pequenas:

```python
@dataclass
class Afirmacao:
    indice: int
    texto: str
    secao: str = ""          # <- novo campo, com default: não quebra os testes existentes
    numeros_citados: list[float] = field(default_factory=list)
    ...
```

```python
def prechecar_numeros_por_secao(
    relatorio: NarrativeReport,
    resultado: AnalysisResult,
    *,
    tolerancia_relativa: float = 0.01,
) -> RelatorioFidelidade:
    """Como prechecar_numeros, mas ancorando cada afirmação à seção do
    relatório que a originou (Visão geral, Qualidade do modelo, ...)."""
    afirmacoes: list[Afirmacao] = []
    indice_global = 0
    for secao in relatorio.secoes:
        parcial = prechecar_numeros(secao.texto, resultado, tolerancia_relativa=tolerancia_relativa)
        for a in parcial.afirmacoes:
            a.indice = indice_global
            a.secao = secao.titulo
            afirmacoes.append(a)
            indice_global += 1
    return RelatorioFidelidade(afirmacoes=afirmacoes)
```

E adicionar a coluna `secao` em `exportar_planilha_classificacao`. Isso é aditivo — `Afirmacao(indice=..., texto=...)` continua funcionando sem passar `secao`, e os testes existentes em `test_fidelity.py` não quebram.

---

## 6. Checklist antes de abrir o PR da #7

- [ ] `uv run pytest tests/test_arquitetura.py` continua verde depois de importar `langchain_core`/`langchain_google_genai`/`pydantic` em `narrative/`.
- [ ] Nenhum `bind_tools`, `create_agent`, `code_execution` ou `google_search_retrieval` em `chain.py`.
- [ ] `temperature` é sempre passado explicitamente como `float`, nunca por omissão.
- [ ] Comentário HTML do `relatorio_tecnico.md` é removido antes de virar prompt (§2.3).
- [ ] `PROMPT_VERSION` em `chain.py` bate com o cabeçalho do `.md` — teste de sincronismo (§3) incluído.
- [ ] Aviso registrado em `NarrativeReport.avisos` quando o modelo resolvido está na lista de linhas Gemini que ignoram `temperature`.
- [ ] `pyproject.toml`: piso de `langchain-google-genai` apertado para `>=4.3` (ou versão exata pinada).
- [ ] Testes de fiação sem rede cobrindo a montagem do prompt e o mapeamento seção→título; testes `@pytest.mark.llm` reais, pulados sem `GOOGLE_API_KEY`.
- [ ] `docs/protocolo-validacao.md`, tabela "Registro de mudanças no protocolo", atualizada se o texto do prompt mudou durante a implementação.
- [ ] Confirmado que `fidelity.prechecar_numeros` (ou a variante por seção) continua devolvendo tudo com `classificacao="pendente"` — nenhuma classificação automática entrou em lugar nenhum do fluxo.