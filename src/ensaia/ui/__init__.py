"""Camada de interface web (NiceGUI).

Só apresentação: monta telas e chama o núcleo determinístico e as camadas de
relatório/IA. Nenhuma conta estatística acontece aqui (spec, seção 7.1) — se a
tela precisa de um número, ele vem pronto no `AnalysisResult`.

Público-alvo: profissionais e estudantes de química sem formação avançada em
estatística ou programação (§1 do pré-projeto). Toda decisão de interface
responde a "isso faz sentido para quem nunca ouviu falar de ANOVA?".
"""
