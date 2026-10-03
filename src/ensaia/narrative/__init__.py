"""Camada de interpretação por LLM.

Regra deste pacote: consome `AnalysisResult` e produz texto. Não importa
numpy, pandas nem statsmodels, e não calcula estatística nenhuma. Se um número
precisa aparecer no relatório, ele vem pronto do núcleo.

Ver docs/decisoes/0001-fronteira-deterministica-llm.md.
"""
