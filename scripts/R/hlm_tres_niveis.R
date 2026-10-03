# hlm_tres_niveis.R — HLM de TRÊS níveis: pessoa < UPA < UF, ambos aleatórios.
#
# Por que existe: o TCC usa dois níveis (UPA aleatória, UF como efeitos fixos).
# A especificação anterior fazia o contrário (UF aleatória, UPA como covariável).
# Nenhuma das duas decompõe a variância nas três camadas ao mesmo tempo — é o que
# este script faz, para responder "quanto do que se atribui ao bairro é, na
# verdade, o estado?".
#
# O impedimento registrado em run_hlm_serie_completa.py ("inverter uma matriz
# 41517 x 41517") vale para o vc_formula do statsmodels, que monta a estrutura de
# forma densa. O lme4 representa Z como matriz esparsa e resolve por Cholesky
# esparsa: é o caso de uso para o qual foi escrito.
#
# Cada UPA pertence a uma única UF (verificado: 0 UPAs em mais de um estado), então
# (1|UF) + (1|UPA) já é o aninhamento correto — não é preciso (1|UF/UPA).
#
# EXPLORATÓRIO: grava em arquivo próprio e não toca em nada do entregável.
#
# Uso:  Rscript scripts/R/hlm_tres_niveis.R M0
#       Rscript scripts/R/hlm_tres_niveis.R M2
#       (um modelo por processo: a memória volta ao SO entre eles)

.libPaths(c("C:/Users/user/R/win-library/4.6", .libPaths()))
suppressPackageStartupMessages({
  library(arrow); library(lme4); library(dplyr)
})
options(warn = 1)

args  <- commandArgs(trailingOnly = TRUE)
MOD   <- if (length(args) >= 1) args[1] else "M0"
ROOT   <- "C:/Users/user/Documents/ProjetoRacismoPNAD"
TABLES <- file.path(ROOT, "outputs", "tables")
t0 <- proc.time()
cat(sprintf("=== HLM 3 níveis (lmer, RE de UPA e de UF) — modelo %s ===\n", MOD))

# ── 1. Dados: os mesmos filtros de run_hlm_stepup.py ─────────────────────────
cols <- c("log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
          "educ_fund_completo", "educ_medio_completo", "educ_superior_completo",
          "educ_pos_graduacao", "educ_cat", "log_horas", "urbano", "Ano",
          "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
          "UF", "UPA")
df <- read_parquet(file.path(ROOT, "data/processed/features.parquet"),
                   col_select = all_of(cols))
df <- df |> filter(!is.na(log_renda), log_renda > 0)
df$educ_missing <- as.integer(is.na(df$educ_cat))
obrig <- setdiff(cols, c("educ_cat"))
df <- df |> filter(if_all(all_of(obrig), ~ !is.na(.x)))
# UPAs com ao menos 10 observações, como no step-up
cnt <- df |> count(UPA) |> filter(n >= 10)
df  <- df |> semi_join(cnt, by = "UPA")
df$UPA_str <- as.factor(df$UPA)
df$UF_str  <- as.factor(df$UF)
df$Ano_f   <- as.factor(df$Ano)
cat(sprintf("  N = %s | UPAs = %s | UFs = %s\n",
            format(nrow(df), big.mark = "."),
            format(n_distinct(df$UPA), big.mark = "."),
            n_distinct(df$UF)))

# ── 2. Fórmulas, paralelas às do step-up ─────────────────────────────────────
IND <- paste("negro + sexo_fem + idade_c + idade_sq",
             "+ educ_fund_completo + educ_medio_completo + educ_superior_completo",
             "+ educ_pos_graduacao + log_horas + urbano + Ano_f")
UPA_CTX <- "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
RE <- "(1 | UF_str) + (1 | UPA_str)"
f <- switch(MOD,
  "M0" = as.formula(paste("log_renda ~ 1 +", RE)),
  "M1" = as.formula(paste("log_renda ~", IND, "+", RE)),
  "M2" = as.formula(paste("log_renda ~", IND, "+", UPA_CTX, "+", RE)),
  stop("modelo deve ser M0, M1 ou M2"))
cat("  fórmula: ", deparse(f, width.cutoff = 200), "\n")

# ── 3. Ajuste ────────────────────────────────────────────────────────────────
# REML para componentes de variância não enviesados — o objeto aqui é a
# decomposição, não o teste de razão de verossimilhança entre modelos.
ctrl <- lmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 2e5),
                    calc.derivs = FALSE)
fit <- lmer(f, data = df, REML = TRUE, control = ctrl)
cat(sprintf("  ajustado em %.1f min\n", (proc.time() - t0)[["elapsed"]] / 60))

# ── 4. Decomposição da variância nas três camadas ────────────────────────────
vc      <- as.data.frame(VarCorr(fit))
tau2_uf  <- vc$vcov[vc$grp == "UF_str"]
tau2_upa <- vc$vcov[vc$grp == "UPA_str"]
sigma2   <- vc$vcov[vc$grp == "Residual"]
tot <- tau2_uf + tau2_upa + sigma2

b <- tryCatch(fixef(fit)[["negro"]], error = function(e) NA_real_)
out <- data.frame(
  modelo = MOD, N = nrow(df),
  n_upas = n_distinct(df$UPA), n_ufs = n_distinct(df$UF),
  tau2_uf = tau2_uf, tau2_upa = tau2_upa, sigma2 = sigma2,
  icc_uf = tau2_uf / tot,                       # fração da variância entre estados
  icc_upa = tau2_upa / tot,                     # entre bairros, líquido do estado
  icc_uf_mais_upa = (tau2_uf + tau2_upa) / tot, # tudo que não é individual
  b_negro = b,
  minutos = (proc.time() - t0)[["elapsed"]] / 60
)
print(out)

dest <- file.path(TABLES, "hlm_tres_niveis.csv")
if (file.exists(dest)) {
  prev <- read.csv(dest, stringsAsFactors = FALSE)
  prev <- prev[prev$modelo != MOD, , drop = FALSE]
  out  <- rbind(prev, out)
}
write.csv(out, dest, row.names = FALSE)
cat(sprintf("OK -> %s\n", dest))
