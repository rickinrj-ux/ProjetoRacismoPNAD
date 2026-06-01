# CHANGELOG — TCC Racismo e Mercado de Trabalho (PNAD Contínua)
**Projeto:** Desigualdade Racial no Mercado de Trabalho Brasileiro  
**Autor:** Ricardo Calheiros  
**Modelo principal de IA:** Claude (Anthropic) — claude-sonnet-4-6  
**Repositório:** ProjetoRacismoPNAD (Git local → GitHub)

---

## Controle de versão e prompts realizados

> Formato: `## vX.Y — DATA` → seções de alterações + prompts originais do usuário

---

## v1.0 — Fundação do projeto

### Estrutura inicial
- Ingestão da PNAD Contínua 2016–2025 via microdados IBGE
- Pipeline de feature engineering: `run_features.py`
- Modelos base: OLS, HLM 3 níveis, KMeans k=3

---

## v2.0 — Análises exploratórias

### Modelos adicionados
- GLMM logístico via lme4 (R): glass ceiling ocupacional
- Decomposição Oaxaca-Blinder expandida (OB 4 grupos, OB por sexo)
- Análise de Redes Sociais (SNA) inicial: 10 nós (raça × educação)
- Regressão quantílica com KB test (Khmaladze-Bierens)
- SHAP values via XGBoost

---

## v3.0 — Pesquisa Operacional integrada

### Novos scripts
- `run_po_topsis.py` — ranking TOPSIS de 6 políticas públicas
- `run_po_pl1.py` — Programação Linear (orçamento × redução de gap)

### Resultados PO
- P1 (Cotas CBO 1–4): CC=0,8344
- P2 (Equidade educacional): CC=0,5879
- P3 (Mentoria redes): CC=0,3962
- P4 (Transparência salarial): CC=0,3422
- P5 (Enforcement): CC=0,2753
- P6 (Desegregação residencial): CC=0,0805
- PL-1 com B=R$5bi: redução de gap = 25,1%

### Geradores de documento atualizados
- `gerar_relatorio_tcc.py` — LaTeX com PO no título, resumo, conclusão
- `gerar_relatorio_word.py` — Word com PO em 7 seções
- `gerar_apresentacao_pptx.py` — Slide de PO

---

## v4.0 — Revisão técnica e correções críticas (2026-05-28)

### Prompt do usuário
> "recebi esses feedbacks sobre o projeto: avalie e implemente as melhorias: [lista completa de 🔴🟡🟢]"

### 🔴 Correções críticas implementadas
1. **Fórmula ICC HLM incompleta** — expandida para 3 níveis completos
   `ρ_UF = τ²_UF / (τ²_UF + τ²_UPA + σ²)` com nota sobre τ²_UPA via slopes fixos
2. **z-scores boundary test todos iguais a 3,61** — corrigidos individualmente:
   M0=3,61; M1=2,36; M2=3,22; M3=2,19 (calculados via P[] keys)
3. **LRT values da subamostra 20%** — corrigidos para população completa:
   M0→M1: 3.084.078; M1→M2: 402.947; M2→M3: 3,3 (p=0,345); M3→M4: 1.927.425
4. **M4 ausente na tabela HLM** — adicionado; lógica de leitura de colunas dinâmica
5. **KB test tabela mostrando "—"** — mapeamento de colunas corrigido via `_kb()` helper
6. **Cluster 0 descrição ambígua** — corrigido para "exclusivamente feminino, 76,2% negras"
7. **Heckman interpretação invertida** — gap corrigido (-7,41%) < não-corrigido (-9,71%) = HLM superestima
8. **RIF-OB vs QR contradição aparente** — parágrafo de reconciliação adicionado
9. **Formalização DID parallel trends** — limitação explícita adicionada (seção 4.14)
10. **PO não aparecia no resumo/título** — adicionado em 7 seções de ambos os geradores

### 🟡 Moderados corrigidos
1. Justificativa de efeitos fixos: de "número elevado de UFs" para justificativa computacional correta
2. Explicação do LRT M2→M3 (p=0,345): τ²_UPA absorvida via slopes é comportamento esperado do HLM
3. SNA: limitação de 10 nós documentada explicitamente

