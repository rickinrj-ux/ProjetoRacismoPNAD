# =============================================================================
# logit_multinivel_glmm.R
# GLMM Logístico Binário com Efeito Aleatório de UPA (logit multinível real)
# Substitui a aproximação logit + FE_UF usada anteriormente no TCC.
#
# Requer: R >= 4.2, pacotes arrow, lme4, broom.mixed, marginaleffects,
#         dplyr, ggplot2, writexl
#
# Para instalar os pacotes pela primeira vez, rode no console do RStudio:
#   install.packages(c("arrow","lme4","broom.mixed","marginaleffects",
#                      "dplyr","ggplot2","writexl","glmmTMB"))
# =============================================================================

.libPaths(c("C:/Users/user/R/win-library/4.6", .libPaths()))

library(arrow)
library(lme4)
library(broom.mixed)
library(marginaleffects)
library(dplyr)
library(ggplot2)
library(writexl)

ROOT    <- "C:/Users/user/Documents/ProjetoRacismoPNAD"
FIGURES <- file.path(ROOT, "outputs", "figures")
TABLES  <- file.path(ROOT, "outputs", "tables")

cat("=== Logit Multinível (GLMM) — lme4::glmer ===\n")
cat("Carregando dados...\n")

# ── 1. Carregar e preparar dados ──────────────────────────────────────────────
df_raw <- read_parquet(file.path(ROOT, "data", "processed", "features.parquet"))

cat(sprintf("  Total bruto: %s obs.\n", format(nrow(df_raw), big.mark=",")))

# ── Resultados anteriores para comparação ────────────────────────────────────
# Modelo empregado==1 (educ_ord, N=2.395.285): M1 OR=0.7045, M2 OR=0.7467
# Modelo pea==1 + conta_propria (educ_ord, N=2.395.285): M1 OR=0.7131, M2 OR=0.7587
old_resumo_path <- file.path(TABLES, "glmm_resumo_full.csv")
if (file.exists(old_resumo_path)) {
  old_res <- read.csv(old_resumo_path)
  cat("\n[REFERÊNCIA] Resultados anteriores (educ_ord, N=2.395.285):\n")
  cat(sprintf("  M1: OR=%.4f  ICC=%.4f (%.1f%%)\n",
              old_res$OR_negro[1], old_res$ICC_UPA[1], 100*old_res$ICC_UPA[1]))
  cat(sprintf("  M2: OR=%.4f  ICC=%.4f (%.1f%%)\n",
              old_res$OR_negro[2], old_res$ICC_UPA[2], 100*old_res$ICC_UPA[2]))
}

# ── EXTENSÃO PARA PEA COMPLETA: usa dummies de educação (100% cobertura) ─────
# educ_ord (contínuo) só cobre 31% da PEA → substitui por dummies binárias
# (mesma especificação do HLM/OB/QR, alinhando todos os modelos do TCC)
df <- df_raw |>
  filter(
    pea          == 1,
    !is.na(renda_bruta),
    renda_bruta   > 0,
    !is.na(negro),
    !is.na(sexo_fem),
    !is.na(UPA),
    !is.na(media_renda_upa_z),           # garante mesmo dataset para M1 e M2
    !is.na(media_educ_upa_z)
    # educ_ord REMOVIDO — substitui por dummies com cobertura total
  ) |>
  mutate(
    negro                  = as.integer(negro),
    sexo_fem               = as.integer(sexo_fem),
    educ_medio_completo    = as.integer(!is.na(educ_medio_completo) & educ_medio_completo == 1),
    educ_superior_completo = as.integer(!is.na(educ_superior_completo) & educ_superior_completo == 1),
    educ_pos_graduacao     = as.integer(!is.na(educ_pos_graduacao) & educ_pos_graduacao == 1),
    emprego_formal = as.integer(!is.na(emprego_formal) & emprego_formal == 1),
    setor_publico  = as.integer(!is.na(setor_publico) & setor_publico == 1),
    conta_propria  = as.integer(!is.na(conta_propria) & conta_propria == 1),
    trab_domestico = as.integer(!is.na(trab_domestico) & trab_domestico == 1),
    horas_c        = ifelse(!is.na(horas_c), horas_c, 0),
    idade_c        = ifelse(!is.na(idade_c), idade_c, 0),
    # Variável dependente: CBO grupos 1-4 (consistente com análise Python)
    ocp_qualif     = as.integer(!is.na(ocp_grupo_cbo) &
                                  as.character(ocp_grupo_cbo) %in%
                                  c("dirigente","profissional","tecnico","administrativo")),
    top20_renda    = as.integer(renda_bruta >= quantile(renda_bruta, 0.80, na.rm = TRUE)),
    UPA            = as.character(UPA),
    UF             = as.character(UF),
    renda_media_upa_c = media_renda_upa_z,
    edu_media_upa_c   = media_educ_upa_z
  )

