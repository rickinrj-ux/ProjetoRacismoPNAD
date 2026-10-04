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
- [x] 1.7 (restam 2 células `(0.0000)` — idade; resolver na tabela nova do Bloco 3) Substituir `(0.0000)` por notação com mais casas; trocar asteriscos por IC 95 % nas
      tabelas do núcleo (MHE-85)

## Bloco 2 — Erros-padrão (🖥, ⏱ ½ dia de máquina + 1 h) — ✅ concluído em 2026-09-20

Lições: rodar UM job pesado por vez (o watchdog de memória do ambiente mata processos com >~20 GB somados); OLS em forma fechada (X'X) e resultados leves em vez de objetos do statsmodels; bootstrap de QR em paralelo (joblib).

- [x] 2.1 `run_hlm_serie_completa.py`: OLS M1–M4 com `cov_type="cluster"` por **UPA** (além do
      cluster-UF já existente); remover `_UF` das fórmulas OLS que têm `C(UF_str)` (colinearidade
      → intercepto 5,5e7 em `hlm_serie_completo.csv`)
- [x] 2.2 Tabela HLM: coluna de SE cluster-UPA ao lado do SE do modelo; para cluster-UF (27 < 42)
      wild-cluster bootstrap ou t com g−k g.l.; nota na Metodologia (MHE-81/82)
- [x] 2.3 (SE via bootstrap em blocos por UPA sobre estatísticas suficientes, 500 réplicas; OB em duas especificações) `run_oaxaca_blinder.py`: OLS por grupo com `cov_type="cluster"` (UPA); bootstrap em
      blocos por UPA (B=200) para dotação/retorno — conferir de onde vêm os SE de `ob_acesso.tex`
      e citar o script certo
- [x] 2.4 (bootstrap em blocos por UPA, m-de-n, 200 réplicas em paralelo; SE de β(τ) na tabela; Z=−16,95 escalado / −2,94 bruto) `run_regressao_quantilica.py`: bootstrap em blocos por UPA para β(τ) e para o contraste
      q90−q10 (hoje: 5 % da amostra) — ou declarar no texto que o SE é conservador
- [x] 2.5 `run_glmm_glassceil.py`: `cov_type="cluster"` por UPA nos logits; IC recalculado
- [x] 2.6 (WLS V1028: β=−0,0967 vs −0,1009; gap 9,2% vs 9,6%) Robustez com peso amostral: M3 OLS cluster-UPA com `weights=V1028`; frase na Metodologia
      dizendo que os demais modelos são não ponderados (MHE-30/FAV-09)

## Bloco 3 — HLM honesto (🖥, ⏱ 1 dia) — ✅ concluído em 2026-09-20

Resultado-chave: ICC_UPA = 0,369 (37% da variância entre bairros); gap agregado 19,1% → dentro do mesmo bairro 10,6% (mediação pela segregação residencial = 47,0%); gap líquido M3 = 10,2%; M4 = 7,0%; a penalidade varia entre bairros (DP 0,17).

- [x] 3.1 (opção a, implementada como HLM de 2 níveis indivíduo→UPA com efeitos fixos de UF — `run_hlm_stepup.py`; o antigo RE-UF fica como robustez) **Escolher**: (a) reescrever como 2 níveis (indivíduo/UF) + contexto de UPA, usando
      `run_hlm_m4.py` (groups=UPA) como modelo de UPA; ou (b) estimar 3 níveis em lme4
      `(1|UF/UPA)` (infra R já existe)
- [x] 3.2 Reescrever `subsec:hlm` (l.370–433): equações, "interceptos fixos de UPA" sai, ICC por
      nível conforme o modelo escolhido
- [x] 3.3 Step-up completo: −2LL, AIC, BIC e LR test M0→M1→M2→M3 (refit ML para efeitos fixos;
      REML só para componentes de variância) — preencher "AIC N/D"
- [x] 3.4 (inclinação aleatória de `negro` por UPA, não por UF: τ²₁=0,029, DP 0,17, LR=38.943) Teste de inclinação aleatória de `negro` por UF (LR, `run_hlm_m3_random_slope.py` já existe)
- [x] 3.5 (figura `hlm_efeitos_uf_blup_upa.png`: efeitos fixos de UF + histograma dos BLUPs de UPA) Gráfico dos BLUPs de UF (caterpillar) — vira uma das figuras do núcleo
- [x] 3.6 Parágrafo OVB: o que M1 omite (qualidade da escola, habilidade, redes), direção provável
      do viés; incluir `konfound_hlm_vs_ols.tex` (já rodado, ausente do relatório)
- [x] 3.7 Padronizar rótulos de educação entre tabelas HLM e OB

## Bloco 4 — GLMM de verdade (🖥, ⏱ ½ dia) — ✅ concluído em 2026-09-20

Resultado-chave (glmer, RE de UPA + UF fixo, população): ICC latente 0,20 (cargo) a 0,35 (top 10%); OR M2 = 0,699 (cargo), 0,688 (top 20%), 0,654 (top 10%); AUC 0,83–0,88; E-values 2,2–2,4; logit-FE cluster-UPA reproduz. Lição: um modelo por processo R (`--one`) — o R não devolve memória entre ajustes.

- [x] 4.1 Alimentar `tcc/scripts/gerar_tabela_glmm.py` com a saída do glmer
      (`scripts/R/logit_multinivel_glmm.R`): OR, IC, ICC_UPA = τ/(τ+π²/3), LR test vs logit pooled
- [x] 4.2 Manter o logit-FE de UF (+cluster-UPA, item 2.5) como coluna de robustez
- [x] 4.3 AUC/ROC + matriz de confusão no cutoff ótimo (sensibilidade/especificidade) para os 3
      desfechos; Hosmer-Lemeshow; comparação de AUC M1→M3 (FAV-43)
- [x] 4.4 Reescrever subsec GLMM (l.735–742) e legenda da tabela conforme o modelo real

## Bloco 5 — Bad control e reflexo (🖥, ⏱ ½ dia) — ✅ concluído em 2026-09-22

Achado colateral: a decomposição interseccional do entregável usava só as ~31% de observações com
`educ_ord` registrado (legenda dizia 'população completa'); refeita na amostra do núcleo, o gap da
mulher negra vs. homem branco passa de 96,4% para 80,6% e a penalidade interseccional extra de
9,5 p.p. para 4,6 p.p.

- [x] 5.1 (tabela OB com (A) sem ocupação: 28,4% não explicado / (B) acesso: 16,2%; Resumo, Abstract, subseção e comparação com Soares atualizados) OB **sem** ocupação/formalidade/horas (especificação M3) ao lado da OB de acesso; comparar
      com Soares (2009) só nessa versão (l.852–859)
- [x] 5.2 Nomear M4/OB-acesso como "limite inferior descritivo" em Resultados, Discussão e Conclusão
- [x] 5.3 (LOO: R² 0,617→0,614; sem renda de vizinhança: 0,578; |SHAP| da raça 0,030 → 0,029) XGBoost sem `media_renda_upa` ou com média leave-one-out; novo ranking SHAP
- [x] 5.3b (feito no bloco 4: o glmer usa %negro/desemprego/educação da UPA, sem `media_renda_upa`; vínculo só no M3, rotulado limite inferior) `run_glmm_glassceil.py`: o logit também usa `media_renda_upa_z` (reflexo — pior nos
      desfechos de renda top-20/top-10, que são função da própria renda) e `emprego_formal`,
      `setor_publico`, `conta_propria`, `trab_domestico` já no M1 (bad controls para o desfecho
      de acesso). Decidir: retirar `media_renda_upa_z` (ou leave-one-out) e mover formalidade
      para um M-extra explicitamente rotulado "dentro do vínculo"
- [x] 5.4 Retirar/reescrever "onde se mora supera quanto se estudou" (l.670–671) conforme 5.3
- [x] 5.5 Limitações: parágrafo COP (renda > 0 condiciona no desfecho; direção do viés; Heckman
      λ = −1,96 no branch extenso) (MHE-32)
- [x] 5.6 Parágrafo QR vs RIF: condicional (fanning-out) vs incondicional (sticky floor); linguagem
      sobre distribuições, não indivíduos (MHE-72/73)
- [x] 5.7 VIF (l.808–810): "descartam multicolinearidade" → explicar que VIF 22 está em
      `educ_missing` (bloco educacional, esperado) e mostrar β_negro estável sem ela
- [x] 5.8 Diagnósticos OLS das regressões de grupo da OB: Breusch-Pagan e RESET (apêndice de uma linha)
- [x] 5.9 (bootstrap em blocos por UPA, 150 réplicas; descoberto que a tabela interseccional rodava em 31% da PEA — refeita na população) N e SE nas tabelas RIF-OB e interseccional; frase explicando "dotações −8,9 %" da mulher branca

## Bloco 6 — Linguagem (✍, ⏱ 1 h)

- [x] 6.1 (feito junto com os blocos 0/1 — Resumo, Abstract, Introdução, Conclusão) "comprova" (l.216, l.971) → "mostra/estima"; "determinam" (l.976); "atribuível à
      discriminação direta" (Resumo l.129–131 e abstract l.177–179) → "não explicado por
      observáveis — limite inferior da discriminação"
- [x] 6.2 "discriminação pura pós-ocupação" (l.1034) → conforme 5.2
- [x] 6.3 Limitações: lista item a item das hipóteses (CIA, bad controls, reflexo, RE, pesos,
      cluster, COP) e o que acontece se falharem (MHE-90)

## Bloco 7 — Storytelling (✍ + figuras, ⏱ 1 dia) — ✅ concluído em 2026-09-22

Quatro figuras do núcleo geradas dos csv por tcc/scripts/gerar_figuras_nucleo.py (não reestimam nada);
página "Em três minutos"; SHAP reduzido a beeswarm + 1 waterfall; 19 títulos de ação nos slides.

- [x] 7.1 (frase-síntese única já inserida na Conclusão; falta a do Resumo → 7.2) Grande Ideia única (uma frase, um número) no Resumo e na Conclusão; reduzir as quatro
      caixas de citação (l.1001–1023) a uma
- [x] 7.2 Página "Em três minutos" após o Resumo (contexto → desequilíbrio → 4 achados → o que muda)
- [x] 7.3 Quatro figuras do núcleo: (1) barras horizontais β_negro M1→M4 com IC; (2) cascata
      gap → dotações → retornos (OB, com e sem ocupação); (3) β(τ) com faixa de IC em pequenos
      múltiplos global/homens/mulheres + barras 100 % dotação/retorno por quantil (QR/RIF);
      (4) barras horizontais de OR com IC, 3 desfechos (GLMM)
- [x] 7.4 Reduzir SHAP a beeswarm + um waterfall
- [x] 7.5 (figuras novas em cinza + azul; paleta dos slides com vermelho só como destaque) Paleta: cinza + azul de destaque em todas as figuras; vermelho só no dado da frase-síntese;
      mesmo grupo = mesma cor; colormap do SHAP ajustado
- [x] 7.6 Legendas: primeira frase = achado (título de ação); manter as notas "Como ler"
- [x] 7.7 Slides: títulos de ação nos 10 slides-tópico; lógica horizontal (só os títulos contam a
      história); Bing-Bang-Bongo; paleta de 11 → 3 cores
- [x] 7.8 (tabela de balanceamento + suporte comum: 97,3% das UPAs mistas; maior desequilíbrio é o bairro, d = −1,18) Tabela de balanceamento (covariáveis por raça) e checagem de suporte comum na Descritiva

## Bloco 8 — ML (🖥, ⏱ 2 h) — ✅ concluído em 2026-09-22

A configuração antiga (max_depth=6) era a penúltima de seis; adotada a escolhida por CV (max_depth=10)
e todo o pipeline de ML/SHAP reexecutado para manter tabela, ranking e figuras coerentes.

- [x] 8.1 (CV 5-fold na POPULAÇÃO, sem amostrar; busca em partição de validação dentro do treino: max_depth=10 vence, R² 0,628±0,001 vs 0,614±0,001) 5-fold CV em subamostra (só para escolher max_depth / learning_rate / n_estimators);
      refit final na população; reportar média ± dp do R² nos folds — **pedir confirmação antes,
      pois usa subamostra**
- [x] 8.2 (erro mediano R$ 538/mês = 37% do rendimento, com correção de Duan) Métrica na unidade original: MAE retransformado (mediana do erro absoluto em R$)

## Fechamento

- [x] F.1 (verificador: 0 ALTO, 0 MÉDIO; restam 2 BAIXO e 4 INFO, justificados na revisão) `./tcc/run_tcc.ps1` completo; `verificar_analises.py` com 0 ALTO
- [x] F.2 (revisão qualitativa final em `tcc/revisoes/revisao_2026-09-22.md`: 1 ALTO, 5 MÉDIO e 6 BAIXO, todos corrigidos na hora — nenhum exigiu decisão do autor) Invocar `revisao-livros` para a revisão qualitativa final; registrar em `tcc/revisoes/`
- [x] F.3 (relatório 38 páginas, 0 erros / 0 refs indefinidas / 0 `(??)` / 0 placeholders) Regerar relatório enxuto, apresentação e Word; conferir PDF
- [x] F.4 Commit por bloco (`fix(tcc): bloco N — …`)

### Lições da revisão final (2026-09-22)

- Nota de tabela escrita em *raw string* deixou `{fmt(...)}` chegar ao PDF: todo texto com
  número tem de passar por f-string ou por substituição explícita — e o verificador passou a
  procurar `{fmt(` e `@@` no `.tex` final.
- Heredoc (`python - <<'EOF'`) continua corrompendo barras invertidas dentro de literais
  Python: scripts de patch devem ser escritos com a ferramenta Write e só então executados.
- `\resizebox` em tabela larga tem de ser aplicado **no gerador** e no `.tex` já materializado;
  caso contrário a próxima execução do gerador desfaz a correção.

---

# Rodada de entrega (aberta em 2026-10-02)

Origem: releitura completa (`releitura_2026-10-02.md`: 80 itens do texto + 40 dos decks/Word),
erro da escolaridade (V3009A → VD3004), renda nominal (deflator + efeito de ano) e auditoria
`/adhd` do wrangling (join, layout e códigos: limpos). Regra: nenhum número digitado —
`caca_fosseis.py --vivos` e `conferir_numeros_entregaveis.py` em zero antes de dar por pronto.

Legenda: 🖥 reestimação · ✍ texto/gerador · 🎨 layout · ❓ decisão do autor

## Bloco E0 — Reestimação completa (🖥, ⏱ ~16 h de máquina) — em andamento desde 12:50

- [x] E0.1 VD3004 extraída dos 40 ZIPs; features reconstruídas; `checar_escolaridade.py` OK
      (cobertura 100%; ≥ superior 17,9%; brancos 25,6% × negros 12,6%; renda real +0,16 2016→25)
- [x] E0.2 (fila principal 26/26 OK em 03/10 10:27; pós-reestimação OK 10:51) `fila_reestima.ps1`: HLM (7 degraus) → GLMM 12 → RIF/SE → RIF pontual → OB/QR →
      QR por área → série OLS → Oaxaca → logit-FE → Konfound → CV → VIF → Gini → HLM 3 níveis
      → grupo raça×gênero → série anual M3 → tendência → SHAP
- [x] E0.3 (tcc/revisoes/antes_depois_2026-10-03.md; todos convergiram; ob_acesso.csv só muda no E6, gerado com o relatório) Conferir convergência de todos os modelos e comparar com `_backup_pre_educ/`
      (tabela antes × depois para o autor)
- [x] E0.4 `run_konfound_evalues.py` neutralizado (legado, só com `--legado`): β digitados e logit-FE; o TCC usa hlm_stepup_konfound.csv e gerar_tabela_glmm.py
      (β M1 −0,215 × −0,112) — hoje fora dos entregáveis, mas produz figura inconsistente

- [x] E0.5 (feito 03/10: retas no corpo + slide do diploma) Escada educacional (pedido 02/10): `run_hlm_negro_por_educ.py` (M3 + negro:C(nivel),
      5 níveis, LR vs M3) roda pela `fila_pos_reestima.ps1` (espera o FIM_FILA). tab2 ganhou a
      dimensão "Nível (núcleo)" (gap bruto, entra pela fila_loo2/tabelas_compl). Texto e figura
      `fig:hlm_negro_educ` montados do csv em `gerar_relatorio_enxuto.py` (antes do parágrafo dos limites)
      + figura de retas por nível (`hlm_negro_por_educ_retas.png`) + `run_hlm_negro_educ_uf.py`
      (UF × nível, HLM V-known de Raudenbush & Bryk cap. 7: OLS within-UPA por UF + efeitos aleatórios
      DerSimonian-Laird por nível; mapa de calor de BLUPs e τ por nível). Falta: texto e entrada no
      documento das duas figuras novas (depois dos números)
- [x] E0.6 (feito 03/10) Figuras de efeitos aleatórios (pedido 02/10): `tcc/scripts/gerar_figuras_efeitos_aleatorios.py`
      → `hlm_variancia_escada.png` (τ², σ² e explicada M0→M4; já gerada com os números novos) e
      `hlm_encolhimento.png` (BLUP do M0 × desvio bruto, λ = τ²/(τ²+σ²/n)). Falta: entrar no
      documento e no deck da Defesa (Fávero), com texto condicional

- [x] E0.7 Escada (03/10): within-UPA nacional = HLM (9,4×9,6% … 1,1×1,1%) — o desenho não muda a
      conclusão; a média do mapa é ENTRE ESTADOS (DL), não do país: rótulo corrigido, mapa regerado
      após a fila_escada. LR da escada rodando (fila_escada.ps1)

- [x] E0.8 (03/10) Regressão do LOO do desemprego na reconstrução de 02/10: corrigido em
      `feature_engineering.py` (UPA e UF), teste em `checar_escolaridade.py`; impacto medido nulo
      em β_negro (5ª casa); por decisão do autor, sem reestimar. Na próxima reconstrução da base o
      teste passa

## Bloco E1 — Texto que a correção da escolaridade e da renda invalida (✍)

- [x] E1.1 (texto-base: parágrafo de renda deflacionada + efeito de ano + jornada habitual; parágrafo novo da VD3004; tabela de simetria; deck s2/s3) Método: escolaridade = VD3004 (nível alcançado) + pós pela V3009A; dummies
      cumulativas de conclusão de ciclo; renda deflacionada (deflator oficial PNADC, reais do
      2º tri/2026) e efeito de ano em todos os métodos; jornada é a HABITUAL (VD4031)
- [x] E1.2 (base e Guia; a pergunta da fragilidade passou a bad control) Apagar o parágrafo "Cobertura da variável de escolaridade" (31%, `educ_missing`,
      sensibilidade) do texto-base e do Guia (l. ~633); tirar `_EDUC_SENS_TXT`/`EDUC_COBERTURA`
- [x] E1.3 (rótulos "ou mais") Tabela de balanceamento sem a linha "Escolaridade não registrada"; marcadores
      `@@BAL_MISS_*@@` e o parágrafo que os usa
- [x] E1.4 (@@VIF_ABERTURA@@ condicional ao csv) Parágrafo do VIF (`@@VIF_MISS@@`) — reescrever conforme o VIF com dummies cumulativas
- [x] E1.5 (parágrafo de pesos já existe e é regravado pelo hlm_serie; deflator por UF no método) Limitações: pesos amostrais (V1028) não usados nas estimativas; deflator por UF
- [x] E1.6 (tab1/tab2 entram na fila_loo2; R$ do ML e slide 4 dizem a base) Tabela descritiva (`tab1`, `tab2`) e slide de descritivos: refazer em reais constantes

## Bloco E2 — Decisões do autor (❓, recomendação de texto pronta para aprovar, após E0)

- [x] E2.1 (aplicado 03/10 nos geradores; entra na regeneração da fila_e2: Defesa s11 — 17,3 dos 23,4 pontos ficam dentro da ocupação; porta = 6,1) "A discriminação opera sobretudo no acesso" × números (OB: porta 12,4 pp × dentro
      16,5 pp; HLM: ⅓ × ⅔) — reformular a tese central
- [x] E2.2 (03/10: M1 com UF = −0,0645 → mediação pelo bairro 41,6% contra 39,5% sem UF: a escada da tabela é conservadora; nota condicional na Tab. 5; agregado sem UF = 20,1%) Escada do HLM não aninhada (agregado com UF fixa; M1 sem; M3 com) — mediação de 47%
      mistura duas mudanças; reestimar um degrau (🖥) ou explicitar
- [x] E2.3 (aplicado 03/10 nos geradores; entra na regeneração da fila_e2: em log-pontos 0,592 < 0,182+0,447 → sub-aditivo; sai a "penalidade extra +4,4 pp") Interseccionalidade: "+4,6 pp acima da soma" é artefato de escala; em log-pontos é
      sub-aditivo (coerente com o GLMM) — leitura única em resumo, abstract, conclusão, decks
- [x] E2.4 (aplicado 03/10 nos geradores; entra na regeneração da fila_e2: M3 = limite superior da penalidade direta; M4 = inferior; p. 13 corrigida) Limite superior × inferior (M3/M4/OB) — um enquadramento só
- [x] E2.5 (concluído 04/10 05:21: (A) ≡ M3 em Oaxaca/QR/RIF — OB retornos 17,9% (A) e 15,4% (B); RIF retornos 26,5% q10 → 8,9% q90; QR 4,3% q10 → 8,4% q90, KB Z = −25,9; regeneração 07:48 com portões OK) com log_horas + urbano + UF na (A)/M3; fila_e2 rodando, QR ~4 h) Horas na especificação (A) do Oaxaca × "controles do M3" × limitações (bad control)
- [x] E2.6 (aplicado 03/10 nos geradores; entra na regeneração da fila_e2: sai — fonte regional_hlm.csv de 16/05; hoje DF é 19º/27 e N/NE = demais) Resultados regionais citados sem tabela (capitais × interior, DF, N/NE): incluir ou tirar
- [x] E2.7 (aplicado 03/10 nos geradores; entra na regeneração da fila_e2: E-value com √OR para desfecho comum (acesso ≈1,45; top20 ≈1,54); benchmark "mais forte que superior" sai — superior tem OR≈6,4) E-value para desfecho comum (√OR) e benchmark das covariáveis
- [x] E2.8 (aplicado 03/10 nos geradores; entra na regeneração da fila_e2: "na base o preço pesa 3,5× mais que no topo" — Defesa s15, Executiva s7) "Na base, a maior parte do gap é preço" (35,5% não é maioria) — 4 entregáveis
- [ ] E2.9 (AGUARDA o e-mail real do orientador) E-mail real do orientador na folha de rosto
- [x] E2.10 (aplicado 03/10 nos geradores; entra na regeneração da fila_e2: Lei 15.142/2025 revogou a 12.990/2014; reserva de 30%) Lei 12.990/2014: conferir se foi substituída (Lei 15.142/2025?)