### 🟢 Melhorias planejadas (implementadas em v4.1)
1. VIF/multicolinearidade para CBO × formalidade
2. Davies-Bouldin formal k=2 vs k=3
3. ICs bootstrap para segregação espacial

---

## v4.1 — Análises complementares e SNA expandida (2026-05-30)

### Prompt do usuário
> "reprocesse os dados e implemente as 3 oportunidades de melhoria não abordadas. Siga o pipeline após o reprocessamento: Mudança códigos --> word --> pptx --> push Github. Crie um controle de versionamento e alterações e prompts realizados durante todo o projeto para estudo futuro. Expanda o SNA de forma que ele deixe de ser uma limitação"

### Novos scripts criados
- `run_vif_multicolinearidade.py` — VIF para 23 preditores do M4 (N=200k subsample)
- `run_segregacao_ci.py` — Bootstrap IC 95% do gap por área (1.000 replicações)
- `run_sna_expandido.py` — SNA expandida para 20 nós (raça × educação × gênero)

### Resultados das novas análises

#### VIF (Multicolinearidade M4)
- N preditores: 23
- VIF máximo: 2,09 (CBO: Serviços/Vendas)
- Crítico (>10): 0 variáveis
- Alto (5–10): 0 variáveis
- Moderado (2–5): 1 variável
- Baixo (<2): 22 variáveis
- **Conclusão:** sem multicolinearidade problemática

#### Davies-Bouldin (k=2 vs k=3)
- k=2: Silhouette=0,1736, DB=2,0140
- k=3: Silhouette=0,1401, DB=2,2814
- **Conclusão:** k=2 melhor em ambas as métricas automáticas, mas k=3 adotado por interpretabilidade substantiva (clivagem racial não discrimina segmentos ocupacionais internos)

#### SNA Expandida (20 nós: raça × educação × gênero)
- Nó de maior betweenness: Branco_Fundamental_Fem (B=0,7836)
- Grupos negros (todos os níveis, ambos gêneros): betweenness = 0
- Constraint máximo: 4,014 (grupos sem instrução)
- Gap renda Branco_Masc vs Negro_Fem (log): Branco_Masc=7,226 vs Negro_Fem=6,578 (Δ=0,648)
- **Conclusão:** confirma H5 com maior robustez; posição de brokerage exclusivamente branca e feminina de escolaridade fundamental

#### Bootstrap CI Segregação Espacial (N=771.756, 1.000 replicações)
- Capital: −38,6% [IC 95%: −39,2%; −38,1%], negros ganham 38,6% menos que brancos
- Interior: −36,4% [IC 95%: −36,7%; −36,1%]
- RM (exceto capital): −28,1% [IC 95%: −28,8%; −27,4%]
- Teste permutação Capital vs. Interior: p < 0,001 (diferença não atribuível ao acaso)

### params.py — Novas chaves adicionadas
```
VIF_MAX, VIF_MAX_VAR, VIF_N_CRITICO, VIF_N_ALTO, VIF_N_MODERADO, VIF_N_BAIXO, VIF_N_TOTAL
SNA_EXP_N_NOS, SNA_EXP_BETWN_TOP, SNA_EXP_BETWN_TOP_NODE, SNA_EXP_CONSTR_MAX, SNA_EXP_CONSTR_MIN
SNA_EXP_GAP_RENDA_LOG, SNA_EXP_BRANCO_FEM_BETWN, SNA_EXP_NEGRO_FEM_RENDA, SNA_EXP_BRANCO_MASC_RENDA
SEGR_CAP_GAP_PCT, SEGR_CAP_CI_LO, SEGR_CAP_CI_HI
SEGR_RM_GAP_PCT, SEGR_RM_CI_LO, SEGR_RM_CI_HI
SEGR_INT_GAP_PCT, SEGR_INT_CI_LO, SEGR_INT_CI_HI, SEGR_P_PERM
KM_DB_K2, KM_DB_K3, KM_DB_K5
```

