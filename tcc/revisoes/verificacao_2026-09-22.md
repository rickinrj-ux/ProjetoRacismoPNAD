# Verificação mecânica — 2026-09-22 15:08

Gatilho: `gerar_relatorio_enxuto.py`  
Achados: **0 ALTO**, 7 MÉDIO, 3 BAIXO, 4 INFO.

| Nível | Critério | Onde | Achado | Correção |
|---|---|---|---|---|
| MÉDIO | MHE-01/MHE-23/FAV-07 | relatorio | Linguagem causal ('comprova', 'determina', 'causa', 'efeito causal') em 1 linha(s): [692]. | Trocar por 'associa-se', 'é consistente com', 'penalidade condicional'; reservar causal para a seção de limitações. |
| MÉDIO | SWD-10/SWD-18/SWD-14 | relatorio: figuras | Nenhuma figura para Oaxaca-Blinder (só tabela). Figuras atuais: 7. | Uma figura por método do núcleo: cascata (OB), coeficiente×quantil com IC (QR/RIF), barras horizontais de OR com IC (GLMM), barras do β_negro M1→M4 (HLM). |
| MÉDIO | SWD-10/SWD-18/SWD-14 | relatorio: figuras | Nenhuma figura para Regressão quantílica/RIF (só tabela). Figuras atuais: 7. | Uma figura por método do núcleo: cascata (OB), coeficiente×quantil com IC (QR/RIF), barras horizontais de OR com IC (GLMM), barras do β_negro M1→M4 (HLM). |
| MÉDIO | SWD-10/SWD-18/SWD-14 | relatorio: figuras | Nenhuma figura para GLMM/logit (só tabela). Figuras atuais: 7. | Uma figura por método do núcleo: cascata (OB), coeficiente×quantil com IC (QR/RIF), barras horizontais de OR com IC (GLMM), barras do β_negro M1→M4 (HLM). |
| MÉDIO | FAV-43/ML-03 | run_glmm_glassceil.py | Logit sem AUC/ROC, matriz de confusão (cutoff) nem Hosmer-Lemeshow. | Reportar AUC + sensibilidade/especificidade no cutoff; comparar M1→M3 (roccomp). |
| MÉDIO | ML-02/ML-06 | run_ml_shap.py | Hold-out único, sem validação cruzada nem busca de hiperparâmetros. | k-fold (k=5) em subamostra para escolher max_depth/lr/n_estimators; reportar CV e hold-out. |
| MÉDIO | SWD-55/SWD-75 | gerar_apresentacao_pptx.py | 10/19 títulos de slide são tópicos ('N. Método — Tema'), não frases de ação. | Ex.: '5. HLM — Decomposição do Gap' → 'Morar em bairro segregado explica metade do gap racial'. |
| BAIXO | FAV-91 | relatorio | Vários N citados como 'população': ['7.689.426', '7.694.198']. | Declarar o N de cada modelo (filtros diferentes) em cada tabela. |
| BAIXO | SWD-55 | relatorio: legendas | 9 legenda(s) começam por rótulo descritivo em vez de afirmar o achado (ex.: 'Desempenho preditivo --- Random Forest, XGBoost e XGBoost se…'). | Título de ação na primeira frase da legenda. |
| BAIXO | SWD-42/SWD-40 | gerar_apresentacao_pptx.py | Paleta com 11 cores nomeadas. | Cinza + uma cor de destaque (azul); vermelho só para o dado que se quer destacar. |
| INFO | FAV-71 | hlm_stepup_fit.csv | BFGS reportou converged=False em M2/M3 (tolerância de gradiente). | Conferir estabilidade dos coeficientes (variam <0,1% entre degraus) ou aumentar maxiter. |
| INFO | MHE-25 | run_oaxaca_blinder.py | OB inclui ocupação/formalidade/horas como dotações (bad controls). Correto SÓ se o texto apresentar também a versão sem ocupação e tratar 16,2% como limite inferior. | Ver critério MHE-25 na revisão qualitativa. |
| INFO | MHE-75 | run_regressao_quantilica.py | QR sem bootstrap: SE dependem da densidade do resíduo em zero. | Bootstrap em blocos por UPA (ou declarar o kernel usado). |
| INFO | MHE-30/FAV-09/FAV-36 | run_hlm_stepup.py, run_oaxaca_blinder.py, run_regressao_quantilica.py, run_rif_decomp.py, run_glmm_glassceil.py, run_ml_shap.py, run_konfound_evalues.py, run_interseccionalidade.py, run_vif_multicolinearidade.py, run_hlm_vs_ols_justificacao.py | Sem peso amostral da PNAD (V1028) em nenhum modelo. | Declarar no texto que as estimativas são não ponderadas (regressão amostral, não populacional) ou reestimar um modelo-chave com pesos como robustez. |

_Checagens mecânicas apenas. Rode `/revisao-livros` para a revisão qualitativa completa (MHE, Fávero, Knaflic, Alencar)._