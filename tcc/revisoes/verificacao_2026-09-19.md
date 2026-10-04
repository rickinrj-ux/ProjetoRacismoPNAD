# Verificação mecânica — 2026-09-19 23:54

Gatilho: `C:\Users\user\Documents\ProjetoRacismoPNAD\scripts\analise\run_ob_qr_melhorias.py`  
Achados: **1 ALTO**, 11 MÉDIO, 3 BAIXO, 3 INFO.

| Nível | Critério | Onde | Achado | Correção |
|---|---|---|---|---|
| ALTO | FAV-77/FAV-70 | run_glmm_glassceil.py | Script rotulado GLMM estima logit com UF como efeito fixo + HC1 (sem efeito aleatório). O relatório descreve 'GLMM com efeito aleatório de UPA'. | Ou alimentar a tabela com scripts/R/logit_multinivel_glmm.R (glmer, ICC UPA, LR test vs logit), ou renomear para 'logit com efeitos fixos de UF' e citar o glmer como robustez. |
| MÉDIO | MHE-75/MHE-84 | run_regressao_quantilica / qr_kb_test.csv | SE do contraste q90−q10 por bootstrap em 5% da amostra, sem blocos por UPA. | Bootstrap em blocos (UPA) ou, no mínimo, declarar no texto que o SE é conservador por vir de subamostra. |
| MÉDIO | FAV-33/FAV-44 | hlm_serie_completo.csv | M3_Completo_OLS: coeficiente degenerado em 'Log-Likelihood' (-8124305.69…) — z-scores de UF são colineares com C(UF_str). | Remover _UF das fórmulas OLS com dummies de UF (ou remover as dummies). |
| MÉDIO | FAV-71/FAV-72 | relatorio: tab:hlm_resultados | AIC/BIC 'N/D' em todos os modelos: sem LR test/critérios de informação a estratégia step-up (Fávero) fica incompleta. | Reportar −2LL, AIC, BIC e LR test M0→M1→M2→M3 (REML comparável ou refit por ML). |
| MÉDIO | MHE-01/MHE-23/FAV-07 | relatorio | Linguagem causal ('comprova', 'determina', 'causa', 'efeito causal') em 1 linha(s): [674]. | Trocar por 'associa-se', 'é consistente com', 'penalidade condicional'; reservar causal para a seção de limitações. |
| MÉDIO | SWD-10/SWD-18/SWD-14 | relatorio: figuras | Nenhuma figura para HLM (só tabela). Figuras atuais: 6. | Uma figura por método do núcleo: cascata (OB), coeficiente×quantil com IC (QR/RIF), barras horizontais de OR com IC (GLMM), barras do β_negro M1→M4 (HLM). |
| MÉDIO | SWD-10/SWD-18/SWD-14 | relatorio: figuras | Nenhuma figura para Oaxaca-Blinder (só tabela). Figuras atuais: 6. | Uma figura por método do núcleo: cascata (OB), coeficiente×quantil com IC (QR/RIF), barras horizontais de OR com IC (GLMM), barras do β_negro M1→M4 (HLM). |
| MÉDIO | SWD-10/SWD-18/SWD-14 | relatorio: figuras | Nenhuma figura para Regressão quantílica/RIF (só tabela). Figuras atuais: 6. | Uma figura por método do núcleo: cascata (OB), coeficiente×quantil com IC (QR/RIF), barras horizontais de OR com IC (GLMM), barras do β_negro M1→M4 (HLM). |
| MÉDIO | SWD-10/SWD-18/SWD-14 | relatorio: figuras | Nenhuma figura para GLMM/logit (só tabela). Figuras atuais: 6. | Uma figura por método do núcleo: cascata (OB), coeficiente×quantil com IC (QR/RIF), barras horizontais de OR com IC (GLMM), barras do β_negro M1→M4 (HLM). |
| MÉDIO | FAV-43/ML-03 | run_glmm_glassceil.py | Logit sem AUC/ROC, matriz de confusão (cutoff) nem Hosmer-Lemeshow. | Reportar AUC + sensibilidade/especificidade no cutoff; comparar M1→M3 (roccomp). |
| MÉDIO | ML-02/ML-06 | run_ml_shap.py | Hold-out único, sem validação cruzada nem busca de hiperparâmetros. | k-fold (k=5) em subamostra para escolher max_depth/lr/n_estimators; reportar CV e hold-out. |
| MÉDIO | SWD-55/SWD-75 | gerar_apresentacao_pptx.py | 10/19 títulos de slide são tópicos ('N. Método — Tema'), não frases de ação. | Ex.: '5. HLM — Decomposição do Gap' → 'Morar em bairro segregado explica metade do gap racial'. |
| BAIXO | MHE-85/FAV-91 | relatorio: tab:hlm_resultados | Erros-padrão exibidos como (0.0000). | Mais casas decimais ou notação científica. |
| BAIXO | SWD-55 | relatorio: legendas | 10 legenda(s) começam por rótulo descritivo em vez de afirmar o achado (ex.: 'Modelos HLM de Três Níveis --- Determinantes do Log-Rendimen…'). | Título de ação na primeira frase da legenda. |
| BAIXO | SWD-42/SWD-40 | gerar_apresentacao_pptx.py | Paleta com 11 cores nomeadas. | Cinza + uma cor de destaque (azul); vermelho só para o dado que se quer destacar. |
| INFO | MHE-25 | run_oaxaca_blinder.py | OB inclui ocupação/formalidade/horas como dotações (bad controls). Correto SÓ se o texto apresentar também a versão sem ocupação e tratar 16,2% como limite inferior. | Ver critério MHE-25 na revisão qualitativa. |
| INFO | MHE-75 | run_regressao_quantilica.py | QR sem bootstrap: SE dependem da densidade do resíduo em zero. | Bootstrap em blocos por UPA (ou declarar o kernel usado). |
| INFO | MHE-30/FAV-09/FAV-36 | run_hlm_m4.py, run_oaxaca_blinder.py, run_regressao_quantilica.py, run_rif_decomp.py, run_glmm_glassceil.py, run_ml_shap.py, run_konfound_evalues.py, run_interseccionalidade.py, run_vif_multicolinearidade.py, run_hlm_vs_ols_justificacao.py | Sem peso amostral da PNAD (V1028) em nenhum modelo. | Declarar no texto que as estimativas são não ponderadas (regressão amostral, não populacional) ou reestimar um modelo-chave com pesos como robustez. |

_Checagens mecânicas apenas. Rode `/revisao-livros` para a revisão qualitativa completa (MHE, Fávero, Knaflic, Alencar)._