### gerar_relatorio_word.py — Seções atualizadas
- 3.4 Clustering: DB values (k=2 e k=3) adicionados à metodologia
- 3.6 SNA: substituída descrição de limitação pela rede expandida de 20 nós
- 3.8 Segregação Espacial: bootstrap IC adicionado à metodologia
- 3.11 Justificação: parágrafo VIF com tabela de resultados
- 4.2 Clustering: comparação DB formal k=2 vs k=3
- 4.4 SNA: resultados expandidos com dimensão de gênero
- Seção Segregação (resultados): valores bootstrap com IC 95% e p-value permutação
- Figura 19b adicionada (bootstrap CI por área)
- Figura A7 adicionada (VIF M4)

---

## v4.2 — Revisão editorial e narrativa (2026-05-30)

### Prompt do usuário
> "Avalie esses feedbacks, faça as alterações seguindo o pipeline e demonstre o que foi alterado: [revisão editorial completa com 🟢/🔴/🟡 — excesso de densidade, sem hierarquia narrativa, Discussão sem contraste com literatura, Conclusão sem impacto, Metodologia superengenheirada, risco na banca, melhorias prioritárias: enxugar Resultados, reescrever Conclusão, mover detalhes técnicos para apêndice, criar narrativa única 'sistema de barreiras em camadas']"

### Mudanças editoriais implementadas

#### gerar_relatorio_word.py
1. **Tese Central (6 barreiras)** — adicionada antes da seção 4.0 Descritiva:
   - Barreira de acesso (OR GLMM), salarial intra-ocupação (gap M4), progressão glass ceiling (KB-test),
     contextual (mediação UPA), rede (betweenness nulo negros), persistência temporal (1 século)
2. **Seção 3.3 nota executiva** — parágrafo apontando ao apêndice para leitores interessados apenas nos resultados substantivos
3. **Síntese/Discussão** — novo parágrafo de contraste com literatura: Hasenbalg (1979), Henriques (2001), Soares (2009); contribuição: decomposição da "caixa preta" dos 50% inexplicados em mecanismos específicos
4. **Conclusão reescrita** — 4 frases de abertura em negrito (teses centrais), síntese empírica, PO, Contribuição atualizada referenciando Hasenbalg (1979)

#### gerar_relatorio_tcc.py
1. **Tese central no Resultados** — parágrafo de 5 itens (barreiras i–v) antes dos resultados HLM
2. **Discussão** — `\paragraph{O que este trabalho acrescenta ao debate.}` com citações Hasenbalg/Henriques/Soares; decomposição explícita dos 50% de Soares (2009)
3. **Conclusão** — reescrita com `\begin{quote}\textit{...}\end{quote}` para 4 frases impactantes, síntese empírica, PO, Contribuição principal atualizada

#### Bug fix
- `extract_kpis()`: adicionadas chaves `gap_m4` (M4_Ocupacao, Gap%=-6.24%) e `med_occ` (Mediacao_occ%=17.55%) que estavam ausentes

### Justificativa das mudanças narrativas
- Banca cobra clareza: um mapa das conclusões antes dos resultados permite ao examinador acompanhar o argumento central
- Literatura: comparação explícita com Hasenbalg/Soares posiciona contribuição vs. state-of-the-art
- Conclusão com frases-tese em negrito facilita a síntese do trabalho em apresentação oral

---

## v4.3 — Narrativa de 3 Barreiras: reestruturação editorial completa (2026-05-31)

### Prompt do usuário
> "Avalie e implemente as sugestões: [6 pontos de feedback — overengineering acadêmico, tese diluída, storytelling mecanicista, macro-coesão deficiente, conclusão técnica, PO como anexo enxertado. Plano de ação: desidratação técnica, reestruturação por mecanismo, conclusão executiva, bridge narrativa PO]"

### Mudanças implementadas

