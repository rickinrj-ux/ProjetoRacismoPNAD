"""
run_hlm_m4.py
=============
M4 (random slope de educ_ord_c por UPA) + ICC estratificado por raça +
pseudo-R² de Nakagawa-Schielzeth (2013) para todos os modelos HLM.

Usa 20% da amostra (seed=42) para viabilidade computacional.
Os resultados são salvos em outputs/tables/ e outputs/figures/.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import logging
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
TABLES  = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

sys.path.insert(0, str(ROOT / "src"))
from multilevel_model import (
    load_features,
    compute_nakagawa_r2,
    fit_random_slope_model,
    compute_race_stratified_icc,
    plot_random_slope_effects,
    save_m4_outputs,
    FORMULA_M4,
    FORMULAS,
)

SAMPLE_FRAC = None   # None = população completa
SEED        = 42

# ── Carregar dados ────────────────────────────────────────────────────────────
_label = f"{int(SAMPLE_FRAC*100)}% amostra" if SAMPLE_FRAC else "população completa"
logger.info(f"Carregando dados ({_label}, seed={SEED}) ...")
df = load_features(sample_frac=SAMPLE_FRAC)
logger.info(
    f"  {len(df):,} obs | {df['UPA_str'].nunique():,} UPAs | "
    f"Negros={int((df['negro']==1).sum()):,} | Brancos={int((df['negro']==0).sum()):,}"
)

# ── Modelo de referência M3-equiv. para comparação (groups=UPA_str, sem RE UF) ─
logger.info("\n[1] Ajustando M3-equiv. (sem random slope, groups=UPA_str) ...")
# Versão 2-nível de M3 para base de comparação com M4
FORMULA_M3_2L = (
    "log_renda ~ negro + sexo_fem + idade_c + idade_sq + educ_ord_c"
    " + log_horas + urbano + C(Ano)"
    " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
    " + C(UF_str)"
)
try:
    m3_2l = smf.mixedlm(FORMULA_M3_2L, data=df, groups=df["UPA_str"]).fit(
        method="lbfgs", maxiter=1500, reml=False
    )
    var_upa_m3 = float(m3_2l.cov_re.iloc[0, 0])
    ns_m3 = compute_nakagawa_r2(m3_2l, sigma2_u=var_upa_m3)
    b_negro_m3 = m3_2l.params.get("negro", np.nan)
    logger.info(
        f"  M3-equiv.: β_negro={b_negro_m3:.4f} ({(np.exp(b_negro_m3)-1)*100:.1f}%) | "
        f"R²m={ns_m3['R2m']:.3f} | R²c={ns_m3['R2c']:.3f}"
    )
except Exception as e:
    logger.warning(f"  M3-equiv. falhou: {e}")
    m3_2l = None; ns_m3 = {"R2m": np.nan, "R2c": np.nan}; b_negro_m3 = np.nan

# ── M4: Random Slope ──────────────────────────────────────────────────────────
logger.info("\n[2] Ajustando M4 (random slope educ_ord_c por UPA) ...")
m4_res = fit_random_slope_model(df)

logger.info(
    f"\n  β_negro = {m4_res['b_negro']:.4f} ({(np.exp(m4_res['b_negro'])-1)*100:.1f}%)\n"
    f"  β_educ_c = {m4_res['b_educ_c']:.4f}\n"
    f"  τ²₀ = {m4_res['tau2_int']:.4f}  τ²₁ = {m4_res['tau2_slope']:.4f}\n"
    f"  corr(u₀,u₁) = {m4_res['corr_int_slope']:.3f}\n"
    f"  ICC_UPA = {m4_res['icc_upa']:.4f}\n"
    f"  R²m = {m4_res['nakagawa']['R2m']:.4f}  R²c = {m4_res['nakagawa']['R2c']:.4f}\n"
    f"  AIC = {m4_res['aic']:.1f}  BIC = {m4_res['bic']:.1f}"
)

# LRT: M3-equiv. vs M4 (random slope acrescenta τ²₁ e τ₀₁ = +2 parâmetros)
if m3_2l is not None:
    from scipy import stats as scipy_stats
    lr_stat = 2 * (m4_res["llf"] - m3_2l.llf)
    p_lrt   = scipy_stats.chi2.sf(lr_stat, df=2)
    stars_lrt = "***" if p_lrt < 0.001 else "**" if p_lrt < 0.01 else "*" if p_lrt < 0.05 else "ns"
    logger.info(f"  LRT M3→M4: χ²(2)={lr_stat:.2f}  p={p_lrt:.4e}  {stars_lrt}")
else:
    lr_stat = p_lrt = np.nan; stars_lrt = "—"

# ── ICC estratificado por raça ────────────────────────────────────────────────
logger.info("\n[3] ICC estratificado por raça ...")
icc_racial = compute_race_stratified_icc(df)
print(icc_racial.to_string(index=False))

# ── Tabela Nakagawa R² para todos os modelos ──────────────────────────────────
logger.info("\n[4] Pseudo-R² Nakagawa-Schielzeth ...")
nakagawa_rows = []

# M3-equiv. (sem random slope)
nakagawa_rows.append({
    "Modelo": "M3-equiv. (sem slope)",
    **ns_m3,
    "LRT_vs_prev": "—", "p_LRT": "—",
})

# M4 (com random slope)
ns_m4 = m4_res["nakagawa"]
nakagawa_rows.append({
    "Modelo": "M4 (random slope educ)",
    **ns_m4,
    "LRT_vs_prev": round(lr_stat, 2) if not np.isnan(lr_stat) else "—",
    "p_LRT": f"{p_lrt:.4e}" if not np.isnan(p_lrt) else "—",
})

df_ns = pd.DataFrame(nakagawa_rows)
print("\nPseudo-R² Nakagawa-Schielzeth:")
print(df_ns[["Modelo", "sigma2_f", "sigma2_u", "sigma2_e", "R2m", "R2c"]].to_string(index=False))

# ── Figura random slopes ──────────────────────────────────────────────────────
logger.info("\n[5] Gerando figura random slopes ...")
try:
    plot_random_slope_effects(m4_res, df)
    logger.info("  hlm_m4_random_slope.png salvo.")
except Exception as e:
    logger.warning(f"  Figura falhou: {e}")

# ── Salvar outputs ────────────────────────────────────────────────────────────
logger.info("\n[6] Salvando outputs ...")
save_m4_outputs(m4_res, icc_racial, nakagawa_rows)

# Adiciona LRT ao CSV de variância
vc_df = pd.read_csv(TABLES / "hlm_m4_variancia.csv")
lrt_row = pd.DataFrame([{
    "componente": f"LRT M3→M4 χ²(2)={lr_stat:.2f} p={p_lrt:.4e} {stars_lrt}",
    "variancia": lr_stat,
}])
vc_df = pd.concat([vc_df, lrt_row], ignore_index=True)
vc_df.to_csv(TABLES / "hlm_m4_variancia.csv", index=False, encoding="utf-8")

logger.info("\n=== CONCLUÍDO ===")
logger.info("Outputs:")
for f in [
    "hlm_m4_coeficientes.csv", "hlm_m4_variancia.csv",
    "hlm_m4.tex", "hlm_icc_racial.csv", "hlm_nakagawa_r2.csv",
]:
    p = TABLES / f
    logger.info(f"  {'OK' if p.exists() else 'FALTANDO'}: {f}")
fig_m4 = FIGURES / "hlm_m4_random_slope.png"
logger.info(f"  {'OK' if fig_m4.exists() else 'FALTANDO'}: hlm_m4_random_slope.png")

# ── Sumário para TCC ─────────────────────────────────────────────────────────
sep = "=" * 70
print(f"\n{sep}")
print("  SUMÁRIO M4 — PARA O TCC")
print(sep)
print(f"  β_negro (M4) = {m4_res['b_negro']:.4f}  ({(np.exp(m4_res['b_negro'])-1)*100:.1f}%)")
print(f"  τ²₁ (slope educ) = {m4_res['tau2_slope']:.4f}")
print(f"  corr(u₀,u₁) = {m4_res['corr_int_slope']:.3f}")
print(f"  R²m = {ns_m4['R2m']:.4f}  |  R²c = {ns_m4['R2c']:.4f}")
icc_n = icc_racial.loc[icc_racial["Grupo"]=="Negros", "ICC_UPA"].values[0]
icc_b = icc_racial.loc[icc_racial["Grupo"]=="Brancos", "ICC_UPA"].values[0]
print(f"  ICC_UPA Negros = {icc_n:.4f}  |  Brancos = {icc_b:.4f}  |  Δ = {icc_n-icc_b:+.4f}")
print(f"  LRT M3→M4: χ²(2)={lr_stat:.2f}  p={p_lrt:.4e}  {stars_lrt}")
print(sep)
