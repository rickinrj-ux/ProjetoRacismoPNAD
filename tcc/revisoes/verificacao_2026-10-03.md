# Verificação mecânica — 2026-10-03 20:11

Gatilho: `gerar_tabela_mediacao.py`  
Achados: **0 ALTO**, 2 MÉDIO, 0 BAIXO, 2 INFO.

| Nível | Critério | Onde | Achado | Correção |
|---|---|---|---|---|
| MÉDIO | REMISSÃO/SWD-06 | TCC_Ricardo_Calheiros_MBA_USP_Esalq.docx | Título de seção solto dentro de parênteses: “…Subseção “Inferência: erros-padrão agrupados, poucos clu…”. | Redigir a remissão ('ver a seção X') em vez de inserir o título nu, que o leitor lê como continuação da frase. |
| MÉDIO | SWD-30/SWD-40 | relatorio | 2 parágrafo(s) de prosa com carga numérica alta (acima de 6%, ou mais de 6 números acima de 4,5%): ['Modelos de Machine Lea | O erro na unidade original. (6 em 88 = 6.8%)', 'Regressão Quantílica e | Por sexo. (5 em 66 = 7.6%)']. | Manter na linha de leitura só o que a banca vai citar; erro-padrão, IC, estatísticas de teste e componentes de variância vivem na tabela ou em nota. |
| INFO | MHE-25 | run_oaxaca_blinder.py | OB inclui ocupação/formalidade/horas como dotações (bad controls). Correto SÓ se o texto apresentar também a versão sem ocupação e tratar 16,2% como limite inferior. | Ver critério MHE-25 na revisão qualitativa. |
| INFO | MHE-30/FAV-09/FAV-36 | run_hlm_stepup.py, run_oaxaca_blinder.py, run_ob_qr_melhorias.py, run_rif_decomp.py, run_glmm_glassceil.py, run_se_rif_interseccional.py, run_ml_shap.py, run_konfound_evalues.py, run_interseccionalidade.py, run_vif_multicolinearidade.py, run_hlm_vs_ols_justificacao.py | Sem peso amostral da PNAD (V1028) em nenhum modelo. | Declarar no texto que as estimativas são não ponderadas (regressão amostral, não populacional) ou reestimar um modelo-chave com pesos como robustez. |

_Checagens mecânicas apenas. Rode `/revisao-livros` para a revisão qualitativa completa (MHE, Fávero, Knaflic, Alencar)._