- [x] E2.16 (aprovado e aplicado 04/10: frase_cbo_mulher_negra no params; TCC (parágrafo da entrada + legenda), Defesa, Executiva, Guia, narrativa; figura com painel por grande grupo CBO — GLMM por CBO concluído 03/10 23h, grupo_rg_por_cbo.csv — OR da mulher negra vs HB: dirigente 0,63; profissional 1,36 (MB 1,42); técnico 0,87; administrativo 1,96 (MB 2,20); CBO 1–2 1,04 (MB 1,17). entra na regeneração da fila_e2) NOVO (03/10, pedido do autor) — "mulher negra alçada no acesso" (OR 1,31 em CBO 1–4)
      é composição de ocupações feminizadas: dirigentes 2,3% (HB 5,9%), mas apoio administrativo
      10,6% (HB 5,4%) e profissionais 12,8% (HB 10,5%, puxado por ensino/saúde); dentro do mesmo
      grande grupo ela ganha a metade (profissionais: mediana R$ 3.614 × R$ 6.799). Propor:
      GLMM por grande grupo CBO (1, 2, 3, 4 separados) e reler o achado em todos os entregáveis.

- [x] E2.12 (aprovado 02/10: fundamental entrou em Oaxaca, OB/QR, QR por área, RIF e logit-FE, antes de a fila chegar; perfis contrafactuais do logit-FE corrigidos para dummies cumulativas) Especificação: Oaxaca, QR e RIF não têm educ_fund_completo (HLM, GLMM e OB
      interseccional têm). Com dummies cumulativas, a referência mistura sem instrução com
      fundamental completo/médio incompleto. Incluir antes que a fila_reestima chegue em rif/ob_qr?

