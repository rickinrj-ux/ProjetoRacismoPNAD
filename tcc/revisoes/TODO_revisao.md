# TODO — Correções aprovadas da revisão pelos livros (2026-09-19)

Origem: `revisao_2026-09-18.md` + `verificacao_2026-09-18.md`. Todas as propostas aprovadas
pelo autor em 2026-09-19. Ordem = dependência (o que muda número vem antes do que cita número;
o texto e as figuras vêm por último para não serem refeitos duas vezes).
Após cada bloco: rodar `python .claude/skills/revisao-livros/scripts/verificar_analises.py`
e commitar.

Legenda: ⏱ estimativa · 🖥 exige reestimação de modelo · ✍ só texto/gerador

---

## Bloco 0 — Escopo (✍, ⏱ 2 h)

- [x] 0.1 Remover PO do relatório: título (l.97–100), Discussão "Da diagnose à prescrição"
      (l.830–840) e "Ancoragem em políticas públicas" (l.945–966 → manter as leis, tirar
      TOPSIS/PL), Conclusão (l.1043–1049)
- [x] 0.2 Remover SNA: H5 (l.293–295), "Mapa das três camadas" (l.468), Barreira III (l.783–793 →
      vira parágrafo de agenda), Discussão l.912–921 e l.858, Conclusão l.981–989, l.1015–1018,
      l.1055–1060, Limitações l.1096
- [x] 0.3 Remover clustering: H3 (l.283–287), Discussão l.913, Conclusão l.1055
- [x] 0.4 "Seis metodologias" (l.1027) → "quatro métodos e cinco análises de robustez"; reescrever
      "Contribuição principal" (l.1053–1060) só com o núcleo
- [x] 0.5 Espelhar tudo em `tcc/scripts/gerar_relatorio_enxuto.py` (3 menções de PO, SNA, clustering)
      e `scripts/geradores/gerar_apresentacao_pptx.py` (clustering) para a regeneração não reintroduzir
- [x] 0.6 Renumerar slides (13→15→20→21→27→28) ou remover números

## Bloco 1 — Fonte única de números (✍, ⏱ 1 h)

- [x] 1.1 Tabela ML (`tab:ml_perf`, l.581–597) gerada de `ml_performance.csv`; apagar "R² ≈ 0,43"
      (l.594) e o "N_teste = 307.768" (amostra de 20 %) — usar o N do hold-out da população
- [x] 1.2 Z da QR: −5,25 (l.1041) → −5,57 (`qr_kb_test.csv`)
- [x] 1.3 OR 0,676 (l.952, l.1037) → 0,705 (M2, `glmm_glassceil_full.csv`); OR(top20) 0,540 e
      OR(top10) 0,457 são M1 — trocar por M2 (0,691 / 0,656) ou declarar o modelo em cada citação
- [x] 1.4 Terminologia: "gap líquido" = M3 (−9,6 %, sem ocupação); "gap residual pós-ocupação" =
      M4 (−6,2 %). Corrigir l.464 ("−6,2 % após 23 controles"), l.924, l.963, l.1004, l.1034
- [x] 1.5 "ICC cai para 5,3 %" (l.502) → 5,8 % (tabela: 0,0581)
- [x] 1.6 Convenção de sinal única para gaps em % (penalidade positiva OU β negativo)
- [ ] 1.7 (depende do Bloco 2: os SE vêm de hlm_serie_completo.csv) Substituir `(0.0000)` por notação com mais casas; trocar asteriscos por IC 95 % nas
      tabelas do núcleo (MHE-85)

## Bloco 2 — Erros-padrão (🖥, ⏱ ½ dia de máquina + 1 h)

- [ ] 2.1 `run_hlm_serie_completa.py`: OLS M1–M4 com `cov_type="cluster"` por **UPA** (além do
      cluster-UF já existente); remover `_UF` das fórmulas OLS que têm `C(UF_str)` (colinearidade
      → intercepto 5,5e7 em `hlm_serie_completo.csv`)
