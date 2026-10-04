# =============================================================================
# glmm_glassceil.R — GLMM logístico de VERDADE (lme4::glmer, intercepto aleatório de UPA)
# para o teto de vidro ocupacional e salarial — bloco 4 da revisão (tcc/revisoes).
#
# Substitui, como fonte da Tabela tab:glmm_glassceil, o logit com efeitos fixos de UF
# de scripts/analise/run_glmm_glassceil.py (que continua como coluna de robustez, com
# SE agrupado por UPA).
#
# Desfechos: ocp_qualif (CBO 1-4), y_top20, y_top10 (quantis da renda entre ocupados).
# Degraus (todos com efeitos fixos de UF e (1 | UPA)), na mesma lógica do HLM:
#   M1  individual: negro + sexo + escolaridade + idade + horas + UF
#   M2  + contexto do bairro: %negro, desemprego, educação média da UPA (z)
#       (SEM media_renda_upa: reflexo de Manski — TODO 5.3b)
#   M3  + vínculo: formal, setor público, conta própria, doméstico (bad controls -> limite inferior)
#   M4  + interação negro x credencial (superior, pós)
# Para cada modelo: OR e IC 95% de negro, AME (diferença de probabilidade predita, com RE),
# tau2_UPA, ICC = tau2/(tau2 + pi^2/3), LL, AIC, BIC, AUC (com e sem RE), cutoff de Youden
# com sensibilidade/especificidade, Hosmer-Lemeshow (10 decis) e, no M2, LR test vs.
# logit pooled (sem RE; p-valor dividido por 2 — teste na fronteira).
# Estimação: Laplace (nAGQ=0, bobyqa) — adequado para n grande (Bates et al., 2015).
#
# Uso:  Rscript scripts/R/glmm_glassceil.R              # população
#       Rscript scripts/R/glmm_glassceil.R 0.01         # teste: 1% das UPAs
# Saída: outputs/tables/glmm_glassceil_glmer.csv (+ _coefs.csv)
# =============================================================================
.libPaths(c("C:/Users/user/R/win-library/4.6", .libPaths()))
suppressPackageStartupMessages({
  library(arrow); library(lme4); library(dplyr)
})
options(warn = 1)
args <- commandArgs(trailingOnly = TRUE)
SAMPLE <- if (length(args) >= 1 && args[1] != "--one") as.numeric(args[1]) else NA
ONE    <- "--one" %in% args          # ajusta UM modelo e sai (processo novo por modelo: memória volta ao SO)

ROOT   <- "C:/Users/user/Documents/ProjetoRacismoPNAD"
TABLES <- file.path(ROOT, "outputs", "tables")
t_start <- proc.time()
cat("=== GLMM glassceil (glmer, RE de UPA) ===\n")

# ── 1. Dados (mesmos filtros do run_glmm_glassceil.py) ───────────────────────
cols <- c("negro","sexo_fem","idade_c","idade_sq","educ_medio_completo","educ_superior_completo",
          "educ_pos_graduacao","educ_cat","pct_negro_upa_z","tx_desemprego_upa_z","media_educ_upa_z",
          "media_renda_upa_z","emprego_formal","setor_publico","conta_propria","trab_domestico",
          "ocp_dirigente","ocp_profissional","ocp_tecnico","ocp_administrativo","horas_c",
          "educ_fund_completo","urbano","Ano",   # simetria com o HLM
         
          "renda_bruta","pea","UF","UPA")
df <- read_parquet(file.path(ROOT, "data/processed/features.parquet"), col_select = all_of(cols))
df <- df |>
  filter(pea == 1, !is.na(renda_bruta), renda_bruta > 0, !is.na(negro), !is.na(sexo_fem),
         !is.na(media_renda_upa_z), !is.na(media_educ_upa_z),
         !is.na(pct_negro_upa_z), !is.na(tx_desemprego_upa_z)) |>
  mutate(
    negro = as.integer(negro), sexo_fem = as.integer(sexo_fem),
    educ_medio_completo    = as.integer(!is.na(educ_medio_completo) & educ_medio_completo == 1),
    educ_superior_completo = as.integer(!is.na(educ_superior_completo) & educ_superior_completo == 1),
    educ_pos_graduacao     = as.integer(!is.na(educ_pos_graduacao) & educ_pos_graduacao == 1),
    educ_fund_completo = as.integer(!is.na(educ_fund_completo) & educ_fund_completo == 1),
    urbano             = as.integer(!is.na(urbano) & urbano == 1),
    Ano                = factor(Ano),
    educ_missing   = as.integer(is.na(educ_cat)),
    emprego_formal = as.integer(!is.na(emprego_formal) & emprego_formal == 1),
    setor_publico  = as.integer(!is.na(setor_publico) & setor_publico == 1),
    conta_propria  = as.integer(!is.na(conta_propria) & conta_propria == 1),
    trab_domestico = as.integer(!is.na(trab_domestico) & trab_domestico == 1),
    horas_c        = ifelse(is.na(horas_c), 0, horas_c),
    idade_c        = ifelse(is.na(idade_c), 0, idade_c),
    idade_sq       = ifelse(is.na(idade_sq), idade_c^2, idade_sq),
    ocp_qualif = as.integer(coalesce(ocp_dirigente, 0) == 1 | coalesce(ocp_profissional, 0) == 1 |
                            coalesce(ocp_tecnico, 0) == 1 | coalesce(ocp_administrativo, 0) == 1),
    UPA = as.character(UPA), UF = factor(as.character(UF))
  )
