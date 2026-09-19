---
name: revisao-livros
description: Revisa o TCC (relatório enxuto, tabelas, figuras, slides e scripts do núcleo de 4 métodos) contra os ensinamentos de quatro livros lidos na íntegra — Mostly Harmless Econometrics (Angrist & Pischke), Manual de Análise de Dados (Fávero & Belfiore), Storytelling com Dados (Knaflic) e a apostila Árvores/Ensembles (Alencar, USP/ESALQ). Use sempre que uma análise, tabela, figura, texto de resultado ou slide for alterado (o hook PostToolUse chama automaticamente), antes de regenerar o relatório, antes de commit de entregável, ou quando o usuário pedir "revise conforme os livros", "cheque a econometria", "está defensável na banca?".
---

# Revisão do TCC conforme os livros

Objetivo: nenhum resultado chega à banca contradizendo o que os quatro livros ensinam, e
nenhum número do relatório diverge da sua fonte (csv em `outputs/tables/`).

Escopo do TCC (tcc/ESCOPO_TCC.md): **núcleo de 4** — HLM, Oaxaca-Blinder, QR + RIF-OB, GLMM
logístico — mais robustez (XGBoost/SHAP, E-values/Konfound, OB interseccional, VIF, HLM vs OLS).
SNA, clustering, PO/TOPSIS, Heckman etc. estão parqueados no branch `mestrado-extenso` e
**não podem** aparecer como resultado no relatório enxuto.

## Passo 1 — Checagens mecânicas (sempre)

```
python .claude/skills/revisao-livros/scripts/verificar_analises.py
```

Gera `tcc/revisoes/verificacao_<data>.md` com achados ALTO/MÉDIO/BAIXO/INFO e o critério
violado. O script expande os `\input{}` do `.tex`, compara números do relatório com os csv
(ML, GLMM, QR, HLM, OB), procura métodos fora do núcleo, linguagem causal, ausência de
figuras por método, `SAMPLE_FRAC`, OLS sem `cov_type`, logit rotulado GLMM, hold-out sem CV,
pizza/3D, títulos de slide descritivos e lacunas de numeração. Falso positivo → ajustar o
padrão no script, não ignorar.

## Passo 2 — Revisão qualitativa (o que o script não vê)

Ler os três arquivos de critérios em `references/` (IDs MHE-xx, FAV-xx, SWD-xx, ML-xx; cada
item marcado `[TCC]` é um ponto de exposição conhecido). Para cada arquivo alterado, percorrer
só os critérios pertinentes:

| Alterou… | Critérios a percorrer |
|---|---|
| HLM (`run_hlm_*`, tab. HLM, subsec:hlm) | FAV-70…77 (step-up, ICC por nível, LR test, REML/ML, BLUPs), MHE-56 (RE vs FE), MHE-81/82 (Moulton, 27 UFs), MHE-13/24 (sequência curta→longa + OVB), MHE-42 (reflexo em médias de grupo) |
| Oaxaca-Blinder / RIF-OB | MHE-25 (bad controls: ocupação, formalidade, horas), MHE-23 (resíduo ≠ discriminação medida), MHE-73 (condicional vs incondicional), MHE-81/84 (bootstrap em blocos), FAV-91 (N, SE, IC) |
| Regressão quantílica | MHE-70…76 (location shift vs fanning-out; efeitos sobre distribuições, não indivíduos; bootstrap), FAV-37 |
| GLMM/logit | FAV-40…45 e FAV-77 (χ², OR+IC, AME, AUC/ROC, cutoff, Hosmer-Lemeshow, ICC = τ/(τ+π²/3), LR vs logit), MHE-31 (efeitos marginais/LPM), MHE-32 (condicionar em renda>0) |
| ML/SHAP | ML-01…09 (split, k-fold, hiperparâmetros, overfitting, métricas na unidade original), MHE-42 (`media_renda_upa` = reflexo), FAV-31 (R² não é causalidade) |
| Texto de resultados/discussão/conclusão | MHE-01/02/03/23/90 (FUQ, CIA, "seu melhor cético"), FAV-07, SWD-03/04/06/79 (Grande Ideia, história de 3 min, não esconder o que contradiz, frase-síntese única) |
| Figuras | SWD-10…20 (visual certo, base zero, sem pizza/3D/eixo duplo, cascata p/ OB), SWD-30…47 (saturação, cinza + 1 cor, Gestalt), SWD-54/55/56 (títulos de ação, anotações) |
| Slides | SWD-05/70…80 (storyboard, 3 atos, lógica horizontal e vertical, Bing-Bang-Bongo), SWD-55 (títulos de ação), SWD-93 (espaguete → pequenos múltiplos) |

Regras de julgamento:
1. **Fonte única**: todo número do texto tem de existir num csv de `outputs/tables/`. Número
   sem fonte é ALTO.
2. **Nunca amostrar** sem confirmação do usuário (regra do projeto). `SAMPLE_FRAC` numérico é ALTO.
3. **Bad control** (MHE-25): resultado "líquido de ocupação" só é aceitável ao lado da versão
   sem ocupação e nomeado como limite inferior descritivo; comparar com a literatura só na
   mesma especificação.
4. **Erro-padrão** (MHE-81): regressor que varia no nível do grupo (UPA/UF) exige SE
   clusterizado ou bootstrap em blocos; publicar só o SE do modelo de efeitos aleatórios de
   UF quando o cluster-UF é 15× maior é ALTO.
5. **Linguagem**: "comprova", "determina", "causa" só na seção de limitações (e negando).
   Preferir "associa-se", "é consistente com", "penalidade condicional a X".
6. **Storytelling**: cada método do núcleo tem uma figura com título de ação; a sequência de
   títulos dos slides conta a história sozinha; uma frase-síntese com um único número.

## Passo 3 — Relatório da revisão

Escrever `tcc/revisoes/revisao_<data>.md` (ou anexar ao arquivo do dia) com:
- tabela `Nível | Critério | Onde (arquivo:linha) | Achado | Correção proposta`, ALTO primeiro;
- o que foi corrigido na hora (edições pequenas: número desatualizado, palavra causal,
  título) e o que precisa de decisão do usuário (reestimar com cluster/pesos, mudar
  especificação, remover seção);
- no fim, a lista dos critérios verificados e considerados OK (para a banca).

Nunca alterar especificação de modelo, remover seções ou reestimar nada sem o usuário
confirmar; o hook e a skill levantam bandeiras, quem decide é o autor.

## Arquivos

- `references/criterios_mhe.md` — Angrist & Pischke, caps. 1–8 (MHE-01…90)
- `references/criterios_favero.md` — Fávero & Belfiore, caps. 1–18 (FAV-01…93)
- `references/criterios_swd_apostila.md` — Knaflic caps. 1–10 (SWD-01…96) + Alencar (ML-01…10)
- `scripts/verificar_analises.py` — checagens mecânicas (stdlib; roda em segundos)
- `scripts/hook_revisao.py` — hook PostToolUse (registrado em `.claude/settings.json`)
