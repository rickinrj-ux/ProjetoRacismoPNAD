# Auditoria de pré-entrega — 29/09/2026

Escopo: o entregável (`tcc_normas.tex` → PDF e .docx), os csv que o alimentam, as
figuras, as tabelas, a narrativa e a cadeia de geração. Pedida pelo autor às
vésperas da entrega.

Método: às verificações que o projeto já tinha (`validate_consistency.py`,
`verificar_analises.py`, `conferir_anexos_normas.py`, `pericia_cruzada.py`)
somei varreduras novas — rastreio de cada número da prosa até um csv, conferência
tabela a tabela contra a fonte, leitura do log do LaTeX, comparação PDF × Word e
inspeção visual de páginas renderizadas.

---

## 🔴 CRÍTICO — corrigido nesta auditoria

### C1. O Resumo, o Abstract e a Conclusão estavam com frases truncadas no PDF

**O defeito.** `pct()` devolve o símbolo `%` cru, porque serve também ao .docx e
ao .pptx. Em LaTeX, `%` inicia comentário: **tudo o que vem depois dele na linha
desaparece do PDF**. Dez linhas do entregável perdiam texto, e não em qualquer
lugar — no Resumo (4), no Abstract (3) e na Conclusão (3).

O que a banca leria no Resumo:

> "O gap agregado foi de 19,1" ⟵ *fim da frase; some "%, dos quais 47,0%
> resultaram da mediação pelo bairro de moradia"*

> "o diferencial que sobreviveu ao controle de capital humano, contexto e estado
> foi de 10,2" ⟵ *some "%, e 7,0% persistiram dentro da mesma ocupação"*

**Correção.** `tcc/scripts/tcc_normas_texto.py` passou a usar um `pct()` próprio
que escapa o símbolo; o de `params_nucleo` fica cru, porque o .docx e o .pptx
precisam dele assim. Regerado e conferido no PDF: Resumo e Abstract íntegros.

**Regra para não voltar.** `validate_consistency.py` acusa `%` precedido de
dígito e sem escape no `.tex` de entrega. Testada nos dois sentidos: reintroduzi
o defeito numa linha, a regra apontou exatamente aquela linha e mais nenhuma;
com o texto corrigido, zero achados.

### C2. A figura principal do bloco de ML estava ilegível

Quando um patch removeu o *dependence plot*, sobrou uma `subfigure` órfã: o
beeswarm saía com **49% da largura**, rótulos de 29 variáveis miniaturizados e
duas legendas empilhadas ("(a) Beeswarm…" + "Figura 2…"). Numa impressão, não se
lia nenhum nome de variável.

Corrigido: figura simples a 92% da largura, legenda única com título de ação.
Conferido na página renderizada — "Raça (negro)" agora se lê.

---

## 🟠 PENDENTES — P1 e P2 corrigidos a pedido do autor; os demais em aberto

### P1. Uma tabela inteira em formato numérico inglês — ✅ CORRIGIDO

`tab:qr_melhorias` (regressão quantílica, vinda de `qr_melhorias.tex`) traz **29
decimais com ponto** — `$-0.0832$ (0.0019)`, `$-8.0\%$` — enquanto o documento
inteiro usa vírgula. Na mesma tabela:

- `$p = 1.84e-64$` e `3.3e-03` — notação de computador numa tabela de TCC;
- `$Z = -16.95$` e `$\mathbf{-4.03\text{pp}}$`.

**Correção.** A montagem da tabela saiu de dentro de `run_ob_qr_melhorias.py`
para `scripts/analise/tabela_qr_tex.py`, que a remonta a partir de
`qr_melhorias.csv` e `qr_kb_test.csv` — os dois já guardavam tudo o que a tabela
mostra, então não foi preciso repetir o bootstrap de 200 réplicas. O script de
análise agora chama esse módulo, para não regredir na próxima execução.

Conferência: comparei os 57 números da tabela antiga com os da nova. Mudaram
três, todos entendidos:

| antes | depois | motivo |
|---|---|---|
| `p = 1.84e-64` | `p < 0{,}001` | intencional |
| `p=0.0033` | `p = 0{,}003` | intencional |
| `-0.1012` | `-0{,}1013` | **arredondamento duplo** (ver abaixo) |

O `-0,1012` merece registro: o csv guarda o coeficiente com 5 casas
(`-0.10125`) e a tabela mostra 4. Arredondar um valor já arredondado devolve
`-0,1013`, enquanto a execução original, com o valor cheio em memória, imprimiu
`-0,1012`. A diferença é de 0,0001 log-pontos — irrelevante para qualquer
leitura —, mas a causa é real: **o csv deveria guardar mais casas**. Fica
registrado na docstring do módulo para a próxima execução.

