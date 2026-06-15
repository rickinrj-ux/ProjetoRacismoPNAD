# Escopo do TCC — Decisão de Priorização Metodológica

**Data:** 2026-06-15
**Contexto:** resposta ao feedback do orientador (jun/2026).

---

## Feedback do orientador (registro literal)

> "achei seu escopo muito amplo, são muitos métodos. verifique se realmente é necessário
> todos, ou se deve priorizar algum. os resultados, se vc tb colocar em tabelas, facilitaria
> a leitura, além das figuras. A frase 'renda média do bairro é o principal determinante' me
> parece um pouco forte para essa etapa. pode verificar? Mas o mais crítico que vejo é a
> questão dos métodos."

---

## Diagnóstico

O trabalho carregava ~18 técnicas distintas no corpo. O problema não era técnico (cada peça
funciona) e sim **estratégico**: amplitude diluía a mensagem central, multiplicava flancos de
defesa na banca e sinalizava coleção de métodos em vez de desenho de pesquisa.

## Decisão: NÚCLEO DE 4 + ROBUSTEZ

Pergunta central do TCC: *depois de controlar capital humano, ocupação e geografia, persiste
penalidade racial? E ela se concentra no acesso/topo?* Quatro métodos respondem isso de
ângulos não-redundantes (ver `MANIFESTO_METODOS.md`):

1. **HLM 3 níveis** — quanto do gap sobrevive e onde nasce.
2. **Oaxaca-Blinder** — composição vs. discriminação.
3. **Regressão quantílica (+RIF-OB)** — teto de vidro / sticky floor.
4. **GLMM logístico** — gap de acesso a cargo qualificado/topo.

Robustez (apêndice enxuto): ML/SHAP + um par de testes de sensibilidade (E-value + Konfound)
+ interseccional OB-4-grupos. Tudo o mais → parqueado na versão estendida.

## Resposta aos três pontos do orientador

| Ponto | Ação |
|-------|------|
| **(crítico) Muitos métodos** | Núcleo de 4 + 6 de robustez; ~20 técnicas parqueadas em `mestrado-extenso`. |
| **Resultados em tabelas** | Maioria já existia como `.tex` (`ob_decomposicao`, `qr_melhorias`, `rif_ob_decomposicao`, `evalues_glmm`, `hlm_*`). Gerada a tabela-síntese do GLMM (`glmm_glassceil.tex`, via `tcc/scripts/gerar_tabela_glmm.py`) e **inseridas** todas no `relatorio_tcc_enxuto.tex` via `\input`, junto às figuras. |
| **Frase "principal determinante"** | Corrigida — ver abaixo. |

## A frase "renda média do bairro é o principal determinante"

O orientador está certo, e o problema é maior que estilo. Dois defeitos:

1. **Inconsistência interna.** A afirmação vem de um SHAP antigo (modelo sem variáveis
   ocupacionais). No ranking SHAP final (roteiro da banca, Slide 10) os principais preditores
   são *horas trabalhadas → CBO → emprego formal*; `media_renda_upa` **não** é o topo.
2. **Quase tautológico (problema do reflexo, Manski 1993).** Prever a renda *individual* a
   partir da renda *média da própria UPA* — que inclui o indivíduo — é mecanicamente circular.
   "O bairro prediz mais que o diploma" infla artefato de especificação em achado substantivo.

**Reformulação adotada:** de *"é o principal determinante"* para *"o contexto territorial (UPA)
media parcela substancial do gap — mais da metade no HLM —, indicando que a segregação
residencial é um canal relevante da desigualdade racial."* Afirma **mediação** (sustentada pelo
HLM), não determinância causal (não sustentada pelo SHAP).

Arquivos corrigidos no `master`:
- `scripts/geradores/gerar_resultados_preliminares.py`
- `scripts/geradores/gerar_apresentacao_executiva.py`

> A versão estendida (`mestrado-extenso`) mantém o texto original; se quiser propagar a
> correção para lá, faça `git cherry-pick` do commit correspondente.

## O que NÃO se perde

A versão extensa permanece íntegra no branch **`mestrado-extenso`** (GitHub), pronta para
servir de base a um artigo ou dissertação de mestrado. Nenhum script, tabela ou figura foi
apagado.