- [x] E2.15 (aprovado e aplicado 03/10: retas no corpo, parágrafo "O diploma quase iguala o salário, mas não abre a porta" na Discussão, abertura do parágrafo de políticas da Conclusão, slide 9b da Defesa — tudo condicional aos números)
- [x] E2.14 (aprovado e aplicado 03/10: frase_sintese/titulo_bairro/frase_diploma em params_nucleo, condicionais; Resumo, Abstract, Conclusão, Defesa s2/s6/s9/s15/s23, Executiva, Guia, figura do step-up) MANCHETE MUDA (preliminar, 02/10 14:17): com a escolaridade correta e a renda
      deflacionada, β_negro do M3 = −0,0629 (gap ≈ 6,1%) contra −0,1102 (10,4%) antes; M1 −0,0669.
      Reler tese, resumo, títulos e decks quando a fila fechar (todos já vêm do params; o
      risco são as frases qualitativas: "um em cada dez", "metade do gap" etc.)

- [x] E2.17 (aprovado e aplicado 04/10, pedido do autor) Arco narrativo + conceito + críticas/propostas, pelas regras do template oficial: 'Considerações Iniciais' (renomeada; conceito de racismo estrutural por Almeida/Hasenbalg e as 3 marcas; roteiro pela trajetória; 552 palavras ≈1,6 p.); pontes nos Resultados e GLMM antes da QR; Discussão com críticas C1–C4 e propostas P1–P5 (leis no .bib); Conclusão em 2 parágrafos sem citação; Resumo/Abstract reescritos (214/207 palavras); Defesa com slides de críticas e de propostas. Módulo: tcc/scripts/tcc_normas_narrativa.py
- [~] E2.13 (04/10: favero2024, geron2021, wilm2026 e 7 leis/decretos no BIB de scripts/geradores/gerar_relatorio_tcc.py — o relatorio_tcc.bib é REGERADO a cada rodada, editar o arquivo à mão se perde; 41 referências no Word; CHEN completo; FALTA Alencar 2024 — apostila não pública), geron2021 (2. ed., Alta Books, trad. C. Ravaglia) e wilm2026 (IPS Brasil 2026, Imazon) no .bib e citados; FALTA Alencar 2024 — apostila não pública) Obras citadas sem entrada no .bib — preciso dos dados exatos (não invento referência):
      Alencar (2024), apostila "Árvores, Redes e Ensembles I" USP/ESALQ — nome completo do autor;
      Géron (2021) — edição usada (original ou tradução Alta Books); Imazon e parceiros (2026) —
      título do relatório do IPS municipal; Fávero & Belfiore (cap. 12) — edição do livro

