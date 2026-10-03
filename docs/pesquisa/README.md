# Pesquisa de domínio — imersão 2026-08-24

Dossiês produzidos por uma varredura de pesquisa (17 temas em paralelo +
verificação cética de cada candidato a caso de estudo via WebFetch, 31
agentes no total) antes de começar a implementar o núcleo do EnsaIA. Não são
ADR (não registram uma decisão tomada) — são material de apoio para tomar as
decisões registradas em `docs/decisoes/` e para escrever o código das
issues #3–#10.

| Documento | Cobre | Issues relacionadas |
|---|---|---|
| [`nucleo-estatistico.md`](nucleo-estatistico.md) | OLS, matriz de modelo, ANOVA tipo II, falta de ajuste, seleção de termos, efeitos, desejabilidade de Derringer-Suich, amostragem LHS | #3, #4, #5, #6, notas de #9 e #10 |
| [`narrativa-llm.md`](narrativa-llm.md) | Chain LangChain + Gemini, saída estruturada, versionamento de prompt, e como fechar o §4.3(e) em `validation/fidelity.py` | #7 (e o elo que falta para #8) |
| [`casos-de-estudo-candidatos.md`](casos-de-estudo-candidatos.md) | Candidatos reais (fatorial 2^k, CCD, Box-Behnken) para `casos_de_estudo/`, cada um com o que foi de fato conferido abrindo o artigo | #2 do pré-projeto (§4.2), alimenta #8 |

## Como usar isto

Estes documentos foram escritos por agentes de pesquisa e **não substituem
conferência humana** — em especial `casos-de-estudo-candidatos.md`, que trata
de citação bibliográfica: mesmo com uma etapa de verificação cética embutida
(um segundo agente abriu cada DOI/URL antes de aprovar), erros de transcrição
em `referencia.yaml` são exatamente o risco que `casos_de_estudo/README.md`
já avisa que não gera erro nenhum — só um resultado de validação plausível e
falso. Trate cada "alerta para revisão humana" nesses documentos como
bloqueante antes de qualquer valor virar `referencia.yaml`.

Se o texto do prompt de pesquisa, a versão das libs, ou uma decisão de
arquitetura mudar depois desta data, estes dossiês podem ficar desatualizados
— eles descrevem o estado do conhecimento em 2026-08-24, não uma verdade
permanente.
