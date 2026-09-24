# Verificação mecânica — 2026-09-23 21:48

Gatilho: `gerar_tcc_normas_docx.py`  
Achados: **0 ALTO**, 0 MÉDIO, 0 BAIXO, 2 INFO.

| Nível | Critério | Onde | Achado | Correção |
|---|---|---|---|---|
| INFO | MHE-25 | run_oaxaca_blinder.py | OB inclui ocupação/formalidade/horas como dotações (bad controls). Correto SÓ se o texto apresentar também a versão sem ocupação e tratar 16,2% como limite inferior. | Ver critério MHE-25 na revisão qualitativa. |
| INFO | MHE-30/FAV-09/FAV-36 | run_hlm_stepup.py, run_oaxaca_blinder.py, run_ob_qr_melhorias.py, run_rif_decomp.py, run_glmm_glassceil.py, run_se_rif_interseccional.py, run_ml_shap.py, run_konfound_evalues.py, run_interseccionalidade.py, run_vif_multicolinearidade.py, run_hlm_vs_ols_justificacao.py | Sem peso amostral da PNAD (V1028) em nenhum modelo. | Declarar no texto que as estimativas são não ponderadas (regressão amostral, não populacional) ou reestimar um modelo-chave com pesos como robustez. |

_Checagens mecânicas apenas. Rode `/revisao-livros` para a revisão qualitativa completa (MHE, Fávero, Knaflic, Alencar)._