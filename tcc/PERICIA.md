# Laudo de Perícia — Consistência do Trabalho (núcleo de 4)

**Data:** 2026-06-15 · **Escopo:** auditoria de todos os entregáveis e tabelas contra a
nova narrativa (núcleo de 4 métodos). Severidade: 🔴 crítico · 🟠 alto · 🟡 médio · ⚪ baixo.

> Regra do perito: **não se gera entregável final sobre número ainda em disputa.** Os achados
> 🔴 abaixo bloqueiam a regeração dos entregáveis dependentes (pptx, guia, roteiro) até decisão.

---

## 🔴 F1 — Decomposição Oaxaca: a divergência é de ESPECIFICAÇÃO (ocupação), não de amostra — RESOLVIDO

**Diagnóstico inicial (errado) e correção.** Primeiro atribuí a divergência à educação ausente
(`educ_missing`). **Um teste controlado (`tcc/scripts/teste_oaxaca_educ_conhecida.py`) refutou
isso.** A causa real é a **inclusão (ou não) de ocupação e contexto de UPA** na decomposição:

| Especificação | Dotações | Discrim. | Observação |
|---|---|---|---|
| Mincer puro + `C(Ano)` (tabela estendida `ob_decomposicao`) | **24,8%** | 75,2% | sem ocupação nem contexto |
| Educ conhecida, sem ocupação (C3) | 70,6% | 29,4% | + contexto de UPA |
| Educ conhecida + ocupação (C2) | 79,5% | 20,5% | |
| **Pop. completa + ocupação + contexto (C1 = TCC)** | **83,1%** | 16,1% | bate com o "84%" |

Educação conhecida vs completa quase não muda (83,1% → 79,5%). O que move o número de 24,8% para
83% é **tratar ocupação e território como dotações** — exatamente o que a narrativa do trabalho
assume ("o gap é majoritariamente ACESSO a ocupações"). Logo o **"84%" estava correto** (≈83,1%);
a tabela `ob_decomposicao.tex` é que usava um Mincer puro, divergente da narrativa (além do bug do
intercepto, já sanado).

**Resolução adotada:** gerada a tabela `ob_acesso.tex` (`tcc/scripts/gerar_tabela_oaxaca.py`) com a
especificação de acesso (ocupação + contexto, pop. completa) → ~83% dotações / ~16% discriminação.
O relatório enxuto passa a usá-la (label `tab:oaxaca_blinder`). A `ob_decomposicao.tex` (Mincer,
24,8%) permanece para a versão de mestrado como análise alternativa.

**Ressalva (registrada na caption):** incluir ocupação como dotação *subestima* a discriminação
total (Oaxaca & Ransom, 1999), pois a segregação ocupacional é discriminatória — daí a
complementaridade com o GLMM de acesso. A narrativa em dois passos (gap = composição; composição =
produto de discriminação no acesso, via GLMM; discriminação intra-ocupação = sticky floor, via RIF)
permanece válida e **vindicada**.

---

## 🔴 F2 — Entregáveis ainda na narrativa ESTENDIDA (não-núcleo)

`gerar_apresentacao_pptx.py`, `gerar_apresentacao_executiva_pptx.py` e `gerar_guia_estudo.py`
estão inteiramente na narrativa antiga: SNA ("triângulo", betweenness), K-Means (3 clusters),
TOPSIS/Pesquisa Operacional, PO regional, e o "84% de acesso". Para refletir o núcleo de 4
precisam ser **reescritos** (ou parqueados para a versão de mestrado). Bloqueado por F1 (o
número de Oaxaca aparece dezenas de vezes nesses arquivos).

---

## 🟠 F3 — "renda média da UPA é o preditor mais importante" sobrevive no relatório

Suavizei essa afirmação (problema do reflexo, Manski 1993) em `gerar_resultados_preliminares.py`
e `gerar_apresentacao_executiva.py`, mas **não** no gerador principal `gerar_relatorio_tcc.py`
(linhas 637 e 1267) — então ela reaparece no `relatorio_tcc_enxuto.tex` (linha 652).
**Ação:** neutralizar via pós-processador (mantém o gerador completo intacto p/ mestrado).

