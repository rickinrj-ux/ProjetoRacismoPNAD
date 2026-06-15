# Manifesto de Métodos — Classificação de Escopo

> Documento de governança metodológica. Define, para **cada método** do projeto, se ele
> entra no **corpo do TCC** (núcleo), na **seção de robustez** (apêndice enxuto) ou se fica
> **parqueado** para a versão estendida (artigo/mestrado).
>
> A versão estendida — com **todos** os métodos — está preservada no branch Git
> **`mestrado-extenso`** (`git checkout mestrado-extenso`). Nada foi apagado.
>
> Critério de classificação (decidido após feedback do orientador, jun/2026):
> *um método só entra no corpo do TCC se responde uma pergunta de pesquisa distinta e
> não-redundante. Se apenas confirma o que o núcleo já mostra, é robustez. Se responde
> outra pergunta, é estendido (fora do escopo do TCC).*

---

## TIER 1 — NÚCLEO (corpo do TCC)

Quatro métodos, cada um respondendo uma pergunta distinta. Esta é a espinha dorsal do TCC.

| # | Método | Pergunta que responde | Script(s) canônico(s) | Módulo `src/` | Tabela(s) `.tex` |
|---|--------|-----------------------|------------------------|----------------|-------------------|
| 1 | **HLM 3 níveis** | Quanto do gap salarial sobrevive aos controles e em que nível geográfico nasce? | `run_hlm_serie_completa.py`, `run_hlm_m4.py` | `multilevel_model.py` | `hlm_serie_completo.tex`, `hlm_m4.tex`, `hlm_coeficientes.tex`, `hlm_equacoes.tex` |
| 2 | **Oaxaca-Blinder** | Quanto do gap é composição (dotações) vs. retorno (discriminação)? | `run_oaxaca_blinder.py` | — | `ob_decomposicao.tex` |
| 3 | **Regressão quantílica (+RIF-OB)** | A penalidade muda ao longo da distribuição de renda? (teto de vidro / sticky floor) | `run_regressao_quantilica.py`, `run_rif_decomp.py` | `rif_decomp.py` | `qr_melhorias.tex`, `rif_ob_decomposicao.tex` (dados: `quantreg_negro.csv`) |
| 4 | **GLMM logístico** | Negros têm menor chance de acessar cargo qualificado / topo de renda? | `run_glmm_glassceil.py`, `run_logit_multinivel.py` | — | (gerar `glmm_resumo.tex` a partir de `glmm_resumo.csv` + `glmm_odds_ratios.csv`) |

**Apoio descritivo do núcleo** (entram como tabelas/figuras descritivas, não como "método"):
`run_composicao_ocupacional.py` (composição ocupacional por raça), estatísticas descritivas
(`tab1_descritiva_racial.csv`, `tab2_gap_bruto_subgrupos.csv`).

---

## TIER 2 — ROBUSTEZ (apêndice enxuto do TCC)

Não respondem perguntas novas: **confirmam** o núcleo por outra via. Vão para uma seção curta
de robustez. Escolha deliberada de **um** par de testes de sensibilidade (E-value + Konfound),
não os três (Oster fica parqueado).

| Método | Papel | Script | Tabela `.tex` |
|--------|-------|--------|----------------|
| **ML XGBoost + SHAP** | Valida o resíduo racial sem pressuposto de forma funcional | `run_ml_shap.py` | `shap_importance_comparada.csv` |
| **E-values (GLMM)** | Sensibilidade do OR a confundidor não-observado | `run_konfound_evalues.py` | `evalues_glmm.tex` |
| **Konfound (HLM)** | Sensibilidade do gap residual a confundidor | `run_konfound_evalues.py` | `konfound_hlm_vs_ols.tex` |
| **Interseccionalidade OB 4 grupos** | Extensão do Oaxaca para raça×gênero (resultado forte; pode subir ao núcleo se a banca pedir) | `run_interseccionalidade.py` | `interseccional_coeficientes.tex` |
| **VIF / multicolinearidade** | Diagnóstico dos preditores do M4 | `run_vif_multicolinearidade.py` | `vif_m4_preditores.csv` |
| **HLM vs OLS (justificação)** | Justifica a escolha do HLM (ICC, LRT, AIC) | `run_hlm_vs_ols_justificacao.py` | `lrt_tests.csv` |

---

## TIER 3 — ESTENDIDO (parqueado para artigo / mestrado)

Fora do corpo do TCC. **Preservados** no branch `mestrado-extenso`. Respondem outras perguntas
ou são redundantes com o núcleo — mantê-los no TCC diluiria a mensagem central.

| Método | Por que sai do TCC | Script(s) |
|--------|--------------------|-----------|
| SNA / redes (Burt) | Não sustenta conclusão sozinho; é narrativa de robustez "bonita" | `run_sna.py`, `run_sna_expandido.py` |
| K-Means / PAM | Responde "que perfis existem?", não a pergunta do gap | `run_clustering.py` |
| Heckman (seleção) | Correção de viés de seleção; tema próprio | `run_heckman_selecao.py` |
| Event study COVID | Pergunta temporal (efeito da pandemia), outro recorte | `run_event_study_covid.py` |
| Tendência temporal / Chow | Quebra estrutural temporal, outro recorte | `run_tendencia_temporal.py` |
| Oster bounds | Redundante com Konfound/E-value | `run_oster_bounds.py` |
| Segregação espacial | Tema próprio (geografia da segregação) | `run_segregacao_espacial.py`, `run_segregacao_ci.py` |
| Mobilidade intergeracional | Outra pergunta (elasticidade intergeracional) | `run_mobilidade.py` |
| Sobrevivência (Cox) | Outra pergunta (tempo até evento) | `run_sobrevivencia.py` |
| Gini intra-raça | Descritivo distribucional, suporte secundário | `run_gini_raca.py` |
| ENEM contextual | Outra base, outra pergunta | `run_analise_enem_contextual.py`, `run_ingestion_enem.py` |
| Validação RAIS | Validação cruzada com dado administrativo (agenda futura) | `run_validacao_rais.py`, `run_ingestion_rais.py` |
| Causal (PSM/IPW) | Sem identificação causal formal; agenda futura | `run_causal.py` |
| Hipóteses do Estado (Anexo A) | Praticamente um 2º TCC embutido | `run_hipoteses_estado.py` |
| Pesquisa Operacional (TOPSIS/AHP/PL) | Camada de recomendação de política, fora do diagnóstico | `run_politicas_po.py`, `run_po_regional.py`, `run_mapa_po_regional.py`, `run_analise_po.py` |
| Simulação de políticas | Contrafactual de política, fora do diagnóstico | `run_simulacao.py` |
| Análise regional | Recorte geográfico secundário | `run_analise_regional.py` |
| BLUP vs EB | Detalhe técnico de estimação | `run_blup_vs_eb.py` |
| GLMM random slope / HLM RS | Extensões do núcleo (heterogeneidade por setor/UF) | `run_glmm_rs_setor.py`, `run_hlm_rs_ext.py`, `run_hlm_m3_random_slope.py` |
| Retornos raciais | Recorte de retornos por característica | `run_analise_retornos_raciais.py` |

---

## Resumo numérico

| Tier | Métodos | Destino |
|------|---------|---------|
| Núcleo | 4 (+ apoio descritivo) | Corpo do TCC |
| Robustez | 6 | Apêndice enxuto do TCC |
| Estendido | ~20 | Parqueado (`mestrado-extenso`) |

De ~18 técnicas no corpo do trabalho original para **4 no núcleo + 6 de robustez**.
Isso atende diretamente ao ponto crítico do orientador.