cat(sprintf("  PEA COMPLETA (dummies educação, pea==1): %s obs.\n", format(nrow(df), big.mark=",")))
cat(sprintf("  UPAs unicas: %s\n", format(n_distinct(df$UPA), big.mark=",")))
cat(sprintf("  ocp_qualif = 1: %.1f%%\n", 100 * mean(df$ocp_qualif, na.rm=TRUE)))
cat(sprintf("  negro: %.1f%%  |  branco: %.1f%%\n",
            100*mean(df$negro), 100*(1-mean(df$negro))))
cat(sprintf("  educ_superior: %.1f%%  |  conta_propria: %.1f%%  |  trab_domestico: %.1f%%\n",
            100*mean(df$educ_superior_completo),
            100*mean(df$conta_propria), 100*mean(df$trab_domestico)))

# ── 2. Fórmulas dos modelos ───────────────────────────────────────────────────
# Dummies de educação (alinhado com HLM/OB/QR) + tipo de vínculo empregatício
CTRL <- paste("sexo_fem",
              "+ educ_medio_completo + educ_superior_completo + educ_pos_graduacao",
              "+ idade_c + I(idade_c^2) + horas_c",
              "+ emprego_formal + setor_publico + conta_propria + trab_domestico")

f_m1 <- as.formula(paste(
  "ocp_qualif ~ negro +", CTRL, "+ (1 | UPA)"
))

f_m2 <- as.formula(paste(
  "ocp_qualif ~ negro +", CTRL,
  "+ renda_media_upa_c + edu_media_upa_c + (1 | UPA)"
))

# Modelo com interseção aleatória e inclinação aleatória de negro por UPA
# (mais rico mas muito mais lento — use após confirmar convergência de M1/M2)
f_m3 <- as.formula(paste(
  "ocp_qualif ~ negro +", CTRL,
  "+ renda_media_upa_c + edu_media_upa_c + (1 + negro | UPA)"
))

# ── 3. Opções de controle (velocidade vs precisão) ────────────────────────────
# nAGQ=0: Laplace approximation — mais rápido, muito adequado para n grande
# nAGQ=1: Laplace padrão (default) — mais preciso, mais lento
# Recomendação: use nAGQ=0 na primeira rodada; se convergir bem, use nAGQ=1 p/ resultados finais
ctrl_fast <- glmerControl(
  optimizer  = "bobyqa",
  optCtrl    = list(maxfun = 3e5),
  calc.derivs = FALSE
)

# ── 4. Estimar modelos M1 e M2 ────────────────────────────────────────────────
cat("\n--- Estimando M1 (individual + UPA random intercept) ---\n")
cat("    Populacao completa — estimativa: 2–5 min com nAGQ=0 no Predator Helios...\n")
t0 <- proc.time()

m1 <- glmer(f_m1, data = df, family = binomial(link = "logit"),
            nAGQ   = 0,
            control = ctrl_fast)

cat(sprintf("    M1 concluído em %.1f min.\n", (proc.time() - t0)[3] / 60))

cat("\n--- Estimando M2 (+ contexto UPA) ---\n")
t0 <- proc.time()

m2 <- glmer(f_m2, data = df, family = binomial(link = "logit"),
            nAGQ   = 0,
            control = ctrl_fast)

cat(sprintf("    M2 concluído em %.1f min.\n", (proc.time() - t0)[3] / 60))

# ── 5. Resumo e diagnósticos ──────────────────────────────────────────────────
cat("\n=== RESULTADOS M1 ===\n")
print(summary(m1))

cat("\n=== RESULTADOS M2 ===\n")
print(summary(m2))

# ICC (Intraclass Correlation Coefficient da UPA)
var_upa_m1 <- as.numeric(VarCorr(m1)$UPA)
icc_m1     <- var_upa_m1 / (var_upa_m1 + pi^2 / 3)
var_upa_m2 <- as.numeric(VarCorr(m2)$UPA)
icc_m2     <- var_upa_m2 / (var_upa_m2 + pi^2 / 3)