- [ ] 2.2 Tabela HLM: coluna de SE cluster-UPA ao lado do SE do modelo; para cluster-UF (27 < 42)
      wild-cluster bootstrap ou t com g−k g.l.; nota na Metodologia (MHE-81/82)
- [ ] 2.3 `run_oaxaca_blinder.py`: OLS por grupo com `cov_type="cluster"` (UPA); bootstrap em
      blocos por UPA (B=200) para dotação/retorno — conferir de onde vêm os SE de `ob_acesso.tex`
      e citar o script certo
- [ ] 2.4 `run_regressao_quantilica.py`: bootstrap em blocos por UPA para β(τ) e para o contraste
      q90−q10 (hoje: 5 % da amostra) — ou declarar no texto que o SE é conservador
- [ ] 2.5 `run_glmm_glassceil.py`: `cov_type="cluster"` por UPA nos logits; IC recalculado
- [ ] 2.6 Robustez com peso amostral: M3 OLS cluster-UPA com `weights=V1028`; frase na Metodologia
      dizendo que os demais modelos são não ponderados (MHE-30/FAV-09)

## Bloco 3 — HLM honesto (🖥, ⏱ 1 dia) — decisão: qual das duas?

- [ ] 3.1 **Escolher**: (a) reescrever como 2 níveis (indivíduo/UF) + contexto de UPA, usando
      `run_hlm_m4.py` (groups=UPA) como modelo de UPA; ou (b) estimar 3 níveis em lme4
      `(1|UF/UPA)` (infra R já existe)
- [ ] 3.2 Reescrever `subsec:hlm` (l.370–433): equações, "interceptos fixos de UPA" sai, ICC por
      nível conforme o modelo escolhido
- [ ] 3.3 Step-up completo: −2LL, AIC, BIC e LR test M0→M1→M2→M3 (refit ML para efeitos fixos;
      REML só para componentes de variância) — preencher "AIC N/D"
- [ ] 3.4 Teste de inclinação aleatória de `negro` por UF (LR, `run_hlm_m3_random_slope.py` já existe)
- [ ] 3.5 Gráfico dos BLUPs de UF (caterpillar) — vira uma das figuras do núcleo
- [ ] 3.6 Parágrafo OVB: o que M1 omite (qualidade da escola, habilidade, redes), direção provável
      do viés; incluir `konfound_hlm_vs_ols.tex` (já rodado, ausente do relatório)
- [ ] 3.7 Padronizar rótulos de educação entre tabelas HLM e OB

## Bloco 4 — GLMM de verdade (🖥, ⏱ ½ dia)

- [ ] 4.1 Alimentar `tcc/scripts/gerar_tabela_glmm.py` com a saída do glmer
      (`scripts/R/logit_multinivel_glmm.R`): OR, IC, ICC_UPA = τ/(τ+π²/3), LR test vs logit pooled
- [ ] 4.2 Manter o logit-FE de UF (+cluster-UPA, item 2.5) como coluna de robustez
- [ ] 4.3 AUC/ROC + matriz de confusão no cutoff ótimo (sensibilidade/especificidade) para os 3
      desfechos; Hosmer-Lemeshow; comparação de AUC M1→M3 (FAV-43)
- [ ] 4.4 Reescrever subsec GLMM (l.735–742) e legenda da tabela conforme o modelo real

## Bloco 5 — Bad control e reflexo (🖥, ⏱ ½ dia)

- [ ] 5.1 OB **sem** ocupação/formalidade/horas (especificação M3) ao lado da OB de acesso; comparar
      com Soares (2009) só nessa versão (l.852–859)
- [ ] 5.2 Nomear M4/OB-acesso como "limite inferior descritivo" em Resultados, Discussão e Conclusão
- [ ] 5.3 XGBoost sem `media_renda_upa` ou com média leave-one-out; novo ranking SHAP
- [ ] 5.4 Retirar/reescrever "onde se mora supera quanto se estudou" (l.670–671) conforme 5.3
- [ ] 5.5 Limitações: parágrafo COP (renda > 0 condiciona no desfecho; direção do viés; Heckman
      λ = −1,96 no branch extenso) (MHE-32)
