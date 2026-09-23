# Verificação mecânica — 2026-09-23 13:36

Gatilho: `execução manual`  
Achados: **0 ALTO**, 0 MÉDIO, 2 BAIXO, 4 INFO.

| Nível | Critério | Onde | Achado | Correção |
|---|---|---|---|---|
| BAIXO | FAV-91 | relatorio | Vários N citados como 'população': ['7.689.426', '7.694.198']. | Declarar o N de cada modelo (filtros diferentes) em cada tabela. |
| BAIXO | SWD-55 | relatorio: legendas | 5 legenda(s) começam por rótulo descritivo em vez de afirmar o achado (ex.: 'Desempenho preditivo --- Random Forest, XGBoost e XGBoost se…'). | Título de ação na primeira frase da legenda. |
| INFO | FAV-71 | hlm_stepup_fit.csv | BFGS reportou converged=False em M2/M3 (tolerância de gradiente). | Conferir estabilidade dos coeficientes (variam <0,1% entre degraus) ou aumentar maxiter. |
| INFO | MHE-25 | run_oaxaca_blinder.py | OB inclui ocupação/formalidade/horas como dotações (bad controls). Correto SÓ se o texto apresentar também a versão sem ocupação e tratar 16,2% como limite inferior. | Ver critério MHE-25 na revisão qualitativa. |
| INFO | MHE-75 | run_regressao_quantilica.py | QR sem bootstrap: SE dependem da densidade do resíduo em zero. | Bootstrap em blocos por UPA (ou declarar o kernel usado). |
| INFO | MHE-30/FAV-09/FAV-36 | run_hlm_stepup.py, run_oaxaca_blinder.py, run_regressao_quantilica.py, run_rif_decomp.py, run_glmm_glassceil.py, run_ml_shap.py, run_konfound_evalues.py, run_interseccionalidade.py, run_vif_multicolinearidade.py, run_hlm_vs_ols_justificacao.py | Sem peso amostral da PNAD (V1028) em nenhum modelo. | Declarar no texto que as estimativas são não ponderadas (regressão amostral, não populacional) ou reestimar um modelo-chave com pesos como robustez. |

_Checagens mecânicas apenas. Rode `/revisao-livros` para a revisão qualitativa completa (MHE, Fávero, Knaflic, Alencar)._