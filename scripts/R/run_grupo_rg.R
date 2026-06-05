# run_grupo_rg.R
# ==============================================================================
# EXPLORATÓRIO (não incorporado ao trabalho até avaliação).
# Interseccionalidade raça×gênero via grupo_rg de 4 níveis no GLMM de acesso
# (ocp_qualif = CBO 1-4), população completa, com educ_missing.
#
#   grupo_rg (ref = homem_branco):
#     homem_branco (negro=0, sexo_fem=0) | mulher_branca (0,1)
#     homem_negro  (1,0)                 | mulher_negra  (1,1)
#
# Modelo A — 4 grupos, intercepto aleatório:  ocp_qualif ~ grupo_rg + CTRL + (1|UPA)
# Modelo B — RANDOM SLOPE + INTERAÇÃO:         ocp_qualif ~ negro*sexo_fem + CTRL + (1+negro|UF)
#            (compara com base (1|UF) por LRT; testa se a barreira racial, que varia
#             por UF, também difere por gênero — a pergunta interseccional central)
# ==============================================================================
.libPaths(c("C:/Users/user/R/win-library/4.6", .libPaths()))
suppressMessages({
  library(arrow); library(lme4); library(dplyr); library(broom.mixed)
})
ROOT   <- "C:/Users/user/Documents/ProjetoRacismoPNAD"
TABLES <- file.path(ROOT, "outputs", "tables")
t0 <- Sys.time()

cat("== Carregando dados ==\n")
df_raw <- read_parquet(file.path(ROOT, "data", "processed", "features.parquet"))

df <- df_raw %>%
  filter(pea == 1, !is.na(renda_bruta), renda_bruta > 0,
         !is.na(negro), !is.na(sexo_fem), !is.na(UPA),
         !is.na(media_renda_upa_z), !is.na(media_educ_upa_z)) %>%
  mutate(
    negro = as.integer(negro), sexo_fem = as.integer(sexo_fem),
    educ_medio_completo    = as.integer(!is.na(educ_medio_completo) & educ_medio_completo == 1),
    educ_superior_completo = as.integer(!is.na(educ_superior_completo) & educ_superior_completo == 1),
    educ_pos_graduacao     = as.integer(!is.na(educ_pos_graduacao) & educ_pos_graduacao == 1),
    educ_missing   = as.integer(is.na(educ_cat)),
    emprego_formal = as.integer(!is.na(emprego_formal) & emprego_formal == 1),
    setor_publico  = as.integer(!is.na(setor_publico) & setor_publico == 1),
    conta_propria  = as.integer(!is.na(conta_propria) & conta_propria == 1),
    trab_domestico = as.integer(!is.na(trab_domestico) & trab_domestico == 1),
    horas_c = ifelse(!is.na(horas_c), horas_c, 0),
    idade_c = ifelse(!is.na(idade_c), idade_c, 0),
    ocp_qualif = as.integer(!is.na(ocp_grupo_cbo) &
                  as.character(ocp_grupo_cbo) %in% c("dirigente","profissional","tecnico","administrativo")),
    UF = as.character(UF), UPA = as.character(UPA),
    renda_media_upa_c = media_renda_upa_z, edu_media_upa_c = media_educ_upa_z,
    grupo_rg = factor(
      dplyr::case_when(
        negro == 0 & sexo_fem == 0 ~ "homem_branco",
        negro == 0 & sexo_fem == 1 ~ "mulher_branca",
        negro == 1 & sexo_fem == 0 ~ "homem_negro",
        TRUE                       ~ "mulher_negra"),
      levels = c("homem_branco","mulher_branca","homem_negro","mulher_negra"))
  )
cat(sprintf("  N=%s | UFs=%d | UPAs=%s\n", format(nrow(df), big.mark=","),
            n_distinct(df$UF), format(n_distinct(df$UPA), big.mark=",")))
print(round(prop.table(table(df$grupo_rg))*100, 1))

CTRL <- paste("educ_medio_completo + educ_superior_completo + educ_pos_graduacao + educ_missing",
              "+ idade_c + I(idade_c^2) + horas_c",
              "+ emprego_formal + setor_publico + conta_propria + trab_domestico",
              "+ renda_media_upa_c + edu_media_upa_c")
ctrl_fast <- glmerControl(optimizer="bobyqa", optCtrl=list(maxfun=3e5), calc.derivs=FALSE)