cat(sprintf("\nICC UPA — M1: %.4f (%.1f%%)\n", icc_m1, 100 * icc_m1))
cat(sprintf("ICC UPA — M2: %.4f (%.1f%%)\n", icc_m2, 100 * icc_m2))

# Log-Likelihood e AIC
cat("\n--- Log-Likelihoods e AIC ---\n")
cat(sprintf("M1: LL=%.2f  AIC=%.2f\n", logLik(m1)[1], AIC(m1)))
cat(sprintf("M2: LL=%.2f  AIC=%.2f\n", logLik(m2)[1], AIC(m2)))

# LRT M1 vs M2
lrt_12 <- anova(m1, m2)
cat("\n--- LRT M1 vs M2 ---\n"); print(lrt_12)

# ── 6. Odds Ratios com IC 95% ─────────────────────────────────────────────────
tidy_m1 <- tidy(m1, effects = "fixed", conf.int = TRUE, exponentiate = TRUE)
tidy_m2 <- tidy(m2, effects = "fixed", conf.int = TRUE, exponentiate = TRUE)

or_negro_m1 <- tidy_m1 |> filter(term == "negro") |>
  select(term, OR = estimate, ci_low = conf.low, ci_high = conf.high, p.value)
or_negro_m2 <- tidy_m2 |> filter(term == "negro") |>
  select(term, OR = estimate, ci_low = conf.low, ci_high = conf.high, p.value)

cat("\n--- OR para 'negro' ---\n")
cat(sprintf("M1 (sem contexto):   OR = %.4f  [%.4f, %.4f]  p = %.2e\n",
            or_negro_m1$OR, or_negro_m1$ci_low, or_negro_m1$ci_high, or_negro_m1$p.value))
cat(sprintf("M2 (+ contexto UPA): OR = %.4f  [%.4f, %.4f]  p = %.2e\n",
            or_negro_m2$OR, or_negro_m2$ci_low, or_negro_m2$ci_high, or_negro_m2$p.value))

# ── 7. Average Marginal Effect (AME) ─────────────────────────────────────────
# Usa amostra de 10k para AME (evita timeout — marginaleffects é O(n))
cat("\n--- Average Marginal Effects (AME) para 'negro' (amostra 10k) ---\n")
df_ame <- df[sample(nrow(df), min(10000, nrow(df))), ]
ame_m1 <- avg_slopes(m1, variables = "negro", newdata = df_ame)
ame_m2 <- avg_slopes(m2, variables = "negro", newdata = df_ame)
print(ame_m1)
print(ame_m2)

# ── 8. Salvar resultados em CSV / Excel ───────────────────────────────────────
# Tabela de ORs completa (todos os preditores)
or_table <- bind_rows(
  tidy_m1 |> filter(effect == "fixed") |> mutate(modelo = "M1_GLMM"),
  tidy_m2 |> filter(effect == "fixed") |> mutate(modelo = "M2_GLMM")
)
write.csv(or_table,
          file.path(TABLES, "glmm_odds_ratios_full.csv"),
          row.names = FALSE)
cat("\nglmm_odds_ratios_full.csv salvo.\n")

# Resumo executivo — população completa PEA
resumo <- data.frame(
  modelo     = c("M1_GLMM_full", "M2_GLMM_full"),
  populacao  = c("pea==1", "pea==1"),
  N          = c(nrow(df), nrow(df)),
  OR_negro   = c(or_negro_m1$OR, or_negro_m2$OR),
  CI_low     = c(or_negro_m1$ci_low, or_negro_m2$ci_low),
  CI_high    = c(or_negro_m1$ci_high, or_negro_m2$ci_high),
  AME_negro  = c(ame_m1$estimate, ame_m2$estimate),
  ICC_UPA    = c(icc_m1, icc_m2),
  LL         = c(logLik(m1)[1], logLik(m2)[1]),
  AIC        = c(AIC(m1), AIC(m2))
)
write.csv(resumo,
          file.path(TABLES, "glmm_resumo_full.csv"),
          row.names = FALSE)
cat("glmm_resumo_full.csv salvo.\n")