Um caso parecido eu consegui eliminar: o gap em % passou a ser recalculado do
coeficiente em vez de lido da coluna `gap_pct` (que tem 2 casas), o que devolveu
o `-11,0%` de Mulheres q10 que o arredondamento duplo havia virado `-10,9%`.

Resultado: **zero** decimais em formato inglês nas tabelas do documento e
**zero** notação científica no PDF.

### P2. Duas equações ultrapassam a margem — ✅ CORRIGIDO

O log do LaTeX registrava a equação (1) **61,6 pt** (2,17 cm) mais larga que a
linha, e a (2) **37,0 pt** (1,30 cm). São as equações do nível 1 e do nível 2 do
HLM, na página 5, e o excesso era visível na página renderizada.

**Correção.** Em vez de quebrar a fórmula em duas linhas — o que exigiria
`split` e brigaria com a numeração manual que o gerador insere para sobreviver
ao pandoc —, a distribuição do erro saiu de dentro da equação e foi para a frase
seguinte: *"em que Z reúne horas, situação urbana e ano (e, no M4, vínculo e
grupo CBO), e o termo de erro é ε_ij ~ N(0, σ²)"*. A equação encurta, cabe com
folga, e a prosa fica mais legível do que o `\qquad` que a empurrava para fora
da página. O mesmo na equação (2), com u_0j.

Conferido no log e na página renderizada: os dois estouros grandes
desapareceram. Restam dois pequenos em parágrafos de texto corrido (9,1 pt e
11,8 pt, 3 a 4 mm), que exigiriam reescrever prosa do autor e não compensam.

### P3. A tabela RIF misturava duas bases na mesma linha — ✅ CORRIGIDO

`tab:rif_ob` trazia, lado a lado, o gap **observado** (0,559 no q10) e
porcentagens que eram fração do gap **RIF** (0,528). Quem multiplicasse
0,559 × 64,9% obteria 0,363, contra os 0,343 de dotações — erro de 5,8%.

**Correção.** Entrou a coluna `Gap RIF`, que já existia no csv e é a base real
das porcentagens, e a legenda passou a dizer que Dotações + Retornos somam 100%
*do gap RIF* --- "que é o gap decomposto pelo método e difere do gap observado
da segunda coluna". O "Como ler" do texto foi ajustado no mesmo sentido.

A conta agora fecha à vista: 0,528 × 64,9% = 0,343. Nenhum número existente
mudou; só entrou uma coluna.


### P4. Abstract em inglês com convenção numérica errada — ✅ CORRIGIDO

