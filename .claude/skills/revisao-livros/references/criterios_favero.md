# Critérios destilados — Manual de Análise de Dados, 2ª ed. (Fávero & Belfiore, 2022)

Leitura integral dos 18 capítulos (partes conceituais e de interpretação de outputs; os passo a passo de
SPSS/Stata/R/Python foram percorridos apenas pelos trechos interpretativos). Formulação própria.
[TCC] = ponto onde o projeto PNAD está diretamente exposto.

## Parte I — Estatística aplicada (caps. 1–8)
- FAV-01 (cap.1) Tipo de variável determina tratamento. Variável em faixas (renda, escolaridade em categorias) é
  QUALITATIVA: não calcular média/DP de rótulos numéricos. [TCC: educ_cat, faixas etárias, CBO → dummies, nunca escala numérica arbitrária.]
- FAV-02 (cap.1) Qualitativa com n categorias → (n−1) dummies com categoria de referência declarada; "ponderação
  arbitrária" (1,2,3…) é erro grave (caps. 1, 9, 10, 11, 12 repetem).
- FAV-03 (cap.2) Descritiva univariada antes de modelar: tabela de frequências, histograma/boxplot, medidas de posição
  (média, mediana, quartis/percentis), dispersão (DP, erro-padrão, CV), forma (assimetria, curtose). Renda é assimétrica →
  reportar mediana/quantis, não só média; CV>30% = heterogêneo.
- FAV-04 (cap.2) Outliers: identificar (boxplot 1,5·AIQ / 3·AIQ; z-scores; BACON multivariado), entender a causa antes de
  tratar; winsorização/exclusão/substituição são decisões declaradas, não silenciosas. Quantis e QR são menos sensíveis.
- FAV-05 (cap.2) Gráficos por tipo: barras/Pareto para qualitativas; histograma, boxplot, linhas para quantitativas.
- FAV-06 (cap.3) Bivariada: tabela de contingência com % por linha/coluna/total; χ² + V de Cramer (nominal),
  Spearman (ordinal), Pearson + dispersão (métricas). χ² cresce com N → com N em milhões, reportar V de Cramer/tamanho de efeito.
- FAV-07 (cap.3) Correlação ≠ causa (o texto insiste: cegonhas e bebês).
- FAV-08 (cap.5) Escolher a família de distribuição pelo tipo de Y: Bernoulli → logística; binomial → multinomial; Poisson/BN → contagem; normal → OLS.
  Z-scores para padronizar quando escalas diferem.
- FAV-09 (cap.6) **Desenho amostral**: amostragem por conglomerados em múltiplos estágios (PNAD: UPA → domicílio) faz os
  elementos do conglomerado serem parecidos → menos eficiente que AAS; a inferência tem de refletir isso (pesos, estratos,
  conglomerados). Amostragem estratificada é o oposto. Declarar N, desenho e como foi tratado.
- FAV-10 (cap.7) Testes de hipóteses: H0/H1 explícitas, α declarado, p-valor interpretado como "menor α que rejeita".
  Erro tipo I/II. Pressupostos dos paramétricos (normalidade — Shapiro-Wilk n≤30, Shapiro-Francia/K-S n>30;
  homogeneidade de variâncias — Levene, robusto a não normalidade; escala intervalar/razão).
- FAV-11 (cap.7) Comparação de médias: t (uma amostra, independentes com/sem variâncias iguais, emparelhadas), ANOVA um
  fator (F) e fatorial (efeitos principais + interação). Após ANOVA, post hoc para saber QUAL grupo difere.
- FAV-12 (cap.8) Não paramétricos quando pressupostos falham ou dados ordinais: Mann-Whitney (2 indep.), Kruskal-Wallis
  (k indep.), Wilcoxon (pareado), Friedman, McNemar, Q de Cochran, χ². Menos potentes; escolher com justificativa.

## Parte II — Exploratórias (caps. 9–11)
- FAV-20 (cap.9) Cluster é EXPLORATÓRIO: sem poder preditivo; nova observação/variável exige reaplicação; muito sensível a
  outliers; padronizar (z-score) se escalas diferem; justificar medida de distância e método de encadeamento; aplicar os
  três encadeamentos e comparar dendrogramas; usar salto de distância para escolher k; k-means precisa de k a priori
  (input de um hierárquico); validar com ANOVA (F por variável: quais discriminam); reaplicar sem variáveis que não
  contribuem. Clusters viram dummies em regressões apenas para diagnóstico, não previsão. [TCC Tier 3: K-Means/PAM.]
- FAV-21 (cap.10) Fatorial/PCA: só para métricas; adequação por KMO (>0,5) e Bartlett (preferir Bartlett — é teste);
  critério de raiz latente (autovalor>1); comunalidades; rotação Varimax; fatores ortogonais resolvem multicolinearidade.
  Não aplicar a Likert sem tratamento.
- FAV-22 (cap.11) Correspondência (Anacor/ACM) para associação entre categóricas; resíduos padronizados ajustados >1,96
  indicam excesso de ocorrência; mapa perceptual (2 dimensões, inércia).

