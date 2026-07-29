# =============================================================================
# wemix_multinivel_ponderado.R
# GLMM Logístico Multinível PONDERADO (WeMix::mix) — teto de vidro ocupacional
#
# Extensão do logit_multinivel_glmm.R (lme4::glmer, sem peso amostral) para
# incorporar o peso amostral (V1028) diretamente na verossimilhança do modelo
# multinível, em vez do atalho single-level+cluster (glmm_ponderado.csv).
#
# WeMix::mix() exige pesos em CADA nível do modelo (Rabe-Hesketh & Skrondal /
# Pfeffermann et al. 1998, "scaling method 2", usado no manual do pacote):
#   nivel 1 (individuo): peso condicional = V1028 / peso_nivel2_da_UPA
#   nivel 2 (UPA):        media de V1028 dentro da UPA
# A PNAD Continua nao publica peso de segundo estagio (UPA) separado do peso
# final V1028 -- esta e a aproximacao padrao quando so o peso final esta
# disponivel (documentada no vignette do WeMix).
#
# Requer: R >= 4.2, arrow, WeMix, dplyr
#   install.packages(c("arrow","WeMix","dplyr"), type="binary")
#
# EXECUÇÃO: rodar no Predator Helios (Windows), não neste Mac.
# Teste de escala em 2026-07-29 nesta máquina (16GB RAM): mix() do WeMix passou
# de 1h só no M1 de uma subamostra de 2% (154k obs., ~32,9k UPAs -- quase o
# mesmo nº de clusters da população completa, que tem ~41,5k). O custo do
# WeMix escala principalmente com o nº de clusters (busca de nós de
# quadratura por UPA), não com N total, então a população completa
# (41,5k UPAs x ~185 obs/UPA em média) tende a ser tratável só numa máquina
# mais rápida / com mais RAM. Rodar com:
#   Rscript scripts/R/wemix_multinivel_ponderado.R           # população completa (default)
#   Rscript scripts/R/wemix_multinivel_ponderado.R 0.2 pct20 # subamostra 20% (fallback se full não convergir em tempo hábil)
# =============================================================================

.libPaths(c("C:/Users/user/R/win-library/4.6",
            "/Users/dado/Library/R/x86_64/4.2/library",
            .libPaths()))

library(arrow)
library(WeMix)
library(dplyr)

args <- commandArgs(trailingOnly = TRUE)
SAMPLE_FRAC <- if (length(args) >= 1) as.numeric(args[1]) else 1.0
TAG         <- if (length(args) >= 2) args[2] else "full"
SEED        <- 42

.get_root <- function() {
  a <- commandArgs(trailingOnly = FALSE)
  file_arg <- sub("--file=", "", a[grepl("--file=", a)])
  if (length(file_arg) > 0) {
    script_dir <- dirname(normalizePath(file_arg))
    return(normalizePath(file.path(script_dir, "..", "..")))
  }
  if (file.exists("C:/Users/user/Documents/ProjetoRacismoPNAD")) {
    return("C:/Users/user/Documents/ProjetoRacismoPNAD")
  }
  getwd()
}
ROOT    <- .get_root()
TABLES  <- file.path(ROOT, "outputs", "tables")
LOGS    <- file.path(ROOT, "outputs", "_logs")
dir.create(LOGS, showWarnings = FALSE)

cat(sprintf("=== WeMix — GLMM Multinivel Ponderado (amostra=%.1f%%, tag=%s) ===\n",
            SAMPLE_FRAC * 100, TAG))
cat("Carregando dados...\n")
t_load <- proc.time()

df_raw <- read_parquet(file.path(ROOT, "data", "processed", "features.parquet"))
cat(sprintf("  Total bruto: %s obs. (%.1fs)\n",
            format(nrow(df_raw), big.mark = ","), (proc.time() - t_load)[3]))

