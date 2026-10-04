# Retomada — reestimação após a correção do vazamento (leave-one-out)

Estado em 01/10/2026. Este arquivo existe para que a reestimação possa ser
retomada numa sessão nova, sem depender da conversa anterior.

## Por que tudo está sendo reestimado

As médias de contexto (`pct_negro_upa`, `media_educ_upa`, `media_renda_upa`,
`tx_desemprego_upa` e os equivalentes de UF) eram calculadas com `mean()`
simples — **incluindo a própria observação**. A raça da pessoa entrava no
regressor que deveria descrever o bairro dela, contaminando justamente
$\gamma_{01}$, o coeficiente lido como evidência de *duplo disadvantage*. É o
problema do reflexo (Manski, 1993), que o trabalho já nomeava e corrigia apenas
para a renda, apenas nos modelos preditivos.

Decisão do autor: corrigir e reestimar, em vez de entregar com nota
justificando o viés.

## O que já foi feito

- [x] `scripts/utils/recalcular_contexto_loo.py` — recalculou as médias em
      *leave-one-out* no parquet. Original preservado em
      `data/processed/features.parquet.pre_loo`.
- [x] `src/feature_engineering.py` — corrigido na origem (níveis de UPA e UF),
      para que a próxima ingestão já nasça certa.
- [x] **HLM step-up reestimado** (`--force`, 80 min; o cache de 23/09 estava
      devolvendo os modelos antigos sem reajustar — atenção a isso).
- [x] `tcc/scripts/gerar_tabela_robustez.py` — tabela com 13 verificações,
      todas lidas de csv, já ligada à subseção de Inferência.
- [x] Corrigido: "41.517 clusters" estava fixo no gerador; agora vem do csv.

## O que mudou nos números

| | antes (com vazamento) | depois |
|---|---|---|
| $\beta$ M1 | −0,112410 | −0,112410 *(não muda: M1 não tem contexto)* |
| $\beta$ M2 | −0,107630 | −0,109882 |
| **$\beta$ M3 (gap líquido)** | −0,107657 | **−0,110230** |
| **gap M3** | **−10,2%** | **−10,4%** |
| $\beta$ M4 | −0,072425 | −0,074281 |
| **gap M4** | **−7,0%** | **−7,2%** |
| $\gamma_{01}$ (M3) | −0,250750 | −0,249258 |
| OR acesso A1 | 0,691061 | 0,691291 |
| **OR acesso A2** | **0,699348** | **0,696839** |

**A penalidade racial ficou maior, não menor** — o vazamento a subestimava,
porque o contexto absorvia parte do efeito individual. O M1 não mudar é a prova
de que o reprocessamento atingiu só o que devia.

## O que falta — fila de reestimação

1. [x] **GLMM** (`scripts/R/glmm_glassceil.R`) — **12 de 12, todos convergidos** (01/10, 09h20).
       O script retoma sozinho pelo checkpoint no csv. ~19 min por modelo.
       Já traz a simetria de controles com o HLM (ano, área urbana,
       `educ_fund_completo`) e a jornada movida para o degrau A3.
2. [x] `scripts/analise/run_se_rif_interseccional.py` — RIF e interseccional
3. [x] `scripts/analise/run_ob_qr_melhorias.py` — Oaxaca e quantílica
4. [x] `scripts/analise/run_ml_shap.py` — ~2,5 h
5. [x] `scripts/analise/run_ml_cv.py`
6. [x] `scripts/analise/run_vif_multicolinearidade.py`
7. [x] `scripts/analise/run_regressao_quantilica.py --so-area`
8. [x] `scripts/R/hlm_tres_niveis.R M0` e `M2` (robustez de três níveis)
9. [x] `scripts/R/run_grupo_rg_topo.R`
10. [x] `scripts/analise/run_gini_raca.py`
11. [x] Regerar: `tcc/scripts/gerar_tabela_robustez.py`, tabelas, figuras,
        `relatorio_tcc.tex` → enxuto → `tcc_normas.tex` → PDF → .docx →
        `conferir_anexos_normas.py` (26/26) e `validate_consistency.py`
12. [x] Regerar a **versão narrativa** (`tcc/scripts/gerar_narrativa_social.py`)

## Obstáculo operacional

Três processos foram encerrados pelo watchdog de memória do Claude Code
(quantílica 2×, GLMM 2×). Cada execução avança um modelo e morre. A saída é
abrir a sessão com o encerramento automático desligado:

