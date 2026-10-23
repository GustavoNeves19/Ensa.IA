# 0014 — Redução de modelo sempre reajusta (diverge do livro-texto num exemplo)

**Status:** Aceita · **Data:** 2026-10-23 · **Relacionada:** [0003](0003-criterio-de-significancia.md)

## Contexto

Ao ler Barros Neto, Scarminio e Bruns (2010) para validar as métricas de DCCR
do EnsaIA contra o livro-texto citado no TCC (ver
`docs/pesquisa/barros-neto-dccr.md`), apareceu uma discrepância de prática, não
de fórmula, no exemplo 6A.3 (redução de colesterol, p. 303–306, seção 16.4 do
dossiê): o livro ajusta o modelo quadrático completo, descarta os termos não
significativos (mantém só x₁ e x₃) e publica o "modelo reduzido" — **mas os
coeficientes publicados são exatamente os mesmos do modelo completo**, só sem
as linhas dos termos descartados. Não houve um segundo ajuste.

A recomputação confirma isso: reajustando de verdade só com x₁, x₃ e seus
quadráticos, o intercepto muda de 1,861 (livro, igual ao modelo completo) para
1,8135, e os quadráticos de −0,083/−0,093 para −0,0760/−0,0857. São números
diferentes dos publicados no livro.

O EnsaIA, em `core/termos.reduzir_backward`, faz o oposto: a cada termo
removido, reajusta o modelo com os termos remanescentes (`"Elimina, um a um,
o termo não significativo de maior p, e reajusta"`, docstring da função) e
repete até estabilizar. Essa é a prática padrão da literatura de DOE e do
software comercial (Minitab, Design-Expert, Statistica) — backward
elimination sem reajuste a cada passo não é um procedimento reconhecido fora
deste exemplo específico do livro.

## Decisão

O EnsaIA **mantém o reajuste** a cada remoção de termo (`reduzir_backward`
continua como está). Não é um bug a corrigir; é a prática estatisticamente
correta, e a maioria dos softwares de referência da área faz o mesmo.

O ponto deste ADR não é mudar o código — é registrar, por escrito, que esta
escolha **diverge deliberadamente** do único exemplo de redução de modelo que
o livro-texto do TCC publica (6A.3). Isso importa porque, se algum caso de
estudo futuro for construído a partir de um exemplo do livro que envolva
redução de modelo, os coeficientes do "modelo reduzido" publicado **não
vão bater** com o que `validar_caso` produz, mesmo com os dados certos e o
pipeline certo — e sem este registro, isso pareceria um bug de transcrição.

## Consequências

**Boas**
- A prática do EnsaIA é a cientificamente correta: um modelo reduzido sem
  reajuste reporta coeficientes de um modelo que não é o que está sendo usado
  (eles vêm do ajuste com os termos descartados ainda presentes).
- Documentado numa única fonte (`docs/pesquisa/barros-neto-dccr.md` §17, linha
  "C1 Redução do modelo") e agora também aqui, como ADR — quem ler só um dos
  dois lugares ainda encontra a referência ao outro.

**Ruins / a vigiar**
- Nenhum caso de estudo baseado no exemplo 6A.3 do livro pode comparar
  coeficientes do "modelo reduzido" diretamente — só o modelo completo (10
  parâmetros) seria comparável termo a termo. Se esse exemplo virar caso de
  estudo formal algum dia, `referencia.yaml` precisa registrar os coeficientes
  do modelo **completo**, não os do "reduzido" da Tabela/Equação do livro.
- `core/anova.selecionar_termos` (uma função que classifica termos em
  mantidos/descartados **sem reajustar**, mais fiel ao que o livro realmente
  faz em 6A.3) existe no módulo, é testada isoladamente
  (`tests/unit/test_anova.py`), mas **não é chamada por nenhum caminho de
  produção** — `core/pipeline.py` usa `core/termos.reduzir_backward`, que tem
  sua própria lógica de eliminação (com reajuste) e não chama
  `selecionar_termos`. Achado ao escrever este ADR: é código morto, não um
  caminho alternativo já em uso. Vale decidir, numa revisão futura, se ela
  deve virar a opção "sem reajuste" exposta ao usuário, ou ser removida.