q80 <- quantile(df$renda_bruta, 0.80); q90 <- quantile(df$renda_bruta, 0.90)
df$y_top20 <- as.integer(df$renda_bruta >= q80)
df$y_top10 <- as.integer(df$renda_bruta >= q90)
if (!is.na(SAMPLE)) {
  set.seed(42)
  upas <- unique(df$UPA); keep <- sample(upas, max(50, round(length(upas) * SAMPLE)))
  df <- df[df$UPA %in% keep, ]
  cat(sprintf("  AMOSTRA de %.1f%% das UPAs\n", 100 * SAMPLE))
}
df <- df |> select(-media_renda_upa_z, -educ_cat, -ocp_dirigente, -ocp_profissional, -ocp_tecnico,
                   -ocp_administrativo, -renda_bruta, -pea)
invisible(gc())
N <- nrow(df); G <- n_distinct(df$UPA)
cat(sprintf("  N = %s | UPAs = %s | ocp_qualif = %.1f%% | top20 = %.1f%% | top10 = %.1f%%\n",
            format(N, big.mark = ","), format(G, big.mark = ","),
            100 * mean(df$ocp_qualif), 100 * mean(df$y_top20), 100 * mean(df$y_top10)))

# ── 2. Fórmulas ──────────────────────────────────────────────────────────────
# Simetria com o HLM (run_hlm_stepup.py, _IND): mesmos controles individuais.
# Faltavam educ_fund_completo (degrau da base da escada educacional), urbano e
# o ano — a serie cobre 2016-2025 e inclui a pandemia.
# horas_c nao entra aqui: ver VINC abaixo. A simetria e de controles PREDETERMINADOS,
# nao de lista literal — copiar um controle que so faz sentido no outro desfecho
# criaria um bad control.
IND  <- paste("sexo_fem + educ_fund_completo + educ_medio_completo +",
              "educ_superior_completo + educ_pos_graduacao +",
              "idade_c + idade_sq + urbano + factor(Ano) + UF")
CTX  <- "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
# horas_c SAI do bloco individual e entra aqui. No HLM ela é controle necessario
# (o desfecho e a renda MENSAL: sem horas, compara-se quem faz 20h com quem faz 44h).
# Aqui o desfecho e ocupar o cargo, e a jornada nao causa o acesso — e determinada
# junto com ele. Por isso entra no degrau do limite inferior, com o vinculo.
VINC <- "emprego_formal + setor_publico + conta_propria + trab_domestico + horas_c"
INTR <- "negro:educ_superior_completo + negro:educ_pos_graduacao"
RHS <- list(
  M1 = paste("negro +", IND),
  M2 = paste("negro +", IND, "+", CTX),
  M3 = paste("negro +", IND, "+", CTX, "+", VINC),
  M4 = paste("negro +", IND, "+", CTX, "+", VINC, "+", INTR)
)
ctrl <- glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 3e5), calc.derivs = FALSE)