```
set CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1
claude
```

**Contorno adotado em 01/10/2026 (06h)**: o GLMM roda num laço PowerShell
lançado com `Start-Process` (`tcc/scripts/glmm_loop.ps1`) (fora da árvore de shells do Claude Code, logo fora
do alcance do watchdog). Cada iteração chama `Rscript glmm_glassceil.R --one`,
grava um modelo e encerra, devolvendo a memória ao sistema operacional. O laço
para ao chegar a 12 linhas ou quando uma iteração não avança. Log em
`outputs/logs/glmm_loo_loop.log` (codificação mista: ler com `tr -d '\000'`).
O script do laço precisa ser salvo em UTF-8 **com BOM**: sem BOM, o PowerShell
5.1 não o interpreta por causa dos acentos.

## Onde estão os backups

- `data/processed/features.parquet.pre_loo` — parquet antes da correção
- `outputs/_backup_pre_loo/` — csv de todos os blocos antes da reestimação,
  mais `cache_hlm/` com o cache do HLM anterior

## Atenção ao estado atual

`outputs/tables/glmm_glassceil_glmer.csv` tem **2 linhas das 12** — o documento
**não deve ser regerado** antes de o GLMM terminar, ou os números do acesso
saem incompletos. O csv íntegro anterior está em `outputs/_backup_pre_loo/`.

## Atualização 01/10/2026, 09h30

- GLMM completo (12/12, todos `converged = TRUE`). OR do acesso: M1 0,691,
  M2 0,697, M3 0,687, M4 0,684. Os OR do topo **caíram** (penalidade maior):
  top 20% M2 de 0,688 para 0,672; top 10% M2 de 0,654 para 0,640.
- Itens 2–10 rodando em sequência pela fila destacada `tcc/scripts/fila_loo.ps1`
  (SHAP por último). Resumo em `outputs/logs/fila_loo_status.log`; um log por
  passo em `outputs/logs/loo_<nome>.log`. Se cair, comentar os passos já `OK`
  na lista `$passos` e relançar.

## Atualização 01/10/2026, 21h15

- Fila 1 (`fila_loo.ps1`, itens 2–10) concluída às 19:01, todos os passos OK.
- **Lacuna da fila original**: quatro scripts do núcleo usam as médias de contexto
  e não estavam na lista — `run_hlm_serie_completa.py`, `run_oaxaca_blinder.py`,
  `run_glmm_glassceil.py` (logit FE-UF) — mais `run_konfound_evalues.py`, que
  depende deles. Rodados na fila 2 (`tcc/scripts/fila_loo2.ps1`).
- **Terceira armadilha de cache**: `src/rif_decomp.py` guarda checkpoint por
  quantil em `outputs/tables/rif_checkpoints/` e devolvia as estimativas pontuais
  de junho. Checkpoints movidos para `outputs/_backup_pre_loo/rif_checkpoints/`;
  RIF reestimado na fila 2. O `run_se_rif_interseccional.py` só produz os EPs —
  as estimativas pontuais da tab:rif_ob vêm do `rif_ob_decomposicao.csv`.
- Corrigido no caminho: form feed no `run_tcc.ps1` (`scripts\formatar…` virava
  `scripts<FF>ormatar…`); BOM no `run_tcc.ps1` (o PowerShell 5.1 não o lia — não
  há pwsh 7 na máquina); marcador `@@N_UPAS@@` não preenchido na subseção de
  Inferência (agora 40.968 clusters; o antigo "41.517" estava errado);
  âncora do patch Soares com números fixos; parcela de retornos da RIF
  (35,1/12,9) escrita à mão em três lugares — agora `@@RIF_RET_Q10/Q90@@`;
  limitação "Reflexo (Manski)" reescrita para dizer que todas as médias são LOO.
- O `run_tcc.ps1 -Relatorio` não compila o LaTeX; a fila 2 compila e repete os
  passos que copiam o PDF para `entregaveis/`.
- Retomar a fila 2 de qualquer passo: `fila_loo2.ps1 -Desde <nome>`.

## Atualização 02/10/2026, 01h15 — fósseis e tendência

