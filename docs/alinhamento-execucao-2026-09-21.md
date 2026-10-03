# Alinhamento de execução do LYRA

**Registro:** reunião de Gustavo Neves e Gabriel Athayde em 21 de setembro de
2026. Este documento converte os acordos em entregas verificáveis. Não altera
o protocolo de validação nem substitui o pré-projeto aprovado.

## Objetivo operacional

Entregar um núcleo aberto e reprodutível para análise de planejamento de
experimentos químicos, e demonstrar sua equivalência ou suas divergências em
relação a resultados publicados. A contribuição defendida no TCC é a qualidade
da análise estatística, sua rastreabilidade e sua acessibilidade. Interface,
MCP e IA são meios para acesso, não evidência estatística por si mesmos.

## Decisões acordadas

| Tema | Decisão de trabalho | Critério de encerramento |
|---|---|---|
| Dados de desenvolvimento | Usar somente as bases que a Profa. Luiza disponibilizar e autorizar explicitamente. | Inventário com origem, permissão, tipo de planejamento, campos e restrição de uso. |
| Validação externa | Selecionar 3 casos públicos, preferencialmente um fatorial completo, um CCD e um Box-Behnken, que publiquem dados e resultados estatísticos comparáveis. | Cada caso segue a estrutura `casos_de_estudo/<nome>/` e passa por dupla conferência da transcrição. |
| Comparação | Reproduzir os resultados publicados e, quando identificado, contextualizar o software comercial usado no estudo. Não se afirma equivalência com um software sem valores publicados ou execução comparável. | Tabela por caso com coeficientes, significância, R²/R² ajustado, condição ótima e explicação de divergências. |
| Núcleo e IA | O cálculo permanece determinístico, offline e separado da narrativa. A IA apenas explica um `AnalysisResult` congelado. | Testes de arquitetura e métricas de validação aprovados. |
| MCP | Considerar como diferencial de distribuição após o pipeline estatístico e a validação estarem utilizáveis. | Protótipo separado, documentação de autenticação e demonstração sem alterar o núcleo. |
| Modelo local | DeepSeek ou outro modelo local pode ser avaliado como experimento de acessibilidade, com configuração da máquina e versão registradas. | Registro reprodutível e avaliação manual de fidelidade, sem confundir esse teste com a validação estatística. |

## Escopo do MVP acadêmico

O MVP que sustenta a reunião com a orientação não é uma interface completa. É
um fluxo capaz de receber um conjunto tabular de DOE, ajustar o modelo OLS,
produzir a ANOVA tipo II e resultados serializáveis, e comparar o resultado
com um caso publicado.

Para o MVP ser apresentado como funcional, ele precisa conter:

1. Leitura e validação de CSV, incluindo fatores, resposta, dados ausentes e
   escala/codificação declarada.
2. Ajuste OLS com matriz de modelo, ANOVA tipo II e checagens de consistência
   entre ajuste canônico e ajuste auxiliar do `statsmodels`.
3. Coeficientes, efeitos e critérios de significância em `alpha = 0,05`.
4. Um `AnalysisResult` completo, congelado e serializável.
5. Um caso de estudo totalmente transcrito, conferido e executado pelo runner,
   com as métricas do protocolo de validação.
6. Testes automatizados executados em ambiente Python funcional, com o
   resultado registrado.

Otimização por desejabilidade, interface Streamlit, relatório por LLM, MCP e
pesquisa com usuários entram depois desse corte. Eles podem aparecer como
protótipos ou trabalho futuro, nunca como requisito para comprovar o modelo.

## Papéis e forma de colaboração

| Frente | Responsável principal | Apoio e evidência esperada |
|---|---|---|
| Escrita, método e referências | Gabriel | Gustavo revisa aderência ao que foi implementado; cada afirmação de resultado aponta para caso, comando e artefato gerado. |
| Núcleo técnico e reprodutibilidade | Gustavo | Gabriel revisa clareza para leitor não técnico e confere se o código atende ao método descrito. |
| Bases autorizadas pela orientadora | Gustavo, com confirmação da Profa. Luiza | Inventário de bases e permissão registrada antes de uso. |
| Casos publicados e transcrição | Ambos | Uma pessoa transcreve e a outra confere PDF, tabela e página. |
| Fluxograma, mapa e acompanhamento | Gabriel | Mapa com duas árvores, técnica e teórico-metodológica, mais backlog semanal único. |