Era maior do que eu havia registrado. Além dos decimais com vírgula ("the
aggregate gap was 19,1%", "odds ratios of 0,699"), os **milhares saíam com
ponto**: "covering 7.694.198 observations", que em inglês se lê como um decimal.

**Correção.** `tcc_normas_texto.py` ganhou três funções en-US (`en`, `en_pct`,
`en_milhar`) usadas só no bloco do Abstract — o único trecho em inglês do
trabalho, onde a convenção se inverte. Dez chamadas trocadas. O Resumo em
português segue com vírgula, conferido depois de regerar:

| | antes | depois |
|---|---|---|
| Abstract | `7.694.198 observations`, `19,1%`, `0,699` | `7,694,198 observations`, `19.1%`, `0.699` |
| Resumo | `19,1%`, `47,0%` | inalterado |

### P5. Dois csv concorrentes para a decomposição — ❌ ACHADO ERRADO MEU

**Retificação.** Escrevi que "`gerar_relatorio_tcc.py` lê a primeira para
`k["gap_m4"]`", o que sugeria risco de o documento usar a especificação errada.
Não é o que o código faz: ele lê `gap_decomposicao_serie_completo.csv` e, **em
seguida, substitui tudo pelo `gap_decomposicao_stepup.csv` quando este existe**
--- com o comentário "se o HLM step-up existir, ele é a fonte dos KPIs". Eu
tinha lido a linha do `read_csv` e parado antes da substituição.

Por isso o documento mostra −7,0% de ponta a ponta, do step-up, e o −6,21% da
série completa não aparece em lugar nenhum — o que, aliás, eu havia verificado e
registrado na versão anterior deste laudo.

**O que sobrou de real, e foi feito:** o fallback era silencioso. Se
`gap_decomposicao_stepup.csv` sumisse, os números trocariam de especificação sem
aviso nenhum (M4 de −7,0% para −6,2%). O gerador passa a avisar em voz alta
nesse caso, dizendo qual script rodar.

Os três csv continuam com rótulos iguais para modelos diferentes
(`M1_Individual` é o agregado num, o de intercepto aleatório no outro). Renomear
mexeria em vários scripts às vésperas da entrega; fica anotado.


### P6. Dois números escritos à mão num entregável — ❌ ACHADO ERRADO MEU

**Retificação.** Escrevi que dois hardcodes estavam em `gerar_guia_estudo.py`,
"que produz `TCC_Ricardo_Calheiros_Guia_de_Estudo.docx`". Errado: há dois
arquivos com esse nome em pastas diferentes. Os valores digitados estão em
`scripts/geradores/gerar_guia_estudo.py`, que traz no cabeçalho "SUPERADO ---
não usar na entrega final" e gera `guia_estudo_defesa.docx`, arquivo que não
existe em `entregaveis/`. O guia entregue vem de
`tcc/scripts/gerar_guia_estudo.py`, que lê tudo de `params_nucleo`.

**Os hardcodes estão todos em geradores superados. Nenhum toca a entrega.**

O que foi feito no lugar, porque era o problema real: o validador contava esses
valores como erro, e por isso seu veredito era "FALHOU" em **toda** execução ---
um validador que sempre falha deixa de ser lido. Ele passou a detectar o
marcador `SUPERADO` no cabeçalho do gerador e a reportá-los como nota
informativa, fora da contagem. Um hardcode novo, num gerador vivo, volta a ser
visível.

Resultado da primeira execução depois da mudança:
`STATUS: ✓ CONSISTENTE — 0 divergências, 0 hardcodes críticos`.


---

## ✅ VERIFICADO E ÍNTEGRO

| Verificação | Resultado |
|---|---|
| Cadeia de geração idempotente | regerar do zero produz `.tex` idêntico |
| Números da prosa rastreados a csv | 216 de 217; o único sem fonte é "12.990", número de lei |
| Tabela SHAP × csv | 29/29 variáveis, 116 valores, **0 divergências** |
| Tabela de mediação | coerente: β → gap (e^β−1) → mediação acumulada, linha a linha |
| Tabela interseccional | dotações + retornos = 100% nos três grupos |
| Referências cruzadas | nenhuma quebrada; nenhum "??" no PDF |
| Citações | nenhuma indefinida no log do LaTeX |
| Figuras | 10 inclusões, todas presentes no disco |
| Rótulos órfãos | nenhum (o antigo `fig:shap_bee` saiu com a correção C2) |
| PDF × Word | o Word não tem nenhum número que o PDF não tenha |
| Anexos do manual | **26/26 conformes** |
| `verificar_analises.py` | **0 ALTO**, 0 MÉDIO, 0 BAIXO, 2 INFO conhecidos |
| Identidades de decomposição (Oaxaca) | soma das partes = total, nas duas especificações |
| Sobreajuste do ML | gap treino–teste de 0,0015 (RF) e 0,0090 (XGB) |
| Páginas | 34, contra o limite de 50 |

Os 2 INFO do verificador são conhecidos e já tratados no texto: *bad control* da
Oaxaca (MHE-25, discutido nas limitações) e ausência de peso amostral
(declarada).

### Falsos positivos que investiguei e descartei

- **`pericia_cruzada.py` acusa termo de interação órfão no RIF e no OB4.** Os
  arquivos com o problema (`rif_ob_decomposicao.csv` coluna `inter`,
  `interseccional_ob4grupos.csv`) guardam a decomposição *threefold*; o documento
  usa a *two-fold*, que fecha. O laudo antigo auditava o csv que não é usado.
- **LRT = −inf** na tabela de *random slope*: valor degenerado real, mas naquela
  tabela do escopo estendido — não entra no entregável.
- **95 "decimais com ponto" no PDF**: 76 eram separadores de milhar (7.694.198),
  corretos em pt-BR.

---

## Recomendação

O defeito que bloqueava a entrega (C1) está corrigido e o entregável foi
regerado: 34 páginas, 26/26 nos anexos, Resumo e Abstract íntegros. Dos
pendentes, **P1 e P2 são os que a banca enxerga** — uma tabela em formato inglês
com `p = 1.84e-64`, e duas equações invadindo a margem. Ambos são correções de
forma, de baixo risco, e eu as faria antes de entregar. P3 é o único com risco de
leitura errada de um número. P4, P5 e P6 podem esperar.
