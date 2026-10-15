# Avaliação de IHC da interface — o que a literatura dá de respaldo

Dossiê de apoio (mesmo espírito de `README.md` desta pasta: não é ADR, é
material para embasar decisão e escrever texto de TCC). Cobre o eixo de
usabilidade/IHC da interface do EnsaIA, que é complementar ao
`docs/protocolo-validacao.md` — aquele cobre a validação **estatística**
(§4.3 a–e); este cobre a validação de **interface**, cruzando a interface
real (`src/ensaia/ui/`) com duas fontes:

1. **SILVA JUNIOR, C. R. (2025)** — TCC de IHC (UFU) que aplica as 10
   heurísticas de Nielsen, HTA e Design Universal para avaliar o RCmdr (R)
   como ferramenta de ensino de estatística, e propõe um protótipo de
   melhorias.
2. **BAKRI, R. et al. (2025)** — "LOSARI: A novel R-based statistical
   software to facilitate students' self-regulated learning in statistics
   courses", *MethodsX* 15, 103739 (Elsevier). Software R/Shiny com tutorial
   em vídeo embutido, notificação de erro em tempo real e interpretação
   automática, validado por comparação numérica exata contra o R e por
   satisfação do usuário (modelo EUCS).

## 1. O que as duas fontes criticam/propõem (resumo)

| Achado | Fonte |
|---|---|
| RCmdr não dá *feedback* de qual ação foi concluída (heurística 1 de Nielsen) | SILVA JUNIOR, 2025, §3.2.1 item 1 |
| RCmdr usa jargão técnico sem tradução ("Resumo numérico" para "média") | idem, item 2 |
| RCmdr não tem desfazer/confirmação antes de ações | idem, item 3 |
| RCmdr é consistente na disposição dos menus (ponto positivo) | idem, item 4 |
| Erros aparecem só no *console*, sem aviso na própria interface | idem, item 5 |
| Funcionalidades dependem de memorização de caminho de menu (sem ícone/agrupamento) | idem, item 6 |
| Sem atalhos/caminhos rápidos para usuários experientes | idem, item 7 |
| Estética pouco cuidada (sem ícones, cores só funcionais) | idem, item 8 |
| Mensagens de erro não explicam causa nem sugerem correção | idem, item 9 |
| Ajuda existe mas não é visualmente destacada | idem, item 10 |
| Nenhum software R concorrente (JASP, Jamovi, SWANSTAT) combina tutorial em vídeo embutido + notificação de erro em tempo real + interpretação automática no mesmo ambiente | BAKRI et al., 2025, Table 1 |
| Validação por comparação numérica exata com o R (coeficientes, estatística t) é um método aceito e publicável (MethodsX) | idem, Table 2 |
| Satisfação do usuário medida pelo modelo EUCS (conteúdo, precisão, interface, desempenho) é usada como evidência complementar de qualidade | idem, seção "Student's satisfaction" |

## 2. Onde o EnsaIA já atende — evidência no código (respaldo para o TCC)

A interface do EnsaIA (NiceGUI, não Streamlit — a arquitetura evoluiu depois
de `docs/pesquisa/nucleo-estatistico.md` §6) já endereça quase todos os
pontos que SILVA JUNIOR (2025) aponta como falha do RCmdr, e já tem um
equivalente funcional a duas das três inovações de LOSARI.

