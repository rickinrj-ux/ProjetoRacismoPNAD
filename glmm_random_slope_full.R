# =============================================================================
# glmm_random_slope_full.R
# Random slope de `negro` no GLMM logístico (lme4::glmer) — POPULAÇÃO COMPLETA.
#
# (1) Random slope por UF em TODOS os desfechos de acesso/teto de vidro:
#       ocp_qualif (CBO 1-4), y_top20 (quintil renda), y_top10 (decil renda)
#     Para cada um: modelo base (1|UF) vs random slope (1+negro|UF), LRT de
#     fronteira (Stram & Lee 1994: 0.5*chi2_1 + 0.5*chi2_2), variância do gap
#     entre UFs (tau2_negro), correlacao intercepto-slope (rho) e BLUPs por UF.
#
# (2) Heterogeneidade do glass ceiling por estado x setor (publico vs privado):
#       random slope (1+negro|UF) de ocp_qualif estimado separadamente em cada
#       setor -> o concurso publico atenua e/ou homogeneiza a barreira de acesso?
#
# Estimacao: glmer, family=binomial, nAGQ=0 (Laplace rapido p/ n grande), bobyqa.
# Saidas:
#   outputs/tables/glmm_rs_varcomp.csv   (componentes de variancia + LRT por modelo)
#   outputs/tables/glmm_rs_blup_uf.csv   (BLUPs e OR por UF, por desfecho)
#   outputs/tables/glassceil_setor_rs.csv(comparacao publico x privado)
#   outputs/figures/glmm_rs_real.png
# =============================================================================

.libPaths(c("C:/Users/user/R/win-library/4.6",
            "C:/Users/user/AppData/Local/R/win-library/4.6", .libPaths()))
suppressMessages({ library(arrow); library(lme4); library(dplyr); library(ggplot2) })

ROOT    <- "C:/Users/user/Documents/ProjetoRacismoPNAD"
FIGURES <- file.path(ROOT, "outputs", "figures")
TABLES  <- file.path(ROOT, "outputs", "tables")

UF_SIGLA <- c("11"="RO","12"="AC","13"="AM","14"="RR","15"="PA","16"="AP","17"="TO",
              "21"="MA","22"="PI","23"="CE","24"="RN","25"="PB","26"="PE","27"="AL",
              "28"="SE","29"="BA","31"="MG","32"="ES","33"="RJ","35"="SP","41"="PR",
              "42"="SC","43"="RS","50"="MS","51"="MT","52"="GO","53"="DF")

cat("=== GLMM Random Slope (lme4) — populacao completa ===\n")
df_raw <- read_parquet(file.path(ROOT, "data", "processed", "features.parquet"))

df <- df_raw |>
  filter(pea == 1, !is.na(renda_bruta), renda_bruta > 0, !is.na(negro),
         !is.na(sexo_fem), !is.na(UF), !is.na(media_renda_upa_z), !is.na(media_educ_upa_z)) |>
  mutate(
    negro = as.integer(negro), sexo_fem = as.integer(sexo_fem),
    educ_medio_completo    = as.integer(!is.na(educ_medio_completo) & educ_medio_completo == 1),
    educ_superior_completo = as.integer(!is.na(educ_superior_completo) & educ_superior_completo == 1),
    educ_pos_graduacao     = as.integer(!is.na(educ_pos_graduacao) & educ_pos_graduacao == 1),
    emprego_formal = as.integer(!is.na(emprego_formal) & emprego_formal == 1),
    setor_publico  = as.integer(!is.na(setor_publico) & setor_publico == 1),
    conta_propria  = as.integer(!is.na(conta_propria) & conta_propria == 1),
    trab_domestico = as.integer(!is.na(trab_domestico) & trab_domestico == 1),
    horas_c = ifelse(!is.na(horas_c), horas_c, 0),
    idade_c = ifelse(!is.na(idade_c), idade_c, 0),
    ocp_qualif = as.integer(!is.na(ocp_grupo_cbo) &
                  as.character(ocp_grupo_cbo) %in% c("dirigente","profissional","tecnico","administrativo")),
    y_top20 = as.integer(renda_bruta >= quantile(renda_bruta, 0.80, na.rm = TRUE)),
    y_top10 = as.integer(renda_bruta >= quantile(renda_bruta, 0.90, na.rm = TRUE)),
    UF = as.character(UF),
    renda_media_upa_c = media_renda_upa_z, edu_media_upa_c = media_educ_upa_z
  )