## Parte III.1 — Regressão (cap. 12) [TCC núcleo: OLS base do HLM, OB, QR]
- FAV-30 Especificar com base em teoria; interpretar β como efeito marginal ceteris paribus, α raramente tem sentido
  (não forçar zero); interpolação vs. extrapolação (não prever fora do suporte).
- FAV-31 R² não diz significância nem causalidade; não superestimar R² (Wooldridge); R² ajustado para comparar modelos
  com nº diferente de parâmetros; F para "o modelo existe"; t/z e IC para cada parâmetro (IC contendo 0 = excluir).
  Tão importante quanto os significantes é discutir os NÃO significantes.
- FAV-32 Cuidado com exclusão manual simultânea de variáveis; stepwise com α declarado; mas stepwise pode omitir variável
  relevante → RESET.
- FAV-33 **Pressupostos OLS (Quadro 12.2)** e diagnósticos: (a) normalidade dos resíduos → Shapiro-Francia (grande N);
  violação invalida p-valores em amostra pequena, mitigada em grande N; (b) multicolinearidade → matriz de correlação,
  VIF/Tolerance (VIF>10 grave; VIF≈4 já é 75% de variância compartilhada); sintoma: F significante com t's não
  significantes; soluções: reconhecer e não fazer nada, fatores, stepwise (risco de omissão); (c) heterocedasticidade →
  Breusch-Pagan/Cook-Weisberg (supõe normalidade), White; gráfico resíduo×Ŷ ("cone"); consequência: EP viesados, t
  inválidos; Huber-White robusto NÃO resolve a causa — investigar especificação (forma funcional, omissão); MQP quando
  Var(u) é função conhecida de X; (d) autocorrelação só faz sentido com evolução temporal (Durbin-Watson só 1ª ordem e
  sem Y defasado; Breusch-Godfrey ordem p; NUNCA reportar DW em cross-section).
- FAV-34 Especificação: linktest (Ŷ² não significante) e RESET (omissão de variáveis). Formas funcionais (Quadro 12.3):
  log-log = elasticidade; semilog à esquerda (log Y) = variação % (o TCC usa ln(renda)); Box-Cox para escolher λ que
  maximize normalidade; lowess / component-plus-residual para detectar não linearidade.
- FAV-35 Leverage (h_ii > 2k/n) e resíduos padronizados ao quadrado: observações influentes vs. outliers; gráfico conjunto.
- FAV-36 Pesos amostrais: quando a amostra não é aleatória simples, ponderar (pweights) para alvo populacional.
- FAV-37 **Regressão quantílica (apêndice)**: estima percentis condicionais; minimiza soma ponderada de resíduos absolutos;
  não exige normalidade; robusta a outliers (mas não a alta leverage); ideal para renda (assimétrica); comparar
  coeficientes por quantil com IC e com OLS (gráfico β(τ) com faixa OLS); pseudo-R² só para comparar modelos;
  parâmetro pode perder significância ou mudar de sinal ao longo dos quantis — relatar.

## Parte III.1 — Logística (cap. 13) [TCC núcleo: GLMM]
- FAV-40 Y dicotômica → NUNCA OLS (variável qualitativa "numérica" é armadilha). Estimação por máxima verossimilhança.
  Categoria de referência e evento de interesse declarados.
- FAV-41 Reportar: LL do modelo e do nulo; χ² (razão de verossimilhança) para "o modelo existe"; z de Wald + IC por
  parâmetro; **odds ratio com IC** (IC contendo 1 = não significante); pseudo-R² de McFadden só para comparar modelos
  (não é % de variância).
- FAV-42 Distinguir probabilidade de chance (odds); interpretar e^β como fator multiplicativo da chance, ceteris paribus;
  OR de dummies como "chance X% maior/menor em relação à referência".
- FAV-43 **Qualidade de ajuste e desempenho**: Hosmer-Lemeshow (decis; não rejeitar = ajuste ok); tabela de classificação
  com cutoff declarado → eficiência global, sensitividade, especificidade; curva de sensibilidade (cutoff que iguala as
  duas) e **curva ROC + AUC** (critério principal para comparar modelos). Cutoff é decisão gerencial (custo dos erros).
- FAV-44 Pressupostos: só multicolinearidade (VIF) importa; não exigir balanceamento das classes.
- FAV-45 Probit vs. logit: escolher por LL/pseudo-R²/Hosmer-Lemeshow/AUC; β_logit ≈ 1,6·β_probit; justificar a escolha.
- FAV-46 Multinomial: (M−1) logitos vs. referência; relative risk ratios; classificação pela maior probabilidade.
- FAV-47 Gráficos de ajuste logístico probabilístico (curva S) por variável para comunicar.

## Parte III.1 — Contagem (cap. 14) [TCC: não usado]
- FAV-50 Y de contagem → Poisson (equidispersão) → teste de superdispersão → binomial negativa (NB2); excesso de zeros →
  ZIP/ZINB (teste de Vuong). Interpretar IRR.