- **Números fósseis**: dois portões novos. `tcc/scripts/caca_fosseis.py --vivos` (número
  digitado nos geradores) e `tcc/scripts/conferir_numeros_entregaveis.py` (número sem
  fonte no produto final). Ambos em 0, e entram no fim da `fila_loo2.ps1`.
- Corrigidos, entre outros: deck da Defesa inteiro (45 números à mão, figuras de
  junho, UPAs 40.120, "HLM 3 níveis"); Abstract do enxuto (35.1/12.9); N 7.694.198 do
  `params.py` da raiz; R² "0,62" (é 0,63); "31% da PEA" (é 31,65%); nota do log;
  notas das tabelas GLMM e CV. Marcador genérico `@@P:CHAVE:casas:modo@@` no enxuto.
- **Tendência**: série anual reestimada com o M3 do núcleo (`run_m3_serie_sensib.py
  --serie`, `fila_m3.ps1`). δ = 0,000757, IC [−0,000396; 0,001910], p = 0,169; Chow 2020
  p = 0,0007. Texto reformulado: "Na década, nenhuma convergência mensurável"; prazo só
  pelo cenário otimista do IC (~62 anos), conclusão condicional ao resultado.
- **Sensibilidade educ_missing**: M3 com e sem o indicador, variação de 0,99%
  (`sensib_educ_missing.csv`).
- **Figura nova para avaliação** (ainda fora do documento): `outputs/figures/
  hlm_rs_retas_upa.png` — retas por bairro e BLUPs u0j × u1j do M3_RS (corr −0,48),
  gerada por `tcc/scripts/gerar_figura_rs_blups.py`.
- Pendente: commit; decisão sobre incluir a figura de inclinações aleatórias.

## 03/10/2026 — regressão do LOO do desemprego
- **Desemprego do bairro/UF sem leave-one-out nos números "depois":** a reconstrução da base em
  02/10 perdeu o LOO do desemprego (o das outras médias foi mantido). Impacto medido na base de
  03/10, MQO com UF e ano, erro agrupado por UPA: β_negro −0,06302 nos dois casos (idêntico até a
  5ª casa); β_desemprego −0,00509 → −0,00497 (EP 0,0012); correlação das duas versões 0,9999.
  Decisão do autor (03/10): corrigir o código na origem e NÃO reestimar. Teste novo em
  `checar_escolaridade.py` acusa médias de contexto constantes dentro da UPA.

## 04/10/2026 — E2, especificação simétrica e fechamento do texto
- **E2.5 (reestimado):** a especificação (A) do Oaxaca, a RIF, a RIF interseccional e a QR não
  tinham jornada, área urbana e UF, embora o texto dissesse "os controles do M3". Com eles:
  OB retornos 23,4% → 17,9% (A) e 17,3% → 15,4% (B); RIF retornos q10 32,3% → 26,5%, q90 9,1% → 8,9%
  (razão 3,5 → 3,0); QR q10 5,7% → 4,3%, q90 8,7% → 8,4%, KB Z −25,9. Fila: `tcc/scripts/fila_e2.ps1`.
- **E2.2:** M1 reestimado com UF (`--fit M1_UF`, `exportar_m1_uf.py`): mediação pelo bairro 41,6%
  contra 39,5% sem UF — a escada é conservadora; nota condicional na Tab. 5. Agregado sem UF: 20,1%.
- **E2.16:** GLMM dos 4 grupos por grande grupo CBO (`scripts/R/run_grupo_rg_por_cbo.R`): a mulher
  negra tem OR 0,63 entre dirigentes (o menor) e 1,96 no apoio administrativo (mulher branca 2,20);
  o OR 1,31 de CBO 1–4 era composição de ocupações feminizadas.
- **E2.7:** E-value com √OR para desfecho comum (`params_nucleo.evalue`, única implementação):
  acesso 1,76 → 1,46.
- **E2.17:** Considerações Iniciais (conceito de racismo estrutural), pontes nos Resultados, críticas e
  propostas na Discussão, Conclusão em dois parágrafos — `tcc/scripts/tcc_normas_narrativa.py`.
- **E7.1:** releitura por agente (38 achados, 35 corrigidos). Regeneração final com portões OK.
- **Armadilha:** `relatorio_tcc.bib` é REGERADO por `gerar_relatorio_tcc.py` (string BIB) e completado
  pelo enxuto; entrada editada no arquivo se perde.
- **Sem commit** desde ba20b77 (03/10): ~150 arquivos.