cat(sprintf("  N efetivo: %s | UFs: %d\n", format(nrow(df), big.mark=","), n_distinct(df$UF)))

CTRL <- paste("sexo_fem + educ_medio_completo + educ_superior_completo + educ_pos_graduacao",
              "+ idade_c + I(idade_c^2) + horas_c + emprego_formal + conta_propria + trab_domestico",
              "+ renda_media_upa_c + edu_media_upa_c")
ctrl_fast <- glmerControl(optimizer="bobyqa", optCtrl=list(maxfun=3e5), calc.derivs=FALSE)

# p-valor do LRT de fronteira (adiciona tau2_slope + covariancia => mistura 50:50 chi2_1/chi2_2)
boundary_p <- function(lr) 0.5*pchisq(lr, 1, lower.tail=FALSE) + 0.5*pchisq(lr, 2, lower.tail=FALSE)

varcomp_rows <- list(); blup_rows <- list()

fit_rs <- function(dat, desfecho, rotulo, incl_setor = TRUE) {
  ctrl <- if (incl_setor) paste(CTRL, "+ setor_publico") else CTRL
  f_base <- as.formula(paste(desfecho, "~ negro +", ctrl, "+ (1 | UF)"))
  f_rs   <- as.formula(paste(desfecho, "~ negro +", ctrl, "+ (1 + negro | UF)"))
  cat(sprintf("\n--- [%s] %s: base (1|UF) ...\n", rotulo, desfecho))
  t0 <- proc.time()
  m_base <- glmer(f_base, data=dat, family=binomial, nAGQ=0, control=ctrl_fast)
  cat(sprintf("    base ok %.1f min | rs (1+negro|UF) ...\n", (proc.time()-t0)[3]/60))
  t0 <- proc.time()
  m_rs   <- glmer(f_rs, data=dat, family=binomial, nAGQ=0, control=ctrl_fast)
  cat(sprintf("    rs ok %.1f min\n", (proc.time()-t0)[3]/60))

  vc <- VarCorr(m_rs)$UF
  tau2_int <- vc[1,1]; tau2_neg <- vc[2,2]; cov_in <- vc[1,2]
  rho <- if (tau2_int > 0 && tau2_neg > 0) cov_in/sqrt(tau2_int*tau2_neg) else 0
  b_neg <- fixef(m_rs)["negro"]
  lr <- as.numeric(2*(logLik(m_rs) - logLik(m_base)))
  p  <- boundary_p(lr)
  cat(sprintf("    OR_negro(fixo)=%.4f | tau2_negro=%.5f (SD=%.4f) | rho=%.3f | LR=%.1f p=%.3g\n",
              exp(b_neg), tau2_neg, sqrt(max(tau2_neg,0)), rho, lr, p))

  varcomp_rows[[rotulo]] <<- data.frame(
    rotulo=rotulo, desfecho=desfecho, OR_negro=exp(b_neg), b_negro=b_neg,
    tau2_intercepto=tau2_int, tau2_negro=tau2_neg, sd_negro=sqrt(max(tau2_neg,0)),
    cov_int_neg=cov_in, rho=rho, LR=lr, p_boundary=p,
    OR_base=exp(fixef(m_base)["negro"]), N=nrow(dat), n_UF=n_distinct(dat$UF),
    row.names=NULL)

  re <- ranef(m_rs)$UF
  blup_rows[[rotulo]] <<- data.frame(
    rotulo=rotulo, desfecho=desfecho, UF=rownames(re),
    sigla=UF_SIGLA[rownames(re)], u0=re[,1], u1_negro=re[,2],
    gap_log=b_neg + re[,2], OR_uf=exp(b_neg + re[,2]), row.names=NULL)
  invisible(NULL)
}