## Bloco E3 — Correções de texto da releitura (✍, MÉDIO/BAIXO)

- [x] E3.1 (tabela de ajuste, figura, Guia e Defesa) Rótulos A1–A4 no GLMM em figura, tabela, Guia e decks (hoje M1–M4)
- [x] E3.2 (seis quantis; topo = q90 em todo lugar; conclusão condicional; @@QR_SEXO@@ descreve as colunas por sexo a partir do csv; q95 por área fica para o E2.6) QR: declarar τ = 0,95 no método; conclusão em termos condicionais; comentar coluna por sexo
- [x] E3.3 (texto e decks; narrativa social mantém o coloquial) Odds × probabilidade ("30% menos chance" → "chances 30% menores" ou AME)
- [x] E3.4 (@@G_FE_TXT@@ e @@G_HL_QUEDA@@ calculados dos csv) "logit-FE reproduz os mesmos OR" vale a partir do A2; "HL cai à metade" → 30–45%
- [x] E3.5 ("teto de vidro entre pares, piso pegajoso na renda do país: duas perguntas, dois padrões" em figura, legenda, Guia e Executiva; QR deixa de ser "gap bruto") Teto de vidro × piso pegajoso: uma formulação (figura, texto, conclusão)
- [x] E3.6 (legenda da RIF declara os controles = Oaxaca sem ocupação + UF; frase compara RIF q50 com OB (A), não (B); linguagem causal da legenda removida) RIF × Oaxaca: declarar especificação e conciliar (27,8% × 16,5%)
- [x] E3.7 ("importância preditiva não desprezível"; RF com folha mínima e max_features) "Raça preditora de primeira ordem" → "não desprezível"; RF: informar max_features
- [x] E3.8 (Heckman deixa de ser resultado e vira extensão, texto e Guia; SNA/TOPSIS/k-means já não aparecem) Resíduos da versão estendida (Heckman, SNA, k-means, TOPSIS) nas Limitações
- [x] E3.9 (IPQV = perda; MQO sem pesos nomeado; N por método na seção de dados; top 10% não é acesso) IPQV ("perda de qualidade de vida"), transição dos dois Gini, N de cada método na seção
      de dados, MQO equivalente na nota de pesos, top 10% ≠ acesso
