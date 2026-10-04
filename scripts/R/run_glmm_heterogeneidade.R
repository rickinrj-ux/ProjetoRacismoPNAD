# run_glmm_heterogeneidade.R  (04/10/2026)
# ==============================================================================
# Heterogeneidade do GLMM de acesso (A2 de glmm_glassceil.R: individual + contexto do
# bairro + UF e ano fixos + intercepto aleatório de UPA), na mesma base e especificação:
#   cor3   — pardo e preto separados (em vez de "negro"), nos 3 desfechos
#   setor  — A2 estimado separadamente no setor privado e no público, nos 3 desfechos
#   topuf  — top 10% da renda DENTRO de cada UF (o corte nacional mistura geografia)
# Um modelo por chamada (memória volta ao SO): Rscript run_glmm_heterogeneidade.R <bloco> <desfecho> [setor]
# Saída: acrescenta uma linha em outputs/tables/glmm_heterogeneidade.csv
# ==============================================================================
.libPaths(c("C:/Users/user/R/win-library/4.6", .libPaths()))
suppressPackageStartupMessages({ library(arrow); library(lme4); library(dplyr) })
args   <- commandArgs(trailingOnly = TRUE)
BLOCO  <- args[1]; DESF <- args[2]; SETOR <- if (length(args) >= 3) as.integer(args[3]) else NA
ROOT   <- "C:/Users/user/Documents/ProjetoRacismoPNAD"
OUT    <- file.path(ROOT, "outputs", "tables", "glmm_heterogeneidade.csv")
t0 <- proc.time()

cols <- c("negro","V2010","sexo_fem","idade_c","idade_sq","educ_fund_completo","educ_medio_completo",
          "educ_superior_completo","educ_pos_graduacao","pct_negro_upa_z","tx_desemprego_upa_z",
          "media_educ_upa_z","media_renda_upa_z","setor_publico","ocp_dirigente","ocp_profissional",
          "ocp_tecnico","ocp_administrativo","urbano","Ano","renda_bruta","pea","UF","UPA")
df <- read_parquet(file.path(ROOT, "data/processed/features.parquet"), col_select = all_of(cols))
# mesmos filtros e codificação de glmm_glassceil.R
df <- df |>
  filter(pea == 1, !is.na(renda_bruta), renda_bruta > 0, !is.na(negro), !is.na(sexo_fem),
         !is.na(media_renda_upa_z), !is.na(media_educ_upa_z),
         !is.na(pct_negro_upa_z), !is.na(tx_desemprego_upa_z)) |>
  mutate(
    negro = as.integer(negro), sexo_fem = as.integer(sexo_fem),
    pardo = as.integer(V2010 == 4), preto = as.integer(V2010 == 2),
    educ_medio_completo    = as.integer(!is.na(educ_medio_completo) & educ_medio_completo == 1),
    educ_superior_completo = as.integer(!is.na(educ_superior_completo) & educ_superior_completo == 1),
    educ_pos_graduacao     = as.integer(!is.na(educ_pos_graduacao) & educ_pos_graduacao == 1),
    educ_fund_completo = as.integer(!is.na(educ_fund_completo) & educ_fund_completo == 1),
    urbano             = as.integer(!is.na(urbano) & urbano == 1),
    Ano                = factor(Ano),
    setor_publico  = as.integer(!is.na(setor_publico) & setor_publico == 1),
    idade_c        = ifelse(is.na(idade_c), 0, idade_c),
    idade_sq       = ifelse(is.na(idade_sq), idade_c^2, idade_sq),
    ocp_qualif = as.integer(coalesce(ocp_dirigente, 0) == 1 | coalesce(ocp_profissional, 0) == 1 |
                            coalesce(ocp_tecnico, 0) == 1 | coalesce(ocp_administrativo, 0) == 1),
    UPA = as.character(UPA), UF = factor(as.character(UF))
  )
q80 <- quantile(df$renda_bruta, 0.80); q90 <- quantile(df$renda_bruta, 0.90)
df$y_top20 <- as.integer(df$renda_bruta >= q80)
df$y_top10 <- as.integer(df$renda_bruta >= q90)
# top 10% DENTRO da UF: o corte nacional põe quase todo o topo nos estados ricos
df <- df |> group_by(UF) |> mutate(y_top10_uf = as.integer(renda_bruta >= quantile(renda_bruta, 0.90))) |> ungroup()
# cor em 3 categorias: brancos, pardos e pretos (V2010 = 1, 4, 2), os mesmos que formam negro = 0/1
if (BLOCO == "cor3") df <- df |> filter(V2010 %in% c(1, 2, 4))
if (BLOCO == "setor") df <- df |> filter(setor_publico == SETOR)

IND <- paste("sexo_fem + educ_fund_completo + educ_medio_completo + educ_superior_completo +",
             "educ_pos_graduacao + idade_c + idade_sq + urbano + Ano + UF")
CTX <- "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
RACA <- if (BLOCO == "cor3") "pardo + preto" else "negro"
y <- if (BLOCO == "topuf") "y_top10_uf" else DESF
f <- as.formula(paste(y, "~", RACA, "+", IND, "+", CTX, "+ (1 | UPA)"))
cat(sprintf("== %s | %s | setor=%s | N=%s | UPAs=%s | prevalência %.1f%%\n", BLOCO, y, SETOR,
            format(nrow(df), big.mark = ","), format(n_distinct(df$UPA), big.mark = ","),
            100 * mean(df[[y]])))
ctrl <- glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 3e5), calc.derivs = FALSE)
m <- glmer(f, data = df, family = binomial(link = "logit"), nAGQ = 0, control = ctrl)
co <- summary(m)$coefficients
linhas <- lapply(strsplit(RACA, " \\+ ")[[1]], function(v) {
  b <- co[v, "Estimate"]; se <- co[v, "Std. Error"]
  data.frame(bloco = BLOCO, desfecho = y, setor = SETOR, termo = v, OR = exp(b),
             CI95_lo = exp(b - 1.96 * se), CI95_hi = exp(b + 1.96 * se), beta = b, se = se,
             N = nrow(df), n_upa = n_distinct(df$UPA), prevalencia = mean(df[[y]]),
             minutos = as.numeric((proc.time() - t0)[3]) / 60)
})
res <- do.call(rbind, linhas)
print(res[, c("termo", "OR", "CI95_lo", "CI95_hi")])
write.table(res, OUT, sep = ",", row.names = FALSE, col.names = !file.exists(OUT), append = file.exists(OUT))
cat(sprintf("OK -> %s | %.1f min\n", OUT, as.numeric((proc.time() - t0)[3]) / 60))