# ── PARTE 1: random slope em todos os desfechos (populacao completa) ──────────
for (y in c("ocp_qualif","y_top20","y_top10")) fit_rs(df, y, y, incl_setor=TRUE)

# salva Parte 1
write.csv(do.call(rbind, varcomp_rows), file.path(TABLES,"glmm_rs_varcomp.csv"), row.names=FALSE)
write.csv(do.call(rbind, blup_rows),   file.path(TABLES,"glmm_rs_blup_uf.csv"),  row.names=FALSE)
cat("\n[Parte 1 salva] glmm_rs_varcomp.csv + glmm_rs_blup_uf.csv\n")

# ── PARTE 2: glass ceiling por setor (publico x privado) — ocp_qualif ─────────
fit_rs(df |> filter(setor_publico==0), "ocp_qualif", "ocp_qualif_PRIVADO", incl_setor=FALSE)
fit_rs(df |> filter(setor_publico==1), "ocp_qualif", "ocp_qualif_PUBLICO", incl_setor=FALSE)

write.csv(do.call(rbind, varcomp_rows), file.path(TABLES,"glmm_rs_varcomp.csv"), row.names=FALSE)
write.csv(do.call(rbind, blup_rows),   file.path(TABLES,"glmm_rs_blup_uf.csv"),  row.names=FALSE)

# comparacao setorial enxuta
vc_all <- do.call(rbind, varcomp_rows)
setor_cmp <- vc_all[vc_all$rotulo %in% c("ocp_qualif_PRIVADO","ocp_qualif_PUBLICO"),
                    c("rotulo","OR_negro","tau2_negro","sd_negro","rho","p_boundary","N")]
write.csv(setor_cmp, file.path(TABLES,"glassceil_setor_rs.csv"), row.names=FALSE)

# ── Figura: OR por UF (caterpillar) por desfecho + setor ─────────────────────
bl <- do.call(rbind, blup_rows)
bl$grupo <- factor(bl$rotulo, levels=c("ocp_qualif","y_top20","y_top10",
                                       "ocp_qualif_PRIVADO","ocp_qualif_PUBLICO"))
p <- ggplot(bl, aes(x=OR_uf, y=reorder(sigla, OR_uf))) +
  geom_vline(xintercept=1, linetype="dashed", color="gray50") +
  geom_point(aes(color=grupo), size=1.6) +
  facet_wrap(~grupo, scales="free_x", nrow=1) +
  labs(title="Random slope GLMM (lme4) — Odds Ratio de negro por UF",
       subtitle="OR<1 = barreira de acesso | dispersao entre UFs = heterogeneidade geografica (BLUP)",
       x="Odds Ratio de negro por UF", y=NULL,
       caption="GLMM logistico (1+negro|UF), nAGQ=0, populacao completa. PNAD 2016-2025.") +
  scale_x_log10() + theme_minimal(base_size=10) +
  theme(legend.position="none", plot.title=element_text(face="bold", color="#1F3864"))
ggsave(file.path(FIGURES,"glmm_rs_real.png"), p, width=15, height=5.5, dpi=150)

# ── Sumario ───────────────────────────────────────────────────────────────────
cat("\n=======================================================\n")
cat("  SUMARIO — RANDOM SLOPE GLMM (populacao completa)\n")
cat("=======================================================\n")
print(vc_all[,c("rotulo","OR_negro","tau2_negro","sd_negro","rho","LR","p_boundary","N","n_UF")], digits=4)
cat("\nArquivos: glmm_rs_varcomp.csv | glmm_rs_blup_uf.csv | glassceil_setor_rs.csv | glmm_rs_real.png\n")
cat("=== CONCLUIDO ===\n")