| Heurística / recurso | RCmdr (crítica do TCC de IHC) | EnsaIA | Onde no código |
|---|---|---|---|
| H1 — Visibilidade do status | Sem indicação de ação concluída | Trilha de passos na home; `ui.notify` por resultado; `botao.props("loading")` no PDF | `ui/home.py:103` (`_trilha`); `ui/analise.py:1088` (`_baixar_pdf`) |
| H2 — Compatibilidade com o mundo real | "Resumo numérico" para calcular média | Rótulos em português simples ("Mapear", "Analisar"); jargão estatístico (R², ANOVA) mantido só onde é do domínio, sempre com dica ao lado | `ui/analise.py:88` (`_GRUPOS_MAPA`); `ui/ajuda.py:23` (`EXPLICACOES`) |
| H3 — Controle e liberdade | Sem desfazer | Termos do modelo podem ser tirados/devolvidos antes de reajustar; coluna pode voltar de grupo a qualquer momento | `ui/analise.py:1125` (`_ajustar_modelo`) |
| H5 — Prevenção de erros | Erro só aparece depois, no console | Validação antes de rodar (`if not fatores: ui.notify(...)`); coluna de texto recusa entrar em grupo numérico na hora do arrasto | `ui/analise.py:153-158`; `ui/analise.py:224-229` (`_Mapeamento.mover`) |
| H6 — Reconhecimento, não memorização | Funções escondidas em submenus sem ícone | Cartões com ícone, agrupados por etapa (Dados/Triagem/Modelo/Diagnóstico/Otimização), cada um com a pergunta que responde | `ui/painel_analises.py:36` (`ETAPAS`) |
| H9 — Ajudar a diagnosticar/corrigir erro | Mensagem técnica sem causa nem solução | Mensagens em português de laboratório com causa e correção (ex.: "Para gerar o PDF, instale o extra [report]") | `ui/analise.py:1077-1082`; `ui/narrar.py:402` (`_mensagem_erro`) |
| H10 — Ajuda e documentação | Ajuda existe mas escondida num menu textual | Botão de glossário sempre visível, logo após a marca, abre modal com glossário e guia de leitura | `ui/ajuda.py:281` (`botao_glossario`) |
| Interpretação automática (LOSARI) | — | `indicativos.py` já gera leitura em texto por métrica ("Significativa: o modelo explica a resposta"); `narrar.py` gera relatório textual completo | `core/indicativos.py:41`; `ui/narrar.py:441` |
| Notificação de erro em tempo real com sugestão (LOSARI, Table D.1) | — | `ui.notify(type="negative"/"warning", ...)` com mensagem + correção, em quase todo fluxo (upload, mapeamento, otimização, IA) | `ui/upload.py:64-70`; `ui/analise.py:153-177` |
| Validação por comparação numérica exata (LOSARI, Table 2) | — | `validation/metrics.py` já faz o mesmo tipo de comparação (coeficiente a coeficiente, com tolerância), e de forma mais rigorosa: tolerância documentada e casos de estudo publicados reais, não só o dataset `iris` | `docs/protocolo-validacao.md`; `src/ensaia/validation/metrics.py` |