## Parte III.2 — Painel (cap. 15) [TCC Tier 3: tendência temporal, event study; base conceitual do HLM]
- FAV-60 Decomposição de variância within/between/overall antes de modelar; painel curto (n>T) vs. longo (T>n).
- FAV-61 POLS exige EP robustos agrupados por indivíduo (cluster) — obrigatório; efeitos fixos (within) eliminam
  heterogeneidade invariante mas não estimam variáveis fixas no tempo; efeitos aleatórios (GLS) supõem a_i não
  correlacionado com X; R² within/between/overall; rho = correlação intraclasse.
- FAV-62 Testes: LM de Breusch-Pagan (POLS vs. RE), F de Chow (POLS vs. FE), **Hausman (FE vs. RE)** — se rejeita, RE é
  inconsistente. Painel longo: AR(1) nos erros (Wooldridge), Pesaran (correlação entre cross-sections).
- FAV-63 Logit em painel: pooled/PA vs. FE/RE — e^β tem interpretação diferente (mesmo indivíduo vs. indivíduo médio);
  FE descarta indivíduos sem variação em Y.

## Parte III.2 — Multinível (cap. 16) [TCC núcleo: HLM 3 níveis e GLMM logístico]
- FAV-70 Justificativa: aninhamento natural (indivíduo → UPA → UF); variáveis de nível 2/3 invariantes dentro do grupo;
  OLS ignora e gera EP/estimadores viesados. Aninhamento absoluto vs. classificação cruzada (HCM) — declarar.
- FAV-71 **Multilevel step-up strategy** (Raudenbush & Bryk; Snijders & Bosker), obrigatória e reportada em tabela:
  (1) **modelo nulo** → ICC por nível (τ/(τ+σ²); em 3 níveis, ICC de nível 2 e de nível 3) + LR test vs. OLS
  (Sig. χ² < 0,05 descarta OLS); (2) interceptos aleatórios + X de nível 1; (3) inclinações aleatórias (LR test REML com
  mesmos efeitos fixos; se τ11≈0, ficar com interceptos); (4) variáveis de nível superior (W) e interações cross-level
  (W·X); (5) estrutura de covariância dos efeitos aleatórios (independente vs. unstructured, via LR test).
- FAV-72 Componentes de variância: reportar τ00, τ11, σ² com EP; z = τ/EP > 1,96 indica variância significante; ICC
  recalculada a cada passo (a mudança de ICC ao incluir X mostra o quanto X explica dentro/entre grupos). [TCC: "UPA
  media mais da metade do gap" deve vir dessa sequência.]
- FAV-73 MLE vs. REML: REML para variâncias não viesadas; LR test de efeitos fixos diferentes exige MLE; diferença
  desprezível em amostras grandes. Declarar qual foi usado.
- FAV-74 BLUPs dos efeitos aleatórios (u0j) e gráfico de interceptos por grupo; valores previstos com e sem efeitos
  aleatórios; comparar ajuste HLM vs. OLS (gráfico previsto×observado).
- FAV-75 Interações cross-level testadas uma a uma; sinal de um W pode inverter na presença dos demais — explicar.
- FAV-76 Modelo nulo por si só já responde hipóteses (existe variabilidade entre grupos?) — pode ser resultado.
- FAV-77 **GLMM logístico**: mesma lógica (meglm/melogit, família Bernoulli, ligação logit); ICC = τ00/(τ00+π²/3);
  LR test vs. logit simples; OR dos efeitos fixos; comparar AUC do multinível vs. logit simples (roccomp) — ganho
  significativo justifica o multinível; curvas S por grupo. Contagem multinível: Poisson → NB com LR test (force).

## Parte III.3 — Sobrevivência (cap. 17) e canônica (cap. 18) [TCC Tier 3 / não usado]
- FAV-80 Cox: censura tratada; Kaplan-Meier + log-rank; hazard ratio; **testar proporcionalidade** (senão, variável
  tempo-dependente); paramétricos (Weibull/Gompertz) como alternativa.
- FAV-81 Correlação canônica: exploratória para escolher Y e X candidatos; medida de redundância ≈ R² médio.

## Transversais (repetidos em todos os capítulos)
- FAV-90 "Teoria subjacente + experiência do pesquisador" precede o modelo; explicitar hipóteses e constructo.
- FAV-91 Todo output deve vir acompanhado de: N, estatística de teste geral, parâmetros + EP + IC, medida de ajuste
  adequada à família (R²aj / pseudo-R² / AUC / ICC), diagnóstico de pressupostos, e interpretação em linguagem
  substantiva (unidades reais, ceteris paribus).
- FAV-92 Sempre comparar métodos quando aplicável (OLS vs. QR; FE vs. RE; logit vs. probit; HLM vs. OLS) e reportar por
  que um foi escolhido.
- FAV-93 Consistência de rótulos/categorias entre bases e softwares; conferir que o software não tratou categórica como numérica.
