# =============================================================================
# glmm_genero_full.R
# Random slope de `sexo_fem` (GÊNERO) no GLMM logístico (lme4::glmer) — POP. COMPLETA.
# Espelha glmm_random_slope_full.R, mas com inclinação aleatória de GÊNERO por UF.
#
# Para cada desfecho de acesso/teto (ocp_qualif, y_top20, y_top10):
#   base (1|UF) vs random slope (1+sexo_fem|UF); LRT de fronteira (0.5*chi2_1+0.5*chi2_2);
#   tau2_sexo (variância do gap de gênero entre UFs), rho(intercepto,slope) e BLUPs por UF.
# (negro permanece como controle de efeito fixo.)
#
# Saidas:
#   outputs/tables/glmm_genero_varcomp.csv
#   outputs/tables/glmm_genero_blup_uf.csv
#   outputs/figures/glmm_genero_real.png
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

cat("=== GLMM Random Slope de GÊNERO (lme4) — populacao completa ===\n")
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
    horas_c = ifelse(!is.na(horas_c), horas_c, 0), idade_c = ifelse(!is.na(idade_c), idade_c, 0),
    ocp_qualif = as.integer(!is.na(ocp_grupo_cbo) &
                  as.character(ocp_grupo_cbo) %in% c("dirigente","profissional","tecnico","administrativo")),
    y_top20 = as.integer(renda_bruta >= quantile(renda_bruta, 0.80, na.rm = TRUE)),
    y_top10 = as.integer(renda_bruta >= quantile(renda_bruta, 0.90, na.rm = TRUE)),
    UF = as.character(UF),
    renda_media_upa_c = media_renda_upa_z, edu_media_upa_c = media_educ_upa_z)
cat(sprintf("  N efetivo: %s | UFs: %d\n", format(nrow(df), big.mark=","), n_distinct(df$UF)))

CTRL <- paste("negro + educ_medio_completo + educ_superior_completo + educ_pos_graduacao",
              "+ idade_c + I(idade_c^2) + horas_c + emprego_formal + setor_publico",
              "+ conta_propria + trab_domestico + renda_media_upa_c + edu_media_upa_c")
ctrl_fast <- glmerControl(optimizer="bobyqa", optCtrl=list(maxfun=3e5), calc.derivs=FALSE)
boundary_p <- function(lr) 0.5*pchisq(lr,1,lower.tail=FALSE) + 0.5*pchisq(lr,2,lower.tail=FALSE)

varcomp_rows <- list(); blup_rows <- list()
fit_rs <- function(y) {
  f_base <- as.formula(paste(y, "~ sexo_fem +", CTRL, "+ (1 | UF)"))
  f_rs   <- as.formula(paste(y, "~ sexo_fem +", CTRL, "+ (1 + sexo_fem | UF)"))
  cat(sprintf("\n--- [%s] base (1|UF) ...\n", y)); t0 <- proc.time()
  mb <- glmer(f_base, data=df, family=binomial, nAGQ=0, control=ctrl_fast)
  cat(sprintf("    base ok %.1f min | rs (1+sexo_fem|UF) ...\n", (proc.time()-t0)[3]/60)); t0 <- proc.time()
  mr <- glmer(f_rs, data=df, family=binomial, nAGQ=0, control=ctrl_fast)
  cat(sprintf("    rs ok %.1f min\n", (proc.time()-t0)[3]/60))
  vc <- VarCorr(mr)$UF
  tau2_int <- vc[1,1]; tau2_sex <- vc[2,2]; cov_in <- vc[1,2]
  rho <- if (tau2_int>0 && tau2_sex>0) cov_in/sqrt(tau2_int*tau2_sex) else 0
  b <- fixef(mr)["sexo_fem"]; lr <- as.numeric(2*(logLik(mr)-logLik(mb))); p <- boundary_p(lr)
  cat(sprintf("    OR_sexo(fixo)=%.4f | tau2_sexo=%.5f (SD=%.4f) | rho=%.3f | LR=%.1f p=%.3g\n",
              exp(b), tau2_sex, sqrt(max(tau2_sex,0)), rho, lr, p))
  varcomp_rows[[y]] <<- data.frame(desfecho=y, OR_sexo=exp(b), b_sexo=b,
    tau2_intercepto=tau2_int, tau2_sexo=tau2_sex, sd_sexo=sqrt(max(tau2_sex,0)),
    cov_int_sexo=cov_in, rho=rho, LR=lr, p_boundary=p, OR_base=exp(fixef(mb)["sexo_fem"]),
    N=nrow(df), n_UF=n_distinct(df$UF), row.names=NULL)
  re <- ranef(mr)$UF
  blup_rows[[y]] <<- data.frame(desfecho=y, UF=rownames(re), sigla=UF_SIGLA[rownames(re)],
    u0=re[,1], u1_sexo=re[,2], gap_log=b+re[,2], OR_uf=exp(b+re[,2]), row.names=NULL)
  invisible(NULL)
}

for (y in c("ocp_qualif","y_top20","y_top10")) fit_rs(y)

write.csv(do.call(rbind, varcomp_rows), file.path(TABLES,"glmm_genero_varcomp.csv"), row.names=FALSE)
write.csv(do.call(rbind, blup_rows),   file.path(TABLES,"glmm_genero_blup_uf.csv"),  row.names=FALSE)

bl <- do.call(rbind, blup_rows)
bl$desfecho <- factor(bl$desfecho, levels=c("ocp_qualif","y_top20","y_top10"))
p <- ggplot(bl, aes(x=OR_uf, y=reorder(sigla, OR_uf))) +
  geom_vline(xintercept=1, linetype="dashed", color="gray50") +
  geom_point(aes(color=desfecho), size=1.6) +
  facet_wrap(~desfecho, scales="free_x", nrow=1) +
  labs(title="Random slope GLMM de GÊNERO (lme4) — Odds Ratio de sexo_fem por UF",
       subtitle="OR<1 = desvantagem feminina | dispersao entre UFs = heterogeneidade geografica (BLUP)",
       x="Odds Ratio de sexo_fem por UF", y=NULL,
       caption="GLMM logistico (1+sexo_fem|UF), nAGQ=0, populacao completa. PNAD 2016-2025.") +
  scale_x_log10() + theme_minimal(base_size=10) +
  theme(legend.position="none", plot.title=element_text(face="bold", color="#7B3294"))
ggsave(file.path(FIGURES,"glmm_genero_real.png"), p, width=15, height=5, dpi=150)

cat("\n=== SUMARIO — RANDOM SLOPE GLMM DE GENERO ===\n")
print(do.call(rbind, varcomp_rows)[,c("desfecho","OR_sexo","tau2_sexo","sd_sexo","rho","LR","p_boundary")], digits=4)
cat("\nArquivos: glmm_genero_varcomp.csv | glmm_genero_blup_uf.csv | glmm_genero_real.png\n")
cat("=== CONCLUIDO ===\n")