- [x] E3.10 (ordem: HLM, mediação, OB, QR/RIF, GLMM, interseccional, ML, VIF; Como ler duplicado sai do texto; nota da CV enxuta e sem "sem aumentar o sobreajuste"; chamada de float após título de seção vai para depois do título) Subseção de mediação no lugar certo; um só "Como ler" por tabela; duplicações
      (R$ 540, variação entre folds); frase solta antes da tabela interseccional ("três grupos")
- [x] E3.11 (frases suavizadas; H1–H3 rotuladas, remissões alinhadas — bairro é H1 — e retomada condicional na Conclusão) Linguagem causal residual (l. 1520, 1542, 1610, 1573, 519); H1–H3 rotuladas e retomadas
- [x] E3.12 ("Vale guardar a frase" fica só na 1ª; "centrada" unificado; "as dummies"; itálico tirado também das tabelas via \input; 4 citações viram \cite; travessões —/--- saem iguais no PDF, mantidos. Bib: ver E2.13) BAIXO: "dupla desvantagem", gênero de "dummies", travessões, "Vale guardar a frase" ×5,
      grafias (centrada/centralizada, 11°), \emph perdido no gerador de normas, citações em texto
      puro → \cite, obras faltantes no .bib (Alencar 2024, Géron 2021, Imazon 2026)

