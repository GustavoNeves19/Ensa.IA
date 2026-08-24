"""Interface Streamlit do LYRA.

    uv run streamlit run src/lyra/ui/app.py

Público-alvo: profissionais e estudantes de química sem formação avançada em
estatística ou programação. Isso é requisito, não preferência — é a barreira
que o TCC se propõe a derrubar (§1 do pré-projeto). Toda decisão de interface
aqui responde a "isso faz sentido para quem nunca ouviu falar de ANOVA?".

Três regras que decorrem disso:

1. Nada de pedir dado codificado. O usuário informa níveis reais; a
   codificação é interna.
2. Nenhum termo estatístico aparece sem explicação ao lado, na primeira vez.
3. Quando o pipeline bloqueia algo (R² baixo, falta de ajuste inaplicável), a
   tela diz o motivo em português — não some com o botão nem mostra um valor
   vazio.

TODO(#10): implementar.
    - upload de CSV/XLSX + prévia dos dados
    - identificação de fatores e respostas (com sugestão automática)
    - execução do pipeline com barra de progresso
    - resultados: tabela de coeficientes, ANOVA, R², falta de ajuste
    - gráficos: superfície de resposta, Pareto de efeitos, resíduos
    - relatório do LLM, com o JSON do AnalysisResult disponível ao lado
      (transparência: quem quiser conferir os números, consegue)
    - download do relatório e do AnalysisResult
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError("Ver issue #10 — interface Streamlit.")


if __name__ == "__main__":
    main()
