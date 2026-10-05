## O que muda

<!-- Uma frase. O que este PR faz. -->

Fecha #

## Por quê

<!-- O contexto. Se a decisão for de arquitetura, houve ADR novo em
     docs/decisoes/? -->

## Como conferir

<!-- Passos para o revisor rodar e ver funcionando. -->

```bash
uv run pytest
```

## Checklist

- [ ] `uv run pytest` passa
- [ ] `uv run ruff check .` limpo
- [ ] Se mexi em `core/`: os testes de regressão dos casos de estudo continuam passando
- [ ] Se mexi na fronteira núcleo/LLM: `tests/test_arquitetura.py` passa
- [ ] Se mudei um limiar do §4.3: **o pré-projeto também precisa mudar** — combinado com a orientadora?
- [ ] Se mudei o prompt (templates ou few-shot): incrementei `PROMPT_VERSION` em `ai/prompts.py`