O ponto mais forte para o capítulo de fundamentação do TCC: o EnsaIA **já
fazia**, antes de ler esses dois artigos, o equivalente ao que LOSARI chama
de inovação (interpretação automática + notificação de erro em tempo real) —
e vai além num ponto que LOSARI não cobre: `ai/fidelity.py` confere cada
número que uma IA escreve contra o `AnalysisResult`, prevenindo alucinação
num jeito que a interpretação automática *template-based* de LOSARI nem
precisa (porque não usa LLM) nem o próprio LOSARI resolve se algum dia
adicionar "interpretação com IA" (citado como `trabalho futuro` no próprio
artigo, seção *Limitations*: "the automatic interpretation feature will be
extended with AI-driven algorithms"). Isso é citável como diferencial.

## 3. Lacunas reais — o que falta ou precisa ser refeito

### A. Sem indicação de carregamento nas três ações mais pesadas do pipeline 🔴

`_baixar_pdf` já usa `run.io_bound` + `botao.props("loading")` (linha 1091),
mas as três ações que de fato rodam o núcleo estatístico **não têm
indicação nenhuma de que algo está acontecendo**:

| Ação | Onde | O que roda |
|---|---|---|
| "Analisar" | `ui/analise.py:195` (botão), chama `ao_analisar` → `analisar_e_mostrar` (linha 149) | `core.fluxo.analisar_tabela`: OLS, ANOVA Tipo II, possível backward elimination iterativo, Shapiro-Wilk, Cook |
| "Reajustar" | `ui/analise.py:1189` dentro de `_ajustar_modelo` | o mesmo `reanalisar()` acima |
| "Encontrar a melhor condição" | `ui/analise.py:850` dentro de `_bloco_otimizacao` → `buscar()` (linha 816) | `core.desirability.otimizar`: amostra LHS (até `n = 10k` pontos para k>4) + Nelder-Mead a partir de 5 reinícios |

Isso é exatamente a heurística 1 que SILVA JUNIOR (2025) aponta como falha
do RCmdr ("não há qualquer sinal visual indicando que essa ação foi
concluída com sucesso") e é o oposto do que LOSARI reivindica como virtude
arquitetural ("Shiny's input–output bindings... deliver immediate visual
feedback"). Com datasets pequenos a computação é rápida o bastante para não
doer, mas com `quadratico` + redução de termos + k≥4 fatores na otimização
o atraso é perceptível e, sem spinner/`loading`, parece trava.

**O que fazer:** envolver as três chamadas em `run.io_bound` (seguindo o
padrão já estabelecido em `_baixar_pdf`) e marcar o botão correspondente com
`.props("loading")` / `.props(remove="loading")`, do jeito que já é feito
para o PDF. É uma mudança local, reversível, que não toca o núcleo
determinístico — só a camada de interface.

### B. Sem tutorial em vídeo embutido 🟡 (não urgente)

A inovação mais citada de LOSARI é o vídeo-tutorial que abre como pop-up
móvel dentro do próprio ambiente de análise, sem o usuário sair da tela
(BAKRI et al., 2025, Fig. 2). O EnsaIA cobre a mesma necessidade com as
lâmpadas de dica (`ui/ajuda.py`) e o modal de glossário, que são mais leves
de manter, mas não têm o efeito de "ver alguém fazendo" que ajuda
iniciantes completos. Vale registrar como item de trabalho futuro no TCC,
não como pendência de implementação — gravar e manter vídeos tem custo
contínuo que os outros dois artigos não equacionam (LOSARI mesmo lista "the
video tutorial library is still limited in number and scope" como
limitação própria).

### C. Falta uma tabela consolidada de erro → causa → correção 🟢 (documentação, barato)

LOSARI formaliza seu tratamento de erro numa tabela (Table D.1: tipo de
erro, condição de disparo, mensagem, solução sugerida). O EnsaIA já tem o
comportamento espalhado pelo código (`ui/upload.py`, `ui/analise.py`,
`ui/narrar.py`), mas não uma tabela única. Vale extrair uma tabela
equivalente para o capítulo de resultados do TCC — é evidência de paridade
com LOSARI sem exigir nenhuma mudança de código, só documentação.

### D. Sem instrumento formal de satisfação do usuário 🟡

Os dois artigos fecham a validação de interface com um instrumento
quantitativo: LOSARI usa EUCS (777 respondentes, 4 dimensões); SILVA JUNIOR
(2025) cita o SUS como *trabalho futuro* (não chegou a aplicar). O
`protocolo-validacao.md` do EnsaIA cobre muito bem a validação estatística
(§4.3 a–e), mas não tem um eixo equivalente para a interface. Se o TCC do
EnsaIA quiser reivindicar "interface validada", precisa de um desses dois
instrumentos aplicado a usuários reais — isso não se resolve no código, é
desenho de estudo (poderia virar um §4.4 ou um ADR novo, análogo ao 0003,
decidindo SUS vs. EUCS e o N mínimo).

### E. Sem atalhos de teclado para uso repetido 🟢 (baixa prioridade)

SILVA JUNIOR (2025) aponta a ausência de atalhos no RCmdr (heurística 7).
O EnsaIA já cobre o mínimo de acessibilidade por teclado (tabindex,
Enter/Espaço nos cartões, navegação por Tab), mas não tem atalho global para
ações frequentes (ex.: re-analisar). Como o uso típico é uma sessão só por
experimento (não uso repetido diário como o RCmdr em sala de aula), o custo
de não ter isso é baixo — registrar como nota, não como ação.

## 4. Como usar isto no TCC

- O quadro da seção 2 serve de evidência direta, com referência de arquivo
  e linha, de que o EnsaIA foi desenhado (ainda que sem citar os dois
  artigos no momento da implementação) em conformidade com heurísticas de
  Nielsen e com o padrão de interpretação automática + erro em tempo real
  que a literatura recente (LOSARI, MethodsX 2025) trata como estado da
  arte em software estatístico educacional/científico em R.
- O item A é o único achado desta análise que é código a corrigir, não
  só texto a escrever — baixo risco, mudança local, mesmo padrão já usado
  em `_baixar_pdf`.
- Os itens B, D e E são material de "trabalho futuro" do TCC, não pendência
  de implementação — nos dois artigos de referência eles também aparecem
  como limitação ou futuro, nunca como entregue.