---

## 🟡 F4 — Magnitudes de gap usadas sem rótulo claro

Coexistem, para "o gap": **53%** (bruto, `GAP_PCT`), **19,1%** (condicional a educ/sexo/idade,
HLM M2), **37%** (mediana, roteiro), **42,3%** (roteiro, base Oaxaca). Não são contraditórios
*per se* (medidas distintas), mas são usados de forma intercambiável. **Ação:** padronizar
rótulos — "gap bruto (53%)" vs "gap condicional (19,1%)" vs "gap residual (9,6%)".

---

## 🟡 F5 — GLMM: odds ratio citado com valores divergentes

Roteiro da banca: OR=0,741 (ocp) e 0,704. Tabela/params atuais (população completa):
OR_ocp_qualif **0,705** (M2), top20 0,691, top10 0,656; acesso geral 0,693. O **0,741 do roteiro
está desatualizado** (provável estimativa amostral antiga). **Ação:** alinhar roteiro à tabela
`glmm_glassceil.tex`.

---

## 🟡 F6 — Roteiro da banca (`docs/roteiro_apresentacao_banca.md`) na narrativa de 5+ métodos

Apresenta "cinco metodologias", SNA, Hipóteses do Estado (Anexo A) e PO. Slide 7 traz Oaxaca
84/16. Precisa ser reescrito para o núcleo de 4 + robustez e para o Oaxaca decidido (F1).
Bloqueado por F1.

---

## ⚪ F7 — "Mediação" com duas definições

Roteiro: mediação total 74,4% (M1→M4, inclui ocupação). Resumo: 52,5% mediado pelo contexto
(M2→M3, só UPA). São mediações **diferentes** — rotular como "mediação total (74,4%)" vs
"mediação contextual (52,5%)".

---

## ⚪ F8 — Ressalva de identificação do Oaxaca (registrar no texto)

Na decomposição com dummies, a partição do não-explicado entre intercepto e coeficientes
individuais **não é invariante** à categoria de referência (Oaxaca & Ransom 1999; Jann 2008).
Apenas o **agregado** não-explicado é invariante. Não interpretar a contribuição por-variável do
componente de coeficiente.

---

---

# Perícia Cruzada — auditoria numérica de tabelas/figuras/código

Executada por `tcc/scripts/pericia_cruzada.py` (identidades de decomposição em valor
absoluto + consistência params↔tabelas). Resultado bruto em `tcc/pericia_cruzada_resultado.txt`.

## 🟠 FC1 — Coluna "Interação" da RIF-OB é DUPLA CONTAGEM (estava exibida no relatório)

`src/rif_decomp.py:144-147`: com referência $\beta_{branco}$, `end = (\bar x_b-\bar x_n)\beta_b`
já contém a interação ($end = E_3 + I_3$), e `end + ret = gap`. O código ainda calcula
`inter = (\bar x_b-\bar x_n)(\beta_b-\beta_n)` e o exibe como coluna própria → **dupla
contagem**: Dotações% + Retornos% + Interação% **não somam 100%** (q10: 61,3+33,1−31,2=63,2%).
A `rif_ob_decomposicao.tex` (com essa coluna) estava **inserida no relatório**.
**Corrigido:** `tcc/scripts/corrigir_tabela_rif.py` gera `rif_decomp_tcc.tex` em twofold
consistente (Dotações+Retornos=100% sobre `gap_rif`); relatório repontado. Sticky floor
preservado (Retornos 35,1%→12,9% do q10 ao q90).

## 🟡 FC2 — Mesmo padrão em `interseccional_ob4grupos.csv` (não exibido no relatório)