Nenhuma divisão é uma barreira: quem identificar uma lacuna abre a tarefa,
associa a evidência necessária e a atribui para revisão conjunta.

## Sequência de execução até 10 de outubro

Como a reunião ocorreu em 21 de setembro e este registro foi consolidado em
27 de setembro, os itens "amanhã" e "até sexta" da conversa viram ações
imediatas com data explícita.

| Janela | Entrega | Dono | Evidência objetiva |
|---|---|---|---|
| 27 a 29 set. | Confirmar com a Profa. Luiza quais bases podem ser usadas; catalogar as recebidas. | Gustavo | `docs/inventario-bases.md` ou planilha equivalente com status `autorizada`, `pendente` ou `não usar`. |
| 27 a 30 set. | Triar candidatos da literatura e escolher o primeiro caso reproduzível que não seja mistura. | Ambos | Critério preenchido, PDF acessível e estrutura do caso criada sem números inventados. |
| 28 set. a 2 out. | Fechar o caminho técnico mínimo: entrada, OLS, ANOVA tipo II, efeitos e caso executável. | Gustavo | Testes e comando de validação com saída versionada. |
| 28 set. a 3 out. | Criar estrutura do texto: problema, objetivo, método, dados, protocolo, resultados e limites. | Gabriel | Sumário comentado, referências rastreáveis e campos reservados para evidência real. |
| 3 a 6 out. | Fazer revisão cruzada do primeiro resultado e ajustar lacunas descobertas pela reprodução. | Ambos | Tabela de comparação e divergências explicadas ou marcadas como pendentes. |
| 6 a 8 out. | Selecionar e iniciar os outros dois casos, sem sacrificar a qualidade do primeiro. | Ambos | Fichas de proveniência e plano de transcrição. |
| Até 10 out. | Reunião com Marcos Braga, se a agenda permitir. | Ambos | Demonstração de um caso, plano de validação de três casos e perguntas de decisão preparadas. |

## Riscos que precisam permanecer visíveis

1. **Misturas não entram como DOE comum.** Componentes com soma constante
   exigem modelo de Scheffe ou pseudocomponentes. Enquanto essa extensão não
   existir, casos de mistura são referência bibliográfica, não casos validados
   pelo pipeline atual.
2. **Caso candidato não é caso validado.** O diretório
   `tylosin-photo-fenton` ainda é uma estrutura de trabalho não rastreada; só
   ganha status de validado após fonte, transcrição dupla, runner e comparação.
3. **Não usar números gerados ou completados por IA.** Valor não publicado
   fica `null`, com origem de cada número em tabela/página no `fonte.md`.
4. **Ambiente de testes precisa de reparo.** Antes de reportar testes verdes,
   provisionar Python 3.11 e `pytest` de forma que `uv run pytest` execute de
   fato a suíte.
5. **Dados da orientadora são condicionais.** Permissão, finalidade acadêmica,
   anonimização e possibilidade de versionamento devem estar claras antes de
   copiar dados para o repositório.

## Cadência e definição de pronto

Trabalhar em ciclos semanais, com uma revisão breve no início e no fim da
semana. A cada duas semanas, solicitar reunião de acompanhamento com a Profa.
Luiza. Reuniões extraordinárias só entram quando houver decisão que bloqueie a
próxima entrega.

Uma tarefa só é considerada pronta quando possui código ou texto revisável,
evidência reprodutível, indicação de limitações e atualização do mapa/backlog.
"Funciona no meu computador", uma demonstração visual ou uma resposta de IA
sem fonte não satisfazem esse critério.

## Pauta mínima para a reunião com Marcos Braga

1. Problema, público e diferença prática frente às barreiras de licença e
   conhecimento estatístico.
2. Arquitetura: cálculo determinístico separado da narrativa por IA.
3. Método de validação com três casos públicos e os cinco critérios do
   pré-projeto.
4. Demonstração do primeiro caso, incluindo qualquer divergência encontrada.
5. Pedido objetivo de crítica: suficiência dos casos, métricas e recorte do
   diferencial MCP como extensão, não como substituto da validação.
