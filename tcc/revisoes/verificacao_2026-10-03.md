# Verificação mecânica — 2026-10-03 15:44

Gatilho: `C:\Users\user\Documents\ProjetoRacismoPNAD\tcc\scripts\checar_escolaridade.py`  
Achados: **13 ALTO**, 0 MÉDIO, 0 BAIXO, 2 INFO.

| Nível | Critério | Onde | Achado | Correção |
|---|---|---|---|---|
| ALTO | ML-04/FAV-91 | relatorio: tab:ml_perf | Random Forest: R² no relatório = 0.5695 vs csv = 0.5891. | Regerar a tabela a partir de ml_performance.csv (fonte única). |
| ALTO | ML-04/FAV-91 | relatorio: tab:ml_perf | Random Forest: MAE no relatório = 0.4551 vs csv = 0.4288. | Regerar a tabela a partir de ml_performance.csv (fonte única). |
| ALTO | ML-04/FAV-91 | relatorio: tab:ml_perf | Random Forest: RMSE no relatório = 0.6059 vs csv = 0.5753. | Regerar a tabela a partir de ml_performance.csv (fonte única). |
| ALTO | ML-04/FAV-91 | relatorio: tab:ml_perf | XGBoost: R² no relatório = 0.628 vs csv = 0.6444. | Regerar a tabela a partir de ml_performance.csv (fonte única). |
| ALTO | ML-04/FAV-91 | relatorio: tab:ml_perf | XGBoost: MAE no relatório = 0.4216 vs csv = 0.397. | Regerar a tabela a partir de ml_performance.csv (fonte única). |
| ALTO | ML-04/FAV-91 | relatorio: tab:ml_perf | XGBoost: RMSE no relatório = 0.5632 vs csv = 0.5352. | Regerar a tabela a partir de ml_performance.csv (fonte única). |
| ALTO | FAV-91/SWD-06 | relatorio | OR = 0.34 citado no texto não existe em nenhum csv de GLMM/logit (valores atuais CBO1-4: M1=0.728, M2=0.796, M3=0.792). | Atualizar o número (provavelmente resíduo de uma rodada antiga). |
| ALTO | FAV-91 | relatorio | Teste de heterogeneidade quantílica: texto cita Z = -17.39, csv = [-15.61, -2.703]. | Alinhar ao qr_kb_test.csv. |
| ALTO | FAV-91 | relatorio | Teste de heterogeneidade quantílica: texto cita Z = -17.39, csv = [-15.61, -2.703]. | Alinhar ao qr_kb_test.csv. |
| ALTO | FAV-91 | relatorio | % dotações do OB no csv (82.7) não aparece no texto. | Regerar ob_acesso.tex/texto. |
| ALTO | FONTE-ÚNICA/FAV-91 | entregaveis/relatorio_tcc_enxuto.docx | Valores sem correspondência no csv: OR = 0,697. | O entregável não acompanhou a reexecução: regerá-lo lendo os csv (params_nucleo.py) em vez de números escritos à mão. |
| ALTO | FONTE-ÚNICA/FAV-91 | entregaveis/TCC_Ricardo_Calheiros_Guia_de_Estudo.docx | Valores sem correspondência no csv: OR = 0,697, R² = 0,604, R² = 0,628. | O entregável não acompanhou a reexecução: regerá-lo lendo os csv (params_nucleo.py) em vez de números escritos à mão. |
| ALTO | FONTE-ÚNICA/FAV-91 | entregaveis/TCC_Ricardo_Calheiros_MBA_USP_Esalq.docx | Valores sem correspondência no csv: OR = 0,697. | O entregável não acompanhou a reexecução: regerá-lo lendo os csv (params_nucleo.py) em vez de números escritos à mão. |
| INFO | MHE-25 | run_oaxaca_blinder.py | OB inclui ocupação/formalidade/horas como dotações (bad controls). Correto SÓ se o texto apresentar também a versão sem ocupação e tratar 16,2% como limite inferior. | Ver critério MHE-25 na revisão qualitativa. |
| INFO | MHE-30/FAV-09/FAV-36 | run_hlm_stepup.py, run_oaxaca_blinder.py, run_ob_qr_melhorias.py, run_rif_decomp.py, run_glmm_glassceil.py, run_se_rif_interseccional.py, run_ml_shap.py, run_konfound_evalues.py, run_interseccionalidade.py, run_vif_multicolinearidade.py, run_hlm_vs_ols_justificacao.py | Sem peso amostral da PNAD (V1028) em nenhum modelo. | Declarar no texto que as estimativas são não ponderadas (regressão amostral, não populacional) ou reestimar um modelo-chave com pesos como robustez. |

_Checagens mecânicas apenas. Rode `/revisao-livros` para a revisão qualitativa completa (MHE, Fávero, Knaflic, Alencar)._