# ── Mesma preparação de logit_multinivel_glmm.R (alinhar variáveis) ──────────
df <- df_raw |>
  filter(
    pea          == 1,
    !is.na(renda_bruta),
    renda_bruta   > 0,
    !is.na(negro),
    !is.na(sexo_fem),
    !is.na(UPA),
    !is.na(V1028), V1028 > 0,
    !is.na(media_renda_upa_z),
    !is.na(media_educ_upa_z)
  ) |>
  mutate(
    negro                  = as.integer(negro),
    sexo_fem               = as.integer(sexo_fem),
    educ_medio_completo    = as.integer(!is.na(educ_medio_completo) & educ_medio_completo == 1),
    educ_superior_completo = as.integer(!is.na(educ_superior_completo) & educ_superior_completo == 1),
    educ_pos_graduacao     = as.integer(!is.na(educ_pos_graduacao) & educ_pos_graduacao == 1),
    educ_missing           = as.integer(is.na(educ_cat)),
    emprego_formal = as.integer(!is.na(emprego_formal) & emprego_formal == 1),
    setor_publico  = as.integer(!is.na(setor_publico) & setor_publico == 1),
    conta_propria  = as.integer(!is.na(conta_propria) & conta_propria == 1),
    trab_domestico = as.integer(!is.na(trab_domestico) & trab_domestico == 1),
    horas_c        = ifelse(!is.na(horas_c), horas_c, 0),
    idade_c        = ifelse(!is.na(idade_c), idade_c, 0),
    ocp_qualif     = as.integer(!is.na(ocp_grupo_cbo) &
                                  as.character(ocp_grupo_cbo) %in%
                                  c("dirigente","profissional","tecnico","administrativo")),
    UPA               = as.character(UPA),
    renda_media_upa_c = media_renda_upa_z,
    edu_media_upa_c   = media_educ_upa_z
  )
rm(df_raw); gc()

cat(sprintf("  PEA completa (filtros alinhados): %s obs.\n", format(nrow(df), big.mark = ",")))

if (SAMPLE_FRAC < 1.0) {
  set.seed(SEED)
  df <- df |> slice_sample(prop = SAMPLE_FRAC)
  cat(sprintf("  Subamostra (%.1f%%): %s obs.\n", SAMPLE_FRAC * 100, format(nrow(df), big.mark = ",")))
}

n_upa <- n_distinct(df$UPA)
cat(sprintf("  UPAs unicas: %s | media obs/UPA: %.1f\n",
            format(n_upa, big.mark = ","), nrow(df) / n_upa))

# ── Pesos multinível (scaling method 2 — Pfeffermann et al. 1998) ───────────
# w2 (nivel 2, UPA): media do peso final V1028 dentro da UPA.
# w1 (nivel 1, individuo, condicional): V1028 / w2 da sua UPA.
df <- df |>
  group_by(UPA) |>
  mutate(w2_upa = mean(V1028)) |>
  ungroup() |>
  mutate(w1_cond = V1028 / w2_upa)

cat(sprintf("  Peso w1 (condicional) — media=%.3f, min=%.3f, max=%.3f\n",
            mean(df$w1_cond), min(df$w1_cond), max(df$w1_cond)))
cat(sprintf("  Peso w2 (UPA) — media=%.1f, min=%.1f, max=%.1f\n",
            mean(df$w2_upa), min(df$w2_upa), max(df$w2_upa)))

# ── Fórmulas (mesmas do lme4::glmer não-ponderado, p/ comparação direta) ────
CTRL <- paste("sexo_fem",
              "+ educ_medio_completo + educ_superior_completo + educ_pos_graduacao + educ_missing",
              "+ idade_c + I(idade_c^2) + horas_c",
              "+ emprego_formal + setor_publico + conta_propria + trab_domestico")

f_m1 <- as.formula(paste("ocp_qualif ~ negro +", CTRL, "+ (1 | UPA)"))
f_m2 <- as.formula(paste("ocp_qualif ~ negro +", CTRL,
                          "+ renda_media_upa_c + edu_media_upa_c + (1 | UPA)"))