# ── 3. Utilitários ───────────────────────────────────────────────────────────
auc_rank <- function(y, p) {                       # Mann-Whitney: AUC = P(p1 > p0)
  r <- rank(p); n1 <- as.numeric(sum(y == 1)); n0 <- as.numeric(sum(y == 0))   # numeric: n1*n0 > 2^31
  (sum(r[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}
youden <- function(y, p) {                         # cutoff que maximiza sens + espec - 1
  grid <- seq(0.02, 0.98, by = 0.01)
  best <- c(cut = NA, j = -Inf, sens = NA, spec = NA)
  for (cu in grid) {
    yhat <- as.integer(p >= cu)
    sens <- sum(yhat == 1 & y == 1) / as.numeric(sum(y == 1)); spec <- sum(yhat == 0 & y == 0) / as.numeric(sum(y == 0))
    if (sens + spec - 1 > best["j"]) best <- c(cut = cu, j = sens + spec - 1, sens = sens, spec = spec)
  }
  best
}
logit_pooled_ll <- function(formula, data, chunk = 500000L, maxit = 30, tol = 1e-8) {
  # Log-verossimilhança do logit SEM efeito aleatório por IRLS em blocos de linhas:
  # glm() em 7,7 M x 44 colunas passava de 20 GB (cópias da matriz de desenho + QR);
  # aqui só a matriz de desenho fica em memória e os produtos cruzados são acumulados.
  X <- model.matrix(formula, data); y <- model.response(model.frame(formula, data[1:2, ]))  # tipo
  y <- as.numeric(data[[all.vars(formula)[1]]])
  n <- nrow(X); k <- ncol(X); beta <- rep(0, k); beta[1] <- qlogis(mean(y))
  idx <- split(seq_len(n), ceiling(seq_len(n) / chunk))
  ll_old <- -Inf
  for (it in seq_len(maxit)) {
    XtWX <- matrix(0, k, k); XtWz <- numeric(k); ll <- 0
    for (ii in idx) {
      Xi <- X[ii, , drop = FALSE]; eta <- drop(Xi %*% beta); mu <- plogis(eta)
      w <- mu * (1 - mu); z <- eta + (y[ii] - mu) / w
      XtWX <- XtWX + crossprod(Xi * sqrt(w)); XtWz <- XtWz + drop(crossprod(Xi, w * z))
      ll <- ll + sum(y[ii] * log(mu) + (1 - y[ii]) * log1p(-mu))
    }
    beta <- drop(solve(XtWX, XtWz))
    if (abs(ll - ll_old) < tol * abs(ll)) break
    ll_old <- ll
  }
  # LL final no beta atualizado
  ll <- 0
  for (ii in idx) { mu <- plogis(drop(X[ii, , drop = FALSE] %*% beta)); ll <- ll + sum(y[ii] * log(mu) + (1 - y[ii]) * log1p(-mu)) }
  rm(X); invisible(gc())
  ll
}

hosmer <- function(y, p, g = 10) {                 # Hosmer-Lemeshow (10 decis de p)
  dec <- cut(p, breaks = unique(quantile(p, seq(0, 1, length.out = g + 1))), include.lowest = TRUE)
  o1 <- tapply(y, dec, sum); e1 <- tapply(p, dec, sum); n <- tapply(y, dec, length)
  chi <- sum((o1 - e1)^2 / (e1 * (1 - e1 / n)))
  c(chi2 = chi, df = length(n) - 2, p = pchisq(chi, length(n) - 2, lower.tail = FALSE))
}

rows <- list(); coefs <- list()
SUF <- if ("--sim" %in% args) "_sim" else ""   # --sim: grava ao lado, sem sobrescrever
out_csv  <- file.path(TABLES, paste0("glmm_glassceil_glmer", SUF, ".csv"))
out_coef <- file.path(TABLES, paste0("glmm_glassceil_glmer", SUF, "_coefs.csv"))
if (is.na(SAMPLE) && file.exists(out_csv)) {                 # retomada após queda (memória)
  prev <- read.csv(out_csv); prevc <- read.csv(out_coef)
  if (nrow(prev) > 0 && prev$N[1] == N) {
    rows <- lapply(seq_len(nrow(prev)), function(i) prev[i, ]); coefs <- list(prevc)
    cat(sprintf("  retomando: %d modelo(s) já gravado(s)\n", nrow(prev)))
  }
}
feitos <- function() if (length(rows)) paste(bind_rows(rows)$desfecho, bind_rows(rows)$modelo) else character(0)
for (y_col in c("ocp_qualif", "y_top20", "y_top10")) {
  cat(sprintf("\n--- Desfecho: %s ---\n", y_col))
  ll_pooled <- NA
  for (m_name in names(RHS)) {
    if (paste(y_col, m_name) %in% feitos()) { cat(sprintf("  %s: já gravado, pulando\n", m_name)); next }
    f <- as.formula(paste(y_col, "~", RHS[[m_name]], "+ (1 | UPA)"))
    t0 <- proc.time()
    m <- glmer(f, data = df, family = binomial(link = "logit"), nAGQ = 0, control = ctrl)
    el <- (proc.time() - t0)[3] / 60
    b <- fixef(m); V <- as.matrix(vcov(m)); se <- sqrt(diag(V))
    bn <- b["negro"]; sen <- se["negro"]
    tau2 <- as.numeric(VarCorr(m)$UPA); icc <- tau2 / (tau2 + pi^2 / 3)
    # AME: diferença média de probabilidade predita (negro=1 vs 0), com efeitos aleatórios,
    # calculada no preditor linear (evita duas cópias do data.frame de 7,7 M linhas)
    eta <- predict(m, type = "link")                            # inclui RE
    contrib <- bn + ifelse(is.na(b["negro:educ_superior_completo"]), 0, b["negro:educ_superior_completo"]) * df$educ_superior_completo +
                    ifelse(is.na(b["negro:educ_pos_graduacao"]), 0, b["negro:educ_pos_graduacao"]) * df$educ_pos_graduacao
    eta0 <- eta - contrib * df$negro                            # todos como negro = 0
    ame <- mean(plogis(eta0 + contrib) - plogis(eta0)); rm(eta0, contrib)
    y <- df[[y_col]]
    p_re <- predict(m, type = "response")                       # com RE (ajuste na amostra)
    p_fe <- predict(m, type = "response", re.form = NA)          # só efeitos fixos
    auc_re <- auc_rank(y, p_re); auc_fe <- auc_rank(y, p_fe)
    yj <- youden(y, p_re); hl <- hosmer(y, p_re)
    lr_pool <- NA; p_lr_pool <- NA
    if (m_name == "M2") {                                       # LR vs logit pooled (sem RE)
      ll_pooled <- logit_pooled_ll(as.formula(paste(y_col, "~", RHS[[m_name]])), df)
      lr_pool <- 2 * (as.numeric(logLik(m)) - ll_pooled)
      p_lr_pool <- pchisq(lr_pool, 1, lower.tail = FALSE) / 2
    }
    or_inter <- if (m_name == "M4") c(sup = unname(exp(b["negro:educ_superior_completo"])),
                                      pos = unname(exp(b["negro:educ_pos_graduacao"]))) else c(sup = NA, pos = NA)
    rows[[length(rows) + 1]] <- data.frame(
      desfecho = y_col, modelo = m_name, N = N, n_upa = G,
      OR_negro = exp(bn), CI95_lo = exp(bn - 1.96 * sen), CI95_hi = exp(bn + 1.96 * sen),
      beta_negro = bn, se_negro = sen, p_valor = 2 * pnorm(-abs(bn / sen)),
      AME_pp = 100 * ame, tau2_upa = tau2, ICC_UPA = icc,
      LL = as.numeric(logLik(m)), AIC = AIC(m), BIC = BIC(m),
      LR_vs_pooled = lr_pool, p_LR_vs_pooled = p_lr_pool, LL_pooled = ll_pooled,
      AUC_com_RE = auc_re, AUC_so_FE = auc_fe,
      cutoff_youden = yj["cut"], sens = yj["sens"], espec = yj["spec"],
      HL_chi2 = hl["chi2"], HL_df = hl["df"], HL_p = hl["p"],
      OR_inter_superior = or_inter["sup"], OR_inter_pos = or_inter["pos"],
      converged = is.null(m@optinfo$conv$lme4$messages), minutos = round(el, 1))
    coefs[[length(coefs) + 1]] <- data.frame(desfecho = y_col, modelo = m_name, termo = names(b),
                                             coef = unname(b), se = unname(se))
    cat(sprintf("  %s: OR=%.3f [%.3f; %.3f] | AME=%+.2f pp | ICC=%.3f | AUC(RE)=%.3f AUC(FE)=%.3f | cutoff=%.2f sens=%.2f esp=%.2f | %.1f min\n",
                m_name, exp(bn), exp(bn - 1.96 * sen), exp(bn + 1.96 * sen), 100 * ame, icc,
                auc_re, auc_fe, yj["cut"], yj["sens"], yj["spec"], el))
    # salva parcial a cada modelo (proteção contra queda)
    write.csv(bind_rows(rows), out_csv, row.names = FALSE)
    write.csv(bind_rows(coefs), out_coef, row.names = FALSE)
    rm(m, p_re, p_fe, eta); invisible(gc())
    if (ONE) { cat("  --one: modelo gravado; encerrando este processo.
"); quit(save = "no", status = 0) }
  }
}
cat(sprintf("\nCONCLUÍDO em %.1f min -> outputs/tables/glmm_glassceil_glmer.csv\n", (proc.time() - t_start)[3] / 60))
