# Laudo de Perícia — Consistência do Trabalho (núcleo de 4)

**Data:** 2026-06-15 · **Escopo:** auditoria de todos os entregáveis e tabelas contra a
nova narrativa (núcleo de 4 métodos). Severidade: 🔴 crítico · 🟠 alto · 🟡 médio · ⚪ baixo.

> Regra do perito: **não se gera entregável final sobre número ainda em disputa.** Os achados
> 🔴 abaixo bloqueiam a regeração dos entregáveis dependentes (pptx, guia, roteiro) até decisão.

---

## 🔴 F1 — Decomposição Oaxaca: três números conflitantes para "dotações vs discriminação"

| Fonte | Dotações | Discriminação | Amostra |
|---|---|---|---|
| `ob_decomposicao.tex` (agregado, corrigido) | **24,8%** | 75,2% | População completa **+ `educ_missing`** |
| `rif_ob_decomposicao.csv` (RIF por quantil) | **57–77%** | 11–33% | Só **educação conhecida** (`dropna`, ~31% da PEA) |
| Hardcoded nos pptx/guia ("84%") | **84%** | 16% | sem respaldo em tabela atual |

**Causa raiz:** amostras diferentes. O RIF (`src/rif_decomp.py:73`) faz `dropna` nas dummies de
educação → usa só os ~31% com escolaridade registrada, onde a educação entra corretamente como
dotação → dotações dominam. O Oaxaca agregado (`src/analise_retornos_raciais.py`) usa a população
completa com a dummy `educ_missing` (educação desconhecida para ~69%); como a educação não pode
ser atribuída, seu poder explicativo "vaza" para o componente **não-explicado**, inflando a
"discriminação" para 75,2%. O "84%" é um literal antigo, sem origem rastreável nos dados atuais
(não há `OB_PCT_DOTACAO` em `params.py`).

**Consequência:** o número **24,8/75,2 NÃO deve ser headline** — não é um "limite inferior da
discriminação" limpo, pois está contaminado por educação não medida. (Já revertido do resumo.)

**Decisão necessária (ver pergunta ao final):** qual decomposição é canônica?
- (a) OB na subamostra de **educação conhecida** (consistente com o RIF; dotações dominam) — *recomendado*;
- (b) RIF-OB como decomposição oficial (robusta, por quantil, já na narrativa sticky-floor);
- (c) OB população completa (24,8/75,2) **com ressalva explícita** de educação não medida;
- (d) sem percentual agregado — só qualitativo + RIF por quantil.

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

## Itens JÁ corrigidos nesta perícia
- Bug do intercepto no Oaxaca (identidade agora fecha) — commit `2f6b44d`/`c7af186`.
- Resumo/abstract: revertido o headline 24,8/75,2 (F1) para formulação qualitativa + RIF.
- "preditor mais importante" no relatório enxuto: neutralizado via pós-processador (F3).

## Bloqueio para "gerar todos os entregáveis"
F1 (número de Oaxaca) e F2/F6 (reescrita pptx/guia/roteiro p/ núcleo) dependem da decisão em F1.
Resolvido F1, a regeração dos entregáveis é direta.