fit_wemix <- function(formula_obj, data, label) {
  cat(sprintf("\n--- WeMix %s (ponderado) ---\n", label))
  t0 <- proc.time()
  m <- mix(formula_obj, data = data,
           weights = c("w1_cond", "w2_upa"),
           family = binomial(link = "logit"),
           verbose = TRUE)
  elapsed <- (proc.time() - t0)[3]
  cat(sprintf("  %s concluido em %.1f min.\n", label, elapsed / 60))
  list(model = m, elapsed_s = elapsed)
}

resultados <- list()
timings    <- list()

res_m1 <- fit_wemix(f_m1, df, "M1")
timings[["M1"]] <- res_m1$elapsed_s
print(summary(res_m1$model))

res_m2 <- fit_wemix(f_m2, df, "M2")
timings[["M2"]] <- res_m2$elapsed_s
print(summary(res_m2$model))

# ── Extração de OR/CI para 'negro' ───────────────────────────────────────────
extrai_or <- function(m, label) {
  co <- summary(m)$coef
  b  <- co["negro", "Estimate"]
  se <- co["negro", "Std. Error"]
  data.frame(
    modelo   = label,
    OR_negro = exp(b),
    SE_negro = se,
    CI95_lo  = exp(b - 1.96 * se),
    CI95_hi  = exp(b + 1.96 * se),
    p_valor  = co["negro", grep("^Pr", colnames(co), value = TRUE)[1]]
  )
}

tbl <- bind_rows(
  extrai_or(res_m1$model, "M1_WeMix"),
  extrai_or(res_m2$model, "M2_WeMix")
)
tbl$N       <- nrow(df)
tbl$n_UPA   <- n_upa
tbl$sample_frac <- SAMPLE_FRAC
tbl$tempo_min   <- c(timings[["M1"]] / 60, timings[["M2"]] / 60)

out_path <- file.path(TABLES, sprintf("wemix_glmm_ponderado_%s.csv", TAG))
write.csv(tbl, out_path, row.names = FALSE)
cat(sprintf("\n%s salvo.\n", out_path))

# ── Comparação com resultados anteriores (não-ponderado lme4 + single-level ponderado) ──
cmp_rows <- list(tbl)
old_glmm_path <- file.path(TABLES, "glmm_resumo_full.csv")
if (file.exists(old_glmm_path)) {
  old <- read.csv(old_glmm_path)
  cmp <- data.frame(
    modelo   = old$modelo,
    OR_negro = old$OR_negro,
    SE_negro = NA,
    CI95_lo  = old$CI_low,
    CI95_hi  = old$CI_high,
    p_valor  = NA,
    N        = old$N,
    n_UPA    = NA,
    sample_frac = NA,
    tempo_min   = NA
  )
  cmp_rows[[length(cmp_rows) + 1]] <- cmp
}
old_pond_path <- file.path(TABLES, "glmm_ponderado.csv")
if (file.exists(old_pond_path)) {
  op <- read.csv(old_pond_path)
  cmp2 <- data.frame(
    modelo   = ifelse(op$ponderado, "M2_flat_GLM_ponderado_cluster", "M2_flat_GLM_naoponderado_cluster"),
    OR_negro = op$OR_negro,
    SE_negro = op$SE_negro,
    CI95_lo  = op$CI95_lo,
    CI95_hi  = op$CI95_hi,
    p_valor  = NA,
    N        = NA,
    n_UPA    = NA,
    sample_frac = NA,
    tempo_min   = NA
  )
  cmp_rows[[length(cmp_rows) + 1]] <- cmp2
}
comparacao <- bind_rows(cmp_rows)
comp_path <- file.path(TABLES, sprintf("wemix_comparacao_%s.csv", TAG))
write.csv(comparacao, comp_path, row.names = FALSE)
cat(sprintf("%s salvo.\n", comp_path))

cat("\n=== COMPARAÇÃO: WeMix (ponderado, multinível) vs. anteriores ===\n")
print(comparacao)

cat("\n=== CONCLUÍDO ===\n")