Homem Negro e Mulher Negra: `end+ret=gap` mas `inter`≠0 órfão → end%+ret%+inter% = 75,6% e
96,1% (não 100%). Os entregáveis citam só end/ret (71/29 etc.), que estão certos; a coluna
`inter` do CSV é que é espúria. **Ação:** mesmo conserto do FC1 se a tabela for exibida; senão,
remover a coluna `inter` na origem. Não bloqueia o TCC (tabela não entra no relatório enxuto).

## 🟡 FC3 — `hlm_nakagawa_r2`: M4 com `LRT_vs_prev = -inf`, `p = 1.0` (degenerado)

O teste de razão de verossimilhança do M4 (random slope) está degenerado. M4/random slope é
escopo ESTENDIDO (parqueado), então não afeta o núcleo; mas a tabela não deve ser citada como
"M4 melhora significativamente" sem recomputar o LRT. **Ação:** flag para o mestrado.

## 🟡 FC4 — Dois `gap_decomposicao` com M1 divergente

`gap_decomposicao.csv` (M1 = −10,79%) vs `gap_decomposicao_serie_completo.csv` (M1 = −19,13%):
períodos/amostras distintos (2021–2024 vs 2016–2025). O núcleo usa o serie_completo (19,1%,
consistente com o resumo). **Ação:** garantir que nenhum entregável cite o −10,79% como gap do
TCC; rotular explicitamente o período de cada um.

## 🟠 FC6 — `evalues_glmm.tex` STALE + hazard de LaTeX (removida do relatório)

Dois problemas: (1) o OR exibido (ocp M2 = **0,7405**) é a estimativa amostral antiga (= o
0,741 do roteiro), inconsistente com a populacional `glmm_glassceil_full` (**0,7046**); o `.tex`
e o `.csv` de evalues nem entre si batem. (2) Células com underscore cru (`ocp_qualif`,
`y_top20`) **quebrariam o LaTeX** (o relatório não carrega pacote `underscore`).
**Ação:** removida a inserção de `evalues_glmm.tex`; a `glmm_glassceil.tex` já traz coluna de
E-value (coerente com OR 0,705). Para o mestrado, regenerar `evalues` sobre a população.

## 🟡 FC7 — Tabelas com underscore cru não são "inputáveis"

`interseccional_coeficientes.tex` (23) e `evalues_glmm.tex` (10) têm underscores crus em modo
texto. O relatório usa rótulos legíveis nas tabelas inline e **não** carrega `underscore`/
`siunitx`. **Ação:** as tabelas do núcleo geradas em `tcc/scripts/` usam rótulos legíveis (sem
hazard); a interseccional foi reescrita limpa (`ob_interseccional_tcc.tex`, twofold correto).

## ✅ FC5 — Consistências que PASSARAM
- `params.py` ↔ `glmm_glassceil_full`: todos os OR (ocp 0,705; top20 0,691; top10 0,656; M1
  0,555) batem exatamente.
- `params[GAP_PCT]=53,0` ↔ `ob` gap 53,6% (ok).
- ML sem overfit: RF R²=0,57 e XGB R²=0,62, gap treino-teste 0,0006.
- `ob_decomposicao` (Mincer) e `ob_acesso` (acesso): identidade dotação+coef==gap fecha nas duas.

## Resolução de F1 (Oaxaca) — confirmada empiricamente
Re-run com especificação de acesso (`ob_acesso.tex`): **dotações 83,8% / discriminação 16,2%**
(gap +0,4255), reproduzindo o "84%" original. Narrativa vindicada; resumo cita 83,8/16,2.

---

## Itens JÁ corrigidos nesta perícia
- Bug do intercepto no Oaxaca (identidade agora fecha) — commit `2f6b44d`/`c7af186`.
- Resumo/abstract: revertido o headline 24,8/75,2 (F1) para formulação qualitativa + RIF.
- "preditor mais importante" no relatório enxuto: neutralizado via pós-processador (F3).

## Bloqueio para "gerar todos os entregáveis"
F1 (número de Oaxaca) e F2/F6 (reescrita pptx/guia/roteiro p/ núcleo) dependem da decisão em F1.
Resolvido F1, a regeração dos entregáveis é direta.
