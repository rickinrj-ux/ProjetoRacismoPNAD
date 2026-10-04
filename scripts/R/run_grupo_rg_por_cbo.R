# run_grupo_rg_por_cbo.R  (E2.16, 03/10/2026)
# ==============================================================================
# A "vantagem" da mulher negra no acesso (OR ~1,31 em CBO 1-4, run_grupo_rg_topo.R) é
# composição? Descritivamente ela tem metade da presença do homem branco entre dirigentes
# e o dobro no apoio administrativo. Aqui o mesmo modelo, com a MESMA especificação do
# run_grupo_rg_topo.R (para comparar com o OR publicado), estimado por grande grupo CBO:
#   1 dirigente | 2 profissional | 3 técnico | 4 administrativo | CBO 1-2 (alta qualificação)
# 4 grupos raça×gênero (ref = homem branco) via negro*sexo_fem + (1|UPA).
# Saída: outputs/tables/grupo_rg_por_cbo.csv (OR e IC 95% de cada grupo, interação)
# ==============================================================================
.libPaths(c("C:/Users/user/R/win-library/4.6", .libPaths()))
suppressMessages({ library(arrow); library(lme4); library(dplyr) })
ROOT   <- "C:/Users/user/Documents/ProjetoRacismoPNAD"; TABLES <- file.path(ROOT,"outputs","tables")
t0 <- Sys.time()

# só as colunas do modelo: roda em paralelo com a QR (memória, 03/10/2026)
COLS <- c("pea","renda_bruta","negro","sexo_fem","UPA","media_renda_upa_z","media_educ_upa_z",
          "educ_fund_completo","educ_medio_completo","educ_superior_completo","educ_pos_graduacao",
          "emprego_formal","setor_publico","conta_propria","trab_domestico","horas_c","idade_c",
          "ocp_grupo_cbo","Ano")
df <- read_parquet(file.path(ROOT,"data","processed","features.parquet"), col_select=all_of(COLS)) %>%
  filter(pea==1, !is.na(renda_bruta), renda_bruta>0, !is.na(negro), !is.na(sexo_fem),
         !is.na(UPA), !is.na(media_renda_upa_z), !is.na(media_educ_upa_z)) %>%
  mutate(
    negro=as.integer(negro), sexo_fem=as.integer(sexo_fem),
    educ_medio_completo=as.integer(!is.na(educ_medio_completo)&educ_medio_completo==1),
    educ_superior_completo=as.integer(!is.na(educ_superior_completo)&educ_superior_completo==1),
    educ_pos_graduacao=as.integer(!is.na(educ_pos_graduacao)&educ_pos_graduacao==1),
    emprego_formal=as.integer(!is.na(emprego_formal)&emprego_formal==1),
    setor_publico=as.integer(!is.na(setor_publico)&setor_publico==1),
    conta_propria=as.integer(!is.na(conta_propria)&conta_propria==1),
    trab_domestico=as.integer(!is.na(trab_domestico)&trab_domestico==1),
    horas_c=ifelse(!is.na(horas_c),horas_c,0), idade_c=ifelse(!is.na(idade_c),idade_c,0),
    cbo=as.character(ocp_grupo_cbo),
    y_dirigente=as.integer(!is.na(cbo) & cbo=="dirigente"),
    y_profissional=as.integer(!is.na(cbo) & cbo=="profissional"),
    y_tecnico=as.integer(!is.na(cbo) & cbo=="tecnico"),
    y_administrativo=as.integer(!is.na(cbo) & cbo=="administrativo"),
    y_cbo12=as.integer(!is.na(cbo) & cbo %in% c("dirigente","profissional")),
    UPA=as.character(UPA),
    renda_media_upa_c=media_renda_upa_z, edu_media_upa_c=media_educ_upa_z)
cat(sprintf("N=%s\n", format(nrow(df),big.mark=",")))

CTRL <- paste("educ_fund_completo + educ_medio_completo + educ_superior_completo + educ_pos_graduacao",
              "+ idade_c + I(idade_c^2) + horas_c + emprego_formal + setor_publico",
              "+ conta_propria + trab_domestico + renda_media_upa_c + edu_media_upa_c + factor(Ano)")
ctrl_fast <- glmerControl(optimizer="bobyqa", optCtrl=list(maxfun=3e5), calc.derivs=FALSE)

# OR e IC 95% de uma combinação linear dos efeitos fixos
or_ci <- function(b, V, w) {
  est <- sum(w * b); se <- sqrt(as.numeric(t(w) %*% V %*% w))
  c(exp(est), exp(est - 1.96*se), exp(est + 1.96*se))
}

out_f <- file.path(TABLES,"grupo_rg_por_cbo.csv")
res <- list()
for (y in c("y_dirigente","y_profissional","y_tecnico","y_administrativo","y_cbo12")) {
  t1 <- Sys.time()
  cat(sprintf("\n== %s ~ negro*sexo_fem + CTRL + (1|UPA) | prevalência %.1f%% ==\n", y, 100*mean(df[[y]])))
  f <- as.formula(paste(y, "~ negro * sexo_fem +", CTRL, "+ (1 | UPA)"))
  m <- glmer(f, data=df, family=binomial, nAGQ=0, control=ctrl_fast)
  nm <- c("negro","sexo_fem","negro:sexo_fem")
  b <- fixef(m)[nm]; V <- as.matrix(vcov(m))[nm, nm]
  mb <- or_ci(b, V, c(0,1,0)); hn <- or_ci(b, V, c(1,0,0))
  mn <- or_ci(b, V, c(1,1,1)); it <- or_ci(b, V, c(0,0,1))
  cat(sprintf("  OR vs homem branco: mulher branca=%.3f | homem negro=%.3f | mulher negra=%.3f [%.3f; %.3f] | interação=%.3f | %.1f min\n",
              mb[1], hn[1], mn[1], mn[2], mn[3], it[1], as.numeric(difftime(Sys.time(),t1,units="mins"))))
  res[[y]] <- data.frame(desfecho=y, prevalencia=mean(df[[y]]),
                         OR_mulher_branca=mb[1], OR_mb_lo=mb[2], OR_mb_hi=mb[3],
                         OR_homem_negro=hn[1], OR_hn_lo=hn[2], OR_hn_hi=hn[3],
                         OR_mulher_negra=mn[1], OR_mn_lo=mn[2], OR_mn_hi=mn[3],
                         OR_interacao=it[1], OR_int_lo=it[2], OR_int_hi=it[3],
                         n=nrow(df))
  write.csv(do.call(rbind, res), out_f, row.names=FALSE)   # grava a cada modelo
  rm(m); gc()
}
cat(sprintf("\nSalvo: grupo_rg_por_cbo.csv | %.1f min\n", as.numeric(difftime(Sys.time(),t0,units="mins"))))