- [ ] 5.6 Parágrafo QR vs RIF: condicional (fanning-out) vs incondicional (sticky floor); linguagem
      sobre distribuições, não indivíduos (MHE-72/73)
- [ ] 5.7 VIF (l.808–810): "descartam multicolinearidade" → explicar que VIF 22 está em
      `educ_missing` (bloco educacional, esperado) e mostrar β_negro estável sem ela
- [ ] 5.8 Diagnósticos OLS das regressões de grupo da OB: Breusch-Pagan e RESET (apêndice de uma linha)
- [ ] 5.9 N e SE nas tabelas RIF-OB e interseccional; frase explicando "dotações −8,9 %" da mulher branca

## Bloco 6 — Linguagem (✍, ⏱ 1 h)

- [x] 6.1 (feito junto com os blocos 0/1 — Resumo, Abstract, Introdução, Conclusão) "comprova" (l.216, l.971) → "mostra/estima"; "determinam" (l.976); "atribuível à
      discriminação direta" (Resumo l.129–131 e abstract l.177–179) → "não explicado por
      observáveis — limite inferior da discriminação"
- [x] 6.2 "discriminação pura pós-ocupação" (l.1034) → conforme 5.2
- [ ] 6.3 Limitações: lista item a item das hipóteses (CIA, bad controls, reflexo, RE, pesos,
      cluster, COP) e o que acontece se falharem (MHE-90)

## Bloco 7 — Storytelling (✍ + figuras, ⏱ 1 dia)

- [x] 7.1 (frase-síntese única já inserida na Conclusão; falta a do Resumo → 7.2) Grande Ideia única (uma frase, um número) no Resumo e na Conclusão; reduzir as quatro
      caixas de citação (l.1001–1023) a uma
- [ ] 7.2 Página "Em três minutos" após o Resumo (contexto → desequilíbrio → 4 achados → o que muda)
- [ ] 7.3 Quatro figuras do núcleo: (1) barras horizontais β_negro M1→M4 com IC; (2) cascata
      gap → dotações → retornos (OB, com e sem ocupação); (3) β(τ) com faixa de IC em pequenos
      múltiplos global/homens/mulheres + barras 100 % dotação/retorno por quantil (QR/RIF);
      (4) barras horizontais de OR com IC, 3 desfechos (GLMM)
- [ ] 7.4 Reduzir SHAP a beeswarm + um waterfall
- [ ] 7.5 Paleta: cinza + azul de destaque em todas as figuras; vermelho só no dado da frase-síntese;
      mesmo grupo = mesma cor; colormap do SHAP ajustado
- [ ] 7.6 Legendas: primeira frase = achado (título de ação); manter as notas "Como ler"
- [ ] 7.7 Slides: títulos de ação nos 10 slides-tópico; lógica horizontal (só os títulos contam a
      história); Bing-Bang-Bongo; paleta de 11 → 3 cores
- [ ] 7.8 Tabela de balanceamento (covariáveis por raça) e checagem de suporte comum na Descritiva

## Bloco 8 — ML (🖥, ⏱ 2 h)

- [ ] 8.1 5-fold CV em subamostra (só para escolher max_depth / learning_rate / n_estimators);
      refit final na população; reportar média ± dp do R² nos folds — **pedir confirmação antes,
      pois usa subamostra**
- [ ] 8.2 Métrica na unidade original: MAE retransformado (mediana do erro absoluto em R$)

## Fechamento

- [ ] F.1 `./tcc/run_tcc.ps1` completo; `verificar_analises.py` com 0 ALTO
- [ ] F.2 Invocar `revisao-livros` para a revisão qualitativa final; registrar em `tcc/revisoes/`
- [ ] F.3 Regerar relatório enxuto, apresentação e Word; conferir PDF
- [ ] F.4 Commit por bloco (`fix(tcc): bloco N — …`)