# ── Modelo A: 4 grupos (intercepto aleatório por UPA) ─────────────────────────
cat("\n== Modelo A: ocp_qualif ~ grupo_rg + CTRL + (1|UPA) ==\n")
fA <- as.formula(paste("ocp_qualif ~ grupo_rg +", CTRL, "+ (1 | UPA)"))
mA <- glmer(fA, data=df, family=binomial, nAGQ=0, control=ctrl_fast)
orA <- broom.mixed::tidy(mA, effects="fixed", conf.int=TRUE, exponentiate=TRUE) %>%
  filter(grepl("grupo_rg", term)) %>% select(term, OR=estimate, ci_low=conf.low, ci_high=conf.high, p.value)
cat("  Odds Ratios vs. HOMEM BRANCO (ref):\n"); print(as.data.frame(orA), digits=4)
write.csv(orA, file.path(TABLES, "grupo_rg_glmm_ocp.csv"), row.names=FALSE)

# ── Modelo B: random slope de negro por UF + interação negro:sexo_fem ──────────
cat("\n== Modelo B: random slope + interação ==\n")
fB_base <- as.formula(paste("ocp_qualif ~ negro * sexo_fem +", CTRL, "+ (1 | UF)"))
fB_rs   <- as.formula(paste("ocp_qualif ~ negro * sexo_fem +", CTRL, "+ (1 + negro | UF)"))
cat("  ajustando base (1|UF)...\n"); mB_base <- glmer(fB_base, data=df, family=binomial, nAGQ=0, control=ctrl_fast)
cat("  ajustando rs (1+negro|UF)...\n"); mB_rs <- glmer(fB_rs,  data=df, family=binomial, nAGQ=0, control=ctrl_fast)

fe <- fixef(mB_rs)
b_n <- fe[["negro"]]; b_s <- fe[["sexo_fem"]]; b_int <- fe[["negro:sexo_fem"]]
vc <- as.data.frame(VarCorr(mB_rs))
tau_int <- vc$vcov[vc$grp=="UF" & vc$var1=="(Intercept)" & is.na(vc$var2)]
tau_neg <- vc$vcov[vc$grp=="UF" & vc$var1=="negro" & is.na(vc$var2)]
rho     <- vc$sdcor[vc$grp=="UF" & vc$var1=="(Intercept)" & !is.na(vc$var2) & vc$var2=="negro"]
lrt <- anova(mB_base, mB_rs)

cat(sprintf("\n  --- Efeitos fixos (OR) ---\n"))
cat(sprintf("  negro (homem)            OR = %.4f\n", exp(b_n)))
cat(sprintf("  sexo_fem (branco)        OR = %.4f\n", exp(b_s)))
cat(sprintf("  negro:sexo_fem (interac) OR = %.4f  (>1 = sub-aditivo)\n", exp(b_int)))
cat(sprintf("\n  --- 4 grupos derivados (OR vs homem branco) ---\n"))
cat(sprintf("  homem_branco  = 1 (ref)\n"))
cat(sprintf("  mulher_branca = %.4f\n", exp(b_s)))
cat(sprintf("  homem_negro   = %.4f\n", exp(b_n)))
cat(sprintf("  mulher_negra  = %.4f\n", exp(b_n + b_s + b_int)))
cat(sprintf("\n  --- Heterogeneidade geográfica do efeito 'negro' (random slope por UF) ---\n"))
cat(sprintf("  tau2_intercepto = %.5f | tau2_negro = %.5f (SD=%.4f) | rho = %.3f\n",
            tau_int, tau_neg, sqrt(tau_neg), rho))
cat(sprintf("  LRT random slope: ChiSq=%.1f  df=%d  p=%.3g\n",
            lrt$Chisq[2], lrt$Df[2], lrt$`Pr(>Chisq)`[2]))

res <- data.frame(
  param = c("OR_homem_negro","OR_mulher_branca","OR_mulher_negra","OR_interacao_negroXsexo",
            "tau2_negro_UF","sd_negro_UF","rho_int_slope","LRT_chisq","LRT_p"),
  valor = c(exp(b_n), exp(b_s), exp(b_n+b_s+b_int), exp(b_int),
            tau_neg, sqrt(tau_neg), rho, lrt$Chisq[2], lrt$`Pr(>Chisq)`[2]))
write.csv(res, file.path(TABLES, "grupo_rg_glmm_rs_interacao.csv"), row.names=FALSE)
cat(sprintf("\n== CONCLUÍDO em %.1f min ==\n", as.numeric(difftime(Sys.time(), t0, units="mins"))))