# ── 9. Gráfico de Odds Ratios ─────────────────────────────────────────────────
or_plot_data <- or_table |>
  filter(effect == "fixed", term != "(Intercept)") |>
  mutate(
    modelo = factor(modelo, levels = c("M1_GLMM", "M2_GLMM"),
                    labels = c("M1 — Sem contexto UPA",
                               "M2 — Com contexto UPA")),
    term   = recode(term,
      negro          = "Raça (negro)",
      sexo_fem       = "Sexo (feminino)",
      edu_anos_c     = "Anos de educação",
      idade_c        = "Idade",
      horas_c        = "Horas trabalhadas",
      emprego_formal  = "Emprego formal",
      setor_publico   = "Setor público",
      conta_propria   = "Conta própria",
      trab_domestico  = "Trab. doméstico",
      renda_media_upa_c = "Renda média da UPA (log)",
      edu_media_upa_c   = "Educação média da UPA"
    ),
    destaque = ifelse(term == "Raça (negro)", "sim", "não")
  )

p_or <- ggplot(or_plot_data,
               aes(x = estimate, y = reorder(term, estimate),
                   color = destaque, shape = modelo)) +
  geom_vline(xintercept = 1, linetype = "dashed", color = "gray50") +
  geom_errorbarh(aes(xmin = conf.low, xmax = conf.high),
                 height = 0.25, linewidth = 0.7) +
  geom_point(size = 3.5) +
  scale_color_manual(values = c("sim" = "#B71C1C", "não" = "#1565C0"),
                     guide = "none") +
  scale_shape_manual(values = c(16, 17)) +
  labs(
    title    = "Odds Ratios — Logit Multinível (GLMM lme4)",
    subtitle = "Variável dependente: acesso a ocupação qualificada (CBO grupos 1–2)\nOR < 1 = desvantagem | Linha tracejada = paridade",
    x        = "Odds Ratio (escala log)",
    y        = NULL,
    shape    = "Modelo",
    caption  = "Fonte: PNAD Contínua 2016–2025. GLMM com efeito aleatório de UPA (nAGQ=0, bobyqa)."
  ) +
  scale_x_log10() +
  facet_wrap(~modelo, ncol = 2) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title    = element_text(face = "bold", color = "#1F3864"),
    panel.grid.minor = element_blank(),
    legend.position = "bottom"
  )

ggsave(file.path(FIGURES, "glmm_odds_ratios_full.png"),
       plot = p_or, width = 12, height = 7, dpi = 150)
cat("glmm_odds_ratios_full.png salvo.\n")

# ── 10. Sumário final ─────────────────────────────────────────────────────────
cat("\n")
cat("=======================================================\n")
cat("  SUMÁRIO — GLMM LOGÍSTICO (PEA completa, pea==1)\n")
cat("=======================================================\n")
cat(sprintf("  N (PEA completa)           : %s\n", format(nrow(df), big.mark=",")))
cat(sprintf("  OR negro M1 (sem contexto) : %.4f  [%.4f, %.4f]\n",
            or_negro_m1$OR, or_negro_m1$ci_low, or_negro_m1$ci_high))
cat(sprintf("  OR negro M2 (+ UPA ctx)    : %.4f  [%.4f, %.4f]\n",
            or_negro_m2$OR, or_negro_m2$ci_low, or_negro_m2$ci_high))
cat(sprintf("  AME negro M1               : %.4f p.p.\n", ame_m1$estimate * 100))
cat(sprintf("  AME negro M2               : %.4f p.p.\n", ame_m2$estimate * 100))
cat(sprintf("  ICC UPA (M1)               : %.4f (%.1f%%)\n", icc_m1, 100 * icc_m1))
cat(sprintf("  ICC UPA (M2)               : %.4f (%.1f%%)\n", icc_m2, 100 * icc_m2))
cat("-------------------------------------------------------\n")
cat("  COMPARAÇÃO COM MODELOS ANTERIORES:\n")
cat("  Orig  (empregado==1, educ_ord):      OR M1=0.7045  OR M2=0.7467  N=2.395.285\n")
cat("  Interm (pea==1, educ_ord+ctrl):      OR M1=0.7131  OR M2=0.7587  N=2.395.285\n")
cat(sprintf("  ATUAL (pea==1, dummies, PEA total):  OR M1=%.4f  OR M2=%.4f  N=%s\n",
            or_negro_m1$OR, or_negro_m2$OR, format(nrow(df), big.mark=",")))
cat("=======================================================\n")
cat("  Arquivos salvos:\n")
cat("    outputs/tables/glmm_odds_ratios_full.csv\n")
cat("    outputs/tables/glmm_resumo_full.csv\n")
cat("    outputs/figures/glmm_odds_ratios_full.png\n")
cat("=== CONCLUÍDO ===\n")