#### gerar_relatorio_word.py — 6 mudanças estruturais
1. **Tese agressiva na Introdução** — 2 parágrafos em bold ANTES do contexto histórico:
   - "Este trabalho comprova que o racismo não opera como evento isolado — opera como sistema de barreiras em camadas..."
   - "A evidência emerge de 15,9 milhões de observações com 4 paradigmas complementares..."
2. **Roadmap de 3 Barreiras** (substitui lista de 6 bullets da Tese Central):
   - Tabela 0 com 3 linhas: Barreira I/II/III, pergunta central e evidência
   - Prose de orientação antes e depois da tabela
3. **BARREIRA I** — header em bold antes da seção HLM + parágrafo de orientação: "Esta seção documenta como o território amplifica o gap racial"
4. **BARREIRA II** — header em bold antes da seção OB + bridge da Barreira I: "Estabelecido como a exclusão se origina... qual é o preço residual?"
5. **BARREIRA III** — header em bold antes da seção SNA + bridge: "Por que trabalhadores negros com pós-graduação ainda não chegam ao topo?"
6. **Bridge da PO** — 2 parágrafos antes da seção PO: "diagnóstico multicausal implica política multi-dimensional... PO fecha o ciclo diagnóstico-prescritivo"
7. **Conclusão Executive** — 3 parágrafos narrativos SEM números e SEM siglas de modelo:
   - P1: meritocracia falha + engrenagem de múltiplas camadas
   - P2: terceira barreira mais desafiadora (educação ≠ mobilidade)
   - P3: urgência (> 1 século de convergência = reformas incrementais insuficientes)
8. **GLMM** — parágrafo de orientação: "Barreira I em profundidade: quantifica o odds de um negro sequer chegar..."
9. **OB** — parágrafo de orientação: "Esta análise responde: quanto do gap é discriminação pura?"

#### gerar_relatorio_tcc.py — 6 mudanças LaTeX
1. **Introdução** — \begin{quote}\textbf{...}\end{quote} com tese central declarada agressivamente
2. **Resultados** — tabela \tabularx de 3 barreiras como guia de leitura
3. **BARREIRA I** — \noindent\rule + bold header antes de HLM + \textit{orientação}
4. **BARREIRA II** — \noindent\rule + bold header antes de Clustering + \textit{bridge da Barreira I}
5. **BARREIRA III** — \noindent\rule + bold header antes de SNA + \textit{orientação}
6. **Discussão → "Discussão e Prescrição"** — \paragraph{Da diagnose à prescrição.} bridge PO
7. **Conclusão** — 3 parágrafos narrativos SEM números antes das frases-tese em \begin{quote}

#### Bug fix adicional
- extract_kpis(): adicionadas med_upa e med_occ como chaves explícitas (referenciadas no Discussão)

### O que NÃO foi alterado (decisão deliberada)
- Ordem das seções: mantida (risco alto de quebrar pipeline de 3500+ linhas)
- Detalhamento técnico das seções: mantido (detalhe técnico necessário para banca especializada)
- AIC/LRT tables: mantidas (já existem no Anexo B; remover do corpo criaria referências órfãs)
- A "desidratação técnica" foi parcialmente endereçada: barriers headers + orientation paragraphs
  criam hierarquia informacional que permite ao leitor navegar e pular detalhes técnicos

---

## Nota técnica sobre escolhas metodológicas

### Por que não usar Zero-Inflated Models?
Zero-inflated é para contagens com excesso de zeros estruturais (Poisson/NegBin). 
O desfecho é log-renda contínua; zeros tratados via filtro renda>0. 
O problema de seleção amostral é tratado via Heckman (análogo para desfechos contínuos).

### Por que o gap de segregação mudou de positivo para negativo?
Versões anteriores expressavam o gap como "brancos ganham X% a mais que negros" (positivo).
A partir de v4.1, o bootstrap usa a convenção negro − branco (negativo), que é mais direta
e menos propensa a erros de interpretação. Os valores são matematicamente equivalentes:
Capital −38,6% (negros ganham menos) ↔ +62,8% (brancos ganham mais: 1/0,614−1).

---

*Gerado automaticamente por controle de versão do projeto TCC.*