## Bloco E4 — Word de entrega (🎨, conversor `gerar_tcc_normas_docx.py`)

- [x] E4.1 (03/10: 8 pt com 7+ colunas, largura mínima pela maior palavra e rótulos A1–A4 — Tab. 9 e 10 cabem em retrato; paisagem dispensada) Larguras de coluna fixas nas tabelas largas (4, 6A, 11, 12, 13, 14, 3); paisagem nas p. 32–34
- [x] E4.2 Filtrar `\cmidrule` cru (Tabelas 9 e 10)
- [x] E4.3 Chamadas de nota de rodapé em sobrescrito (hoje "0,69714")
- [x] E4.4 (``\emph{Como ler:}`` virava ``\emphNota``; painéis saem do table; subfigure herda a largura) Título "Referências"; notas que começam com ":"; legenda duplicada da Tabela 6;
      figura de waterfalls partida em duas páginas

## Bloco E5 — Decks, Guia e figuras (🎨)

- [x] E5.1 (s3 "multinível" e título contido; s5 faixas sem sobreposição; s9 nota dentro da barra longa; s10 só a figura do título em largura total; s12 cartões compactos e "chance (odds)"; s17 nome inteiro e |SHAP| sem quebra; s19 caixas mais baixas; s22 numerado e convergência condicional à inclinação — conferir visualmente no E6) Defesa: s3 ("mestrado", cabeçalho cortado), s5/s12/s15/s19 caixas transbordando,
      s9 anotação cortada, s10 figuras ilegíveis, s17 cartões quebrando números, s22 sem número
