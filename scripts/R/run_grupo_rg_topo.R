# run_grupo_rg_topo.R  (EXPLORATÓRIO — quadro interseccional completo)
# ==============================================================================
# 4 grupos raça×gênero (ref = homem branco) em 3 desfechos, via interação
# negro*sexo_fem + (1|UPA). Mostra o gradiente acesso->renda:
#   ocp_qualif (acesso à categoria CBO 1-4) | y_top20 (teto salarial) | y_top10 (decil)
# Para cada um: ORs dos 4 grupos derivados + termo de interação (sub/super-aditivo).
# ==============================================================================
.libPaths(c("C:/Users/user/R/win-library/4.6", .libPaths()))
suppressMessages({ library(arrow); library(lme4); library(dplyr) })
ROOT   <- "C:/Users/user/Documents/ProjetoRacismoPNAD"; TABLES <- file.path(ROOT,"outputs","tables")
t0 <- Sys.time()

df <- read_parquet(file.path(ROOT,"data","processed","features.parquet")) %>%
  filter(pea==1, !is.na(renda_bruta), renda_bruta>0, !is.na(negro), !is.na(sexo_fem),
         !is.na(UPA), !is.na(media_renda_upa_z), !is.na(media_educ_upa_z)) %>%
  mutate(
    negro=as.integer(negro), sexo_fem=as.integer(sexo_fem),
    educ_medio_completo=as.integer(!is.na(educ_medio_completo)&educ_medio_completo==1),
    educ_superior_completo=as.integer(!is.na(educ_superior_completo)&educ_superior_completo==1),
    educ_pos_graduacao=as.integer(!is.na(educ_pos_graduacao)&educ_pos_graduacao==1),
    educ_missing=as.integer(is.na(educ_cat)),
    emprego_formal=as.integer(!is.na(emprego_formal)&emprego_formal==1),
    setor_publico=as.integer(!is.na(setor_publico)&setor_publico==1),
    conta_propria=as.integer(!is.na(conta_propria)&conta_propria==1),
    trab_domestico=as.integer(!is.na(trab_domestico)&trab_domestico==1),
    horas_c=ifelse(!is.na(horas_c),horas_c,0), idade_c=ifelse(!is.na(idade_c),idade_c,0),
    ocp_qualif=as.integer(!is.na(ocp_grupo_cbo) &
       as.character(ocp_grupo_cbo) %in% c("dirigente","profissional","tecnico","administrativo")),
    UPA=as.character(UPA),
    renda_media_upa_c=media_renda_upa_z, edu_media_upa_c=media_educ_upa_z)
q80<-quantile(df$renda_bruta,0.80,na.rm=TRUE); q90<-quantile(df$renda_bruta,0.90,na.rm=TRUE)
df$y_top20<-as.integer(df$renda_bruta>=q80); df$y_top10<-as.integer(df$renda_bruta>=q90)
cat(sprintf("N=%s\n", format(nrow(df),big.mark=",")))

CTRL <- paste("educ_medio_completo + educ_superior_completo + educ_pos_graduacao + educ_missing",
              "+ idade_c + I(idade_c^2) + horas_c + emprego_formal + setor_publico",
              "+ conta_propria + trab_domestico + renda_media_upa_c + edu_media_upa_c")
ctrl_fast <- glmerControl(optimizer="bobyqa", optCtrl=list(maxfun=3e5), calc.derivs=FALSE)

res <- list()
for (y in c("ocp_qualif","y_top20","y_top10")) {
  cat(sprintf("\n== %s : %s ~ negro*sexo_fem + CTRL + (1|UPA) ==\n", y, y))
  f <- as.formula(paste(y, "~ negro * sexo_fem +", CTRL, "+ (1 | UPA)"))
  m <- glmer(f, data=df, family=binomial, nAGQ=0, control=ctrl_fast)
  fe <- fixef(m); b_n<-fe[["negro"]]; b_s<-fe[["sexo_fem"]]; b_i<-fe[["negro:sexo_fem"]]
  or_hn<-exp(b_n); or_mb<-exp(b_s); or_mn<-exp(b_n+b_s+b_i); or_int<-exp(b_i)
  pen_h <- or_hn-1; pen_m <- or_mn/or_mb-1   # penalidade racial entre homens / entre mulheres
  cat(sprintf("  homem_branco=1 | mulher_branca=%.3f | homem_negro=%.3f | mulher_negra=%.3f\n",
              or_mb, or_hn, or_mn))
  cat(sprintf("  interacao negro:sexo_fem OR=%.3f (%s)\n", or_int,
              ifelse(or_int>1,"sub-aditivo","super-aditivo")))
  cat(sprintf("  penalidade racial: entre homens=%.1f%% | entre mulheres=%.1f%%\n",
              100*pen_h, 100*pen_m))
  res[[y]] <- data.frame(desfecho=y, OR_mulher_branca=or_mb, OR_homem_negro=or_hn,
                         OR_mulher_negra=or_mn, OR_interacao=or_int,
                         pen_racial_homens_pct=100*pen_h, pen_racial_mulheres_pct=100*pen_m)
}
out <- do.call(rbind, res)
write.csv(out, file.path(TABLES,"grupo_rg_4grupos_desfechos.csv"), row.names=FALSE)
cat(sprintf("\nSalvo: grupo_rg_4grupos_desfechos.csv | %.1f min\n", as.numeric(difftime(Sys.time(),t0,units="mins"))))
