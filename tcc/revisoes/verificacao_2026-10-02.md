# Verificação mecânica — 2026-10-02 21:28

Gatilho: `C:\Users\user\Documents\ProjetoRacismoPNAD\scripts\geradores\gerar_relatorio_tcc.py`  
Achados: **4 ALTO**, 0 MÉDIO, 0 BAIXO, 2 INFO.

| Nível | Critério | Onde | Achado | Correção |
|---|---|---|---|---|
| ALTO | FONTE-ÚNICA/FAV-91 | entregaveis/TCC_Ricardo_Calheiros_Defesa.pptx | Valores sem correspondência no csv: AME = 5,55, AME = 5,68, OR = 0,691, OR = 0,697. | O entregável não acompanhou a reexecução: regerá-lo lendo os csv (params_nucleo.py) em vez de números escritos à mão. |
| ALTO | FONTE-ÚNICA/FAV-91 | entregaveis/relatorio_tcc_enxuto.docx | Valores sem correspondência no csv: OR = 0,697. | O entregável não acompanhou a reexecução: regerá-lo lendo os csv (params_nucleo.py) em vez de números escritos à mão. |
| ALTO | FONTE-ÚNICA/FAV-91 | entregaveis/TCC_Ricardo_Calheiros_Guia_de_Estudo.docx | Valores sem correspondência no csv: OR = 0,697. | O entregável não acompanhou a reexecução: regerá-lo lendo os csv (params_nucleo.py) em vez de números escritos à mão. |
| ALTO | FONTE-ÚNICA/FAV-91 | entregaveis/TCC_Ricardo_Calheiros_MBA_USP_Esalq.docx | Valores sem correspondência no csv: OR = 0,697. | O entregável não acompanhou a reexecução: regerá-lo lendo os csv (params_nucleo.py) em vez de números escritos à mão. |
| INFO | MHE-25 | run_oaxaca_blinder.py | OB inclui ocupação/formalidade/horas como dotações (bad controls). Correto SÓ se o texto apresentar também a versão sem ocupação e tratar 16,2% como limite inferior. | Ver critério MHE-25 na revisão qualitativa. |
| INFO | MHE-30/FAV-09/FAV-36 | run_hlm_stepup.py, run_oaxaca_blinder.py, run_ob_qr_melhorias.py, run_rif_decomp.py, run_glmm_glassceil.py, run_se_rif_interseccional.py, run_ml_shap.py, run_konfound_evalues.py, run_interseccionalidade.py, run_vif_multicolinearidade.py, run_hlm_vs_ols_justificacao.py | Sem peso amostral da PNAD (V1028) em nenhum modelo. | Declarar no texto que as estimativas são não ponderadas (regressão amostral, não populacional) ou reestimar um modelo-chave com pesos como robustez. |

_Checagens mecânicas apenas. Rode `/revisao-livros` para a revisão qualitativa completa (MHE, Fávero, Knaflic, Alencar)._