- [x] E5.2 (s3 "com todos os registros"/UPAs; s6 título em uma linha e remissão ao GLMM; s7 figura com altura limitada) Executiva: s3 "sem amostragem", s6 título sobre subtítulo e "(slide anterior)" errado,
      s7 texto sobre os eixos
- [x] E5.3 (coluna passa a ICC do M2) Guia: tabela do GLMM mistura A2 (OR/AME) com A1 (ICC/AUC)
- [x] E5.4 (títulos em português, vírgula via `src/figuras_ptbr.py`, laranja só na raça; fig1 em R$ constantes; composição com `ativar()` no savefig) Figuras SHAP (beeswarm e waterfalls) em português e vírgula decimal; figuras do deck
      com ponto decimal (densidade, composição)

- [x] E5.5 (02/10: as três APROVADAS pelo autor — SHAP 50 mil, KDE da fig1, 20% das Mincer) Amostragens pré-existentes a confirmar com o autor (regra: nunca amostrar sem ok):
      SHAP em 50 mil casos do treino (`run_ml_shap.py`, SHAP_SAMPLE); KDE da fig1 com
      reamostragem ponderada de 50 mil; `gerar_tabelas_complementares.py` sorteia 20% para
      as Mincer tab3/tab4 (não usadas no TCC)

## Bloco E6 — Regeneração e portões (✍, ⏱ ~30 min de máquina)

- Nota (02/10): `fila_loo2.ps1` ganhou `tabelas_compl` (tab1/tab2 → MED_BR, GAP_MEDIANA…) e
  `composicao` — estavam fora de toda fila e não receberiam a deflação. Rodar com
  `-Desde tabelas_compl` (os passos de análise anteriores já estão na fila_reestima).

- [x] E6.1 (03/10 18:32: 21 passos OK; RIF e VIF na população, opção b; Word travado e validate lento corrigidos no caminho) `fila_loo2.ps1 -Desde tabelas_compl` (tabelas, figuras, relatório, PDFs, Word,
      decks, Guia, Narrativa)
- [x] E6.2 (validate 0/0, caca_fosseis 0, conferir_numeros 0; 61/61 patches) Portões: `caca_fosseis.py --vivos` = 0; `conferir_numeros_entregaveis.py` = 0;
      `validate_consistency.py` = 0; anexos 26/26; hook dos livros 0 ALTO;
      `auditar_wrangling.py` e `checar_escolaridade.py` OK
- [x] E6.3 Conferência visual (03/10; resta só a bib do usuário): exportar todos os slides e páginas do Word e olhar
  - [x] Figuras: interseccional (rótulos repelidos, ticks), fig_qr_rif (rótulos q10/q90, legenda),
        BLUPs (título com milhar/decimal certos), fig1 (rótulos), waterfalls SHAP ("R$ 2.832")
  - [x] Word: capa (título centralizado, autores com respiro, afiliações 10 pt), títulos do
        Resumo/Abstract; notas de tabela que começavam por ":" (`\footnotesize{Como ler:}`);
        Nota depois da Fonte e colada a ela; nota solta entre tabela e Fonte (Tab. 1, HLM);
        legenda inteira e presa ao objeto; tabelas curtas sem quebra, linhas sem quebra;
        largura mínima pela maior palavra; 8 pt com 7+ colunas; células de texto à esquerda;
        números das tabelas como texto (não OMML); nº da nota sobrescrito dentro da nota
  - [x] Tab. 4: EP "(1,8e-05)" -> "(<0,0001)"; Tab. 10: rótulos A1–A4 (definidos na Tab. 9)
  - [x] CHEN 2016 completo (local, editora, DOI)
  - [x] Defesa: numeração automática dos títulos (s8 e 9b entram na sequência); s20 cabeçalhos
        em uma linha; s6 com a pergunta de cada método; s3 espaçamento; s11 figura maior;
        termos em inglês traduzidos
  - [x] Executiva: s4 cartões na mesma cor e frase "maior do que a diferença de salário"
        (odds × log-renda, unidades diferentes) trocada; s5 figura maior
  - [x] Guia: fórmula de Oaxaca com subscritos; tabelas com cabeçalho repetido e sem quebra;
        número de página
  - [x] Regenerado (fila_loo2 -Desde relatorio, 03/10 19:24, 11/11 OK; validate 0, caca_fosseis 0, conferir_numeros 0) e reconferido; s18 da Defesa refeito à parte (cabeçalhos em uma linha)
  - [ ] Pendente de dado do usuário: bib de Alencar 2024, Géron 2021, Imazon 2026, Fávero & Belfiore

## Bloco E8 — Feedback do orientador de julho, refeito na base atual (04/10)

- [x] E8.0 Merge do master do GitHub (4 commits de jul/2026) — versão local nos 26 conflitos;
      PR #1 mesclado (c7ca2ca). Branch novo: robustez-desenho-amostral-2026-10
- [x] E8.1 Oaxaca ponderada por V1028 (run_robustez_desenho.py --oaxaca): sem peso reproduz a
      Tab. 6 (17,9 / 15,4); com peso, retornos 15,3% (A) e 12,7% (B)
- [x] E8.2 Logit A2 com cluster UPA, sem/com peso V1028: acesso 0,820/0,808; top20 0,770/0,790; top10 0,758/0,777 (logit próprio em blocos; statsmodels estourava a memória)
- [x] E8.3 Baseline MQO do ML no mesmo treino/teste: R² teste MQO 0,587; RF 0,589 (+0,002); XGBoost 0,644 (+0,058)
- [x] E8.4 WeMix ENCERRADO (04/10, decisão do autor): piloto com 2% das UPAs (829) ficou ~4h na fase inicial de quadratura, sem chegar às iterações — população completa (41 mil UPAs) levaria dias. Vai para as Limitações como agenda; a robustez ao peso fica com o logit ponderado + cluster (E8.2). Pacote WeMix 4.0.3 instalado; script adaptado ao A2 atual
- [x] E8.6 Módulo de heterogeneidade concluído (04/10 17:13): glmm_heterogeneidade.csv, hlm_heterogeneidade.csv, qr_por_cor.csv, rif_por_cor.csv, oaxaca_por_cor.csv
- [x] E8.7 Inspeção visual + releitura das seções novas (04/10 noite): 20 achados de redação/coerência, 0 número errado. Aplicados: C1 (teto "pesa menos", Lei 12.990/2014, setor público ≠ causalidade da obrigação), P3 dividida (resultados × literatura; "maior retorno" removido), cor com q90 (não q95) e RIF nos mesmos quantis, colorismo definido (Telles 2004), idade (coorte ≠ teto; 65+ selecionado), pesos ("logit com efeito fixo de estado"; WeMix explicado), robustez (top 10% com peso; RF/XGB em números), legenda da Tab. 12 (modelo do top 10%, definição de setor), nota da Fig. interseccional ("série"), legenda sem repetir o título, Conclusão e roteiros citam cor/setor/idade, slide 15 e Guia 4.6 alinhados, títulos longos (Executiva 8, Defesa 16). Não aplicados: IC das diferenças preto×pardo e público×privado (exigiria teste formal; ver resposta ao autor), linha MQO na tab:ml_perf. IC: diferenças preto×pardo fora dos IC 95% e acesso público×privado com IC sobrepostos agora no texto (condicional, params HET_COR_SEPARA/HET_SETOR_*). Regenerado 04/10 20:21: norma 27/27, Word 49 pp, fósseis 0, sem fonte 0, verificar 0 ALTO. Agenda: representação negra nos cargos eletivos por estado (TSE) nas Limitações, uma frase, sem número (decisão do autor 04/10). Regenerado 20:48 e commitado
- [x] E8.5 Incluído, regenerado (04/10 17:40) e commitado (d874db5 código, d101bfd resultados), enviado e PR #2 aberto: subseção 'O que o agregado esconde' + Tab. 12 (cor, setor, idade, topo na UF); peso amostral e WeMix no parágrafo de Pesos; 2 linhas na tabela de robustez; C1 com o setor; P3 com medidas nos bairros; slide na Defesa; 4.6 no Guia; título do Resumo/Abstract à esquerda (norma); portão de 50 páginas pelo Word (48) e conferir_anexos agora derruba a fila

## Bloco E7 — Releitura final e fechamento

- [x] E7.1 (04/10: releitura por agente — 38 achados; corrigidos ~33 nos geradores: 'pela metade'/'quase à metade'/'dois terços'/'1/3 da chance', três camadas calculadas, limite superior × inferior, interação da pós-graduação, jornada fora do A2, HL por desfecho, nAGQ=0 ≠ Laplace, alçada, títulos dos decks, Gap obs. no RIF, VIF/robustez, QR q25 do β; regeneração 11:08 com portões OK. NÃO feitos: reordenar abertura da interseccionalidade (#36), padronizar 39%/39,5% (#38), explicar 41.454 × 41.459 × 40.728 UPAs (#38)) Releitura corrida (texto) + conferência visual (decks/Word) só sobre o que mudou
- [x] E7.2 (04/10: RETOMADA com a seção de 04/10; lições 24–27 em tcc/licoes_aprendidas.md; memórias de interseccionalidade e GLMM atualizadas; sobras da releitura feitas — interseccionalidade abre pela pergunta, frase das UPAs por método, 39,5% padronizado; regeneração 11:47 OK) Atualizar `RETOMADA_reestimacao_loo.md`, `releitura_2026-10-02.md` e memória
- [~] E7.3 (04/10: commits 2c07798 código e 3894ce7 resultados/entregáveis, no branch correcao-escolaridade-2026-10, enviado ao GitHub em 04/10; falta a tag de entrega, depois do E2.9/E2.13) Commits (código / resultados e entregáveis) e tag de entrega
- [ ] E7.4 Versão para o orientador
