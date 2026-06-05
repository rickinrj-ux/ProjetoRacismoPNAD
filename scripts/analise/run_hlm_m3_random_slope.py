"""
run_hlm_m3_random_slope.py
===========================
Estima M3 com inclinação aleatória (random slope) para `negro` por UF.

PERGUNTA: o penalidade racial varia significativamente entre estados?
  - H0: tau2_negro = 0  (discriminação homogênea entre UFs)
  - H1: tau2_negro > 0  (discriminação geograficamente heterogênea)

ESTRATÉGIA:
  - Agrupamento por UF (27 grupos): viável computacionalmente.
    UPA teria 40k grupos + slope = inviável.
  - Duas especificações:
      1. Correlacionada:  RE = (u0j, u1j) ~ BVN([0,0], Σ)
         Estima covariância entre intercepto e slope de negro.
         Pergunta extra: em UFs com maior gap médio, o gap racial é maior?
      2. Não-correlacionada: u0j ⊥ u1j (mais estável, menos parâmetros).
         Tenta primeiro; se não convergir, cai para correlacionada.
  - LRT: M3_rs vs M3_base (intercepto aleatório apenas), ML (não REML).
    H0 na fronteira tau2=0 → p-valor = 0.5*chi2(1) + 0.5*chi2(2) (mix).

SAÍDA:
  outputs/tables/hlm_m3_random_slope_varcov.csv   — componentes de variância
  outputs/tables/hlm_m3_random_slope_coefs.csv    — coeficientes fixos
  outputs/tables/hlm_m3_random_slope_lrt.csv      — LRT vs M3 base
  logs/hlm_m3_random_slope.log

AMOSTRA:
  SAMPLE_FRAC = 0.20  (1.54M obs) para verificar convergência e τ²₁.
  Se significativo, altere para None para população completa.
"""

# --- bootstrap raiz do projeto (reorg estrutura) ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---


import sys, logging, time, warnings
from pathlib import Path

sys.path.insert(0, "src")

Path("logs").mkdir(exist_ok=True)
LOG_FILE = "logs/hlm_m3_random_slope.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

# ── Configuração ───────────────────────────────────────────────────────────────
SAMPLE_FRAC    = None   # None = pop. completa
RANDOM_STATE   = 42
FEATURES_PATH  = Path("data/processed/features.parquet")
OUTPUTS        = Path("outputs/tables")
OUTPUTS.mkdir(parents=True, exist_ok=True)

# Fórmula M3 (igual ao run_hlm_serie_completa.py)
_IND = ("negro + sexo_fem + idade_c + idade_sq"
        " + educ_fund_completo + educ_medio_completo"
        " + educ_superior_completo + educ_pos_graduacao + educ_missing"
        " + log_horas + urbano + C(Ano)")
_UPA = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
_UF  = "pct_negro_uf_z + tx_desemprego_uf_z + media_educ_uf_z"

FORMULA_M3 = f"log_renda ~ {_IND} + {_UPA} + {_UF}"

MODEL_VARS = [
    "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao", "educ_missing",
    "log_horas", "urbano", "Ano",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "pct_negro_uf_z",  "tx_desemprego_uf_z",  "media_educ_uf_z",
    "UPA", "UF",
]


# ── Carga de dados ─────────────────────────────────────────────────────────────

def load_data():
    logger.info(f"Carregando {FEATURES_PATH} ...")
    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    logger.info(f"  Com renda positiva: {len(df):,}")

    df["educ_missing"] = df["educ_cat"].isna().astype("int8") if "educ_cat" in df.columns else 0

    if "log_horas" not in df.columns and "horas_trabalhadas" in df.columns:
        df["log_horas"] = np.log(df["horas_trabalhadas"].clip(lower=1))
    if "urbano" not in df.columns:
        df["urbano"] = (df["V1022"] == 1).astype("int8") if "V1022" in df.columns else 1

    df = df.dropna(subset=MODEL_VARS).reset_index(drop=True)

    # Filtro UPA >= 10 obs (consistência com HLM principal)
    upa_counts = df["UPA"].value_counts()
    df = df[df["UPA"].isin(upa_counts[upa_counts >= 10].index)].reset_index(drop=True)
    logger.info(f"  Após filtro UPA>=10: {len(df):,}")

    if SAMPLE_FRAC:
        df = df.sample(frac=SAMPLE_FRAC, random_state=RANDOM_STATE).reset_index(drop=True)
        logger.info(f"  Amostra {SAMPLE_FRAC*100:.0f}%: {len(df):,}")

    df["UF_str"] = df["UF"].astype(str)
    df["log_renda"] = df["log_renda"].astype(float)
    logger.info(f"  UFs: {df['UF_str'].nunique()} | UPAs: {df['UPA'].nunique():,}")
    return df


# ── Modelo base M3 (intercepto aleatório, ML para LRT) ────────────────────────

def fit_base(df, reml=True):
    label = "M3_base" + ("_REML" if reml else "_ML")
    logger.info(f"[{label}] Ajustando intercepto aleatório por UF ...")
    t0 = time.time()
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        model  = smf.mixedlm(FORMULA_M3, data=df, groups=df["UF_str"])
        result = model.fit(method="powell", maxiter=500, reml=reml)
    elapsed = time.time() - t0
    b_neg   = result.params.get("negro", np.nan)
    tau2_uf = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] > 0 else 0.0
    sigma2  = float(result.scale)
    icc     = tau2_uf / (tau2_uf + sigma2) if (tau2_uf + sigma2) > 0 else 0.0
    logger.info(
        f"[{label}] OK em {elapsed:.0f}s | b_negro={b_neg:.4f} | "
        f"tau2_UF={tau2_uf:.5f} | sigma2={sigma2:.4f} | ICC={icc:.4f}"
    )
    return result, tau2_uf, sigma2, icc


# ── M3 com random slope para negro ────────────────────────────────────────────

def fit_random_slope(df, correlated=False, reml=True):
    """
    re_formula="~negro" → random intercept + random slope para negro.
    correlated=False  → inicia com modelo não-correlacionado (mais estável).
    correlated=True   → estima Σ completa (2×2).
    """
    label = ("M3_rs_corr" if correlated else "M3_rs_uncorr") + ("_REML" if reml else "_ML")
    logger.info(f"[{label}] Ajustando random slope para negro por UF ...")
    t0 = time.time()

    converged = False
    result = None
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            model = smf.mixedlm(
                FORMULA_M3,
                data=df,
                groups=df["UF_str"],
                re_formula="~negro",
            )
            result = model.fit(method="powell", maxiter=1000, reml=reml)
            singular = any("singular" in str(x.message).lower() for x in w)
            converged = result.converged if hasattr(result, "converged") else True
        except Exception as e:
            logger.error(f"[{label}] ERRO: {e}")
            return None, None

    elapsed = time.time() - t0

    # Extrai componentes de variância
    cov_re = result.cov_re
    tau2_int   = float(cov_re.iloc[0, 0]) if cov_re.shape[0] > 0 else 0.0
    tau2_negro = float(cov_re.iloc[1, 1]) if cov_re.shape[0] > 1 else 0.0
    cov_int_neg= float(cov_re.iloc[0, 1]) if cov_re.shape[0] > 1 else 0.0
    sigma2     = float(result.scale)

    # Correlação intercept × slope
    denom = np.sqrt(tau2_int * tau2_negro) if tau2_int > 0 and tau2_negro > 0 else 0.0
    rho   = cov_int_neg / denom if denom > 0 else 0.0

    b_negro = result.params.get("negro", np.nan)

    # ICC do gap racial: quanto da variância do efeito negro é entre UFs?
    icc_negro = tau2_negro / (tau2_negro + sigma2) if (tau2_negro + sigma2) > 0 else 0.0

    status = "SINGULAR" if singular else ("NÃO CONVERGIU" if not converged else "OK")
    logger.info(
        f"[{label}] {status} em {elapsed:.0f}s\n"
        f"  b_negro (fixo) = {b_negro:.4f}\n"
        f"  tau2_intercepto = {tau2_int:.6f}\n"
        f"  tau2_negro      = {tau2_negro:.6f}  ← variância do gap racial entre UFs\n"
        f"  cov(u0,u1)      = {cov_int_neg:.6f}\n"
        f"  rho(u0,u1)      = {rho:.4f}\n"
        f"  sigma2          = {sigma2:.4f}\n"
        f"  ICC_negro       = {icc_negro:.4f}"
    )

    # Interpreta rho para o usuário
    if abs(rho) > 0.3:
        sinal = "positiva" if rho > 0 else "negativa"
        logger.info(
            f"  → Correlação {sinal} ({rho:.3f}): em UFs onde o gap médio é "
            + ("maior, o gap racial também é maior." if rho > 0
               else "maior, o gap racial é menor (efeito compensatório).")
        )

    varcov = {
        "modelo": label,
        "b_negro_fixo": round(b_negro, 4),
        "tau2_intercepto": round(tau2_int, 6),
        "tau2_negro_slope": round(tau2_negro, 6),
        "cov_int_negro": round(cov_int_neg, 6),
        "rho_int_negro": round(rho, 4),
        "sigma2": round(sigma2, 4),
        "icc_negro": round(icc_negro, 4),
        "status": status,
        "n_obs": len(df),
        "n_ufs": df["UF_str"].nunique(),
        "sample_frac": SAMPLE_FRAC if SAMPLE_FRAC else 1.0,
    }
    return result, varcov


# ── LRT: M3_base vs M3_rs (boundary test tau2_negro=0) ───────────────────────

def lrt_boundary(res_base, res_rs, label_r="M3_base_ML", label_f="M3_rs_ML"):
    """
    H0: tau2_negro = 0 (na fronteira do espaço paramétrico).
    Distribuição do LRT: mistura 50% chi2(1) + 50% chi2(2) — Stram & Lee (1994).
    """
    if res_rs is None:
        return {"erro": "modelo rs não convergiu"}

    lr = 2 * max(res_rs.llf - res_base.llf, 0)

    # Mistura: P(LR > c) = 0.5*P(chi2(1) > c) + 0.5*P(chi2(2) > c)
    p_mix = 0.5 * stats.chi2.sf(lr, df=1) + 0.5 * stats.chi2.sf(lr, df=2)

    sig = "***" if p_mix < 0.001 else ("**" if p_mix < 0.01 else ("*" if p_mix < 0.05 else "ns"))
    logger.info(
        f"\n{'='*60}\n"
        f"LRT: {label_r} vs {label_f}\n"
        f"  LR = {lr:.3f}  |  p (boundary mix) = {p_mix:.6f}  {sig}\n"
        f"  Interpretação: tau2_negro {'É' if p_mix < 0.05 else 'NÃO é'} "
        f"significativamente diferente de zero.\n"
        + ("  → RECOMENDAÇÃO: incluir random slope no modelo final.\n"
           "  → Adiciona dimensão geográfica à discriminação racial."
           if p_mix < 0.05 else
           "  → random slope não justificado; M3 com intercepto aleatório é suficiente.")
        + f"\n{'='*60}"
    )
    return {
        "comparacao": f"{label_r} → {label_f}",
        "LR": round(lr, 3),
        "p_boundary_mix": round(p_mix, 6),
        "sig": sig,
        "tau2_negro_significativo": p_mix < 0.05,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    t_total = time.time()
    logger.info("=" * 60)
    logger.info("HLM M3 com Random Slope para Negro")
    logger.info(f"SAMPLE_FRAC = {SAMPLE_FRAC} | RANDOM_STATE = {RANDOM_STATE}")
    logger.info("=" * 60)

    df = load_data()

    # 1. M3 base com REML (para ICC e referência)
    res_base_reml, tau2_uf, sigma2, icc_uf = fit_base(df, reml=True)
    logger.info(f"\nM3 BASE (REML): ICC_UF={icc_uf:.4f} | tau2_UF={tau2_uf:.5f}")

    # 2. M3 base com ML (necessário para LRT válido)
    res_base_ml, *_ = fit_base(df, reml=False)

    # 3. M3 + random slope (não-correlacionado, ML para LRT)
    logger.info("\n--- Especificação NÃO-CORRELACIONADA (ML) ---")
    res_rs_ml, vc_rs = fit_random_slope(df, correlated=False, reml=False)

    # 4. LRT
    lrt_result = lrt_boundary(res_base_ml, res_rs_ml,
                               "M3_base_ML", "M3_rs_uncorr_ML")

    # 5. Se τ²₁ > 0 com p<0.05, tenta especificação REML para publicação
    vc_rs_reml = None
    if lrt_result.get("tau2_negro_significativo", False):
        logger.info("\n--- Especificação NÃO-CORRELACIONADA (REML) — para publicação ---")
        res_rs_reml, vc_rs_reml = fit_random_slope(df, correlated=False, reml=True)

    # ── Salva resultados ────────────────────────────────────────────────────────
    rows_vc = []
    rows_vc.append({
        "modelo": "M3_base_REML",
        "b_negro_fixo": round(res_base_reml.params.get("negro", np.nan), 4),
        "tau2_intercepto": round(tau2_uf, 6),
        "tau2_negro_slope": 0.0,
        "cov_int_negro": 0.0,
        "rho_int_negro": 0.0,
        "sigma2": round(sigma2, 4),
        "icc_negro": 0.0,
        "status": "OK",
        "n_obs": len(df),
        "n_ufs": df["UF_str"].nunique(),
        "sample_frac": SAMPLE_FRAC if SAMPLE_FRAC else 1.0,
    })
    if vc_rs:
        rows_vc.append(vc_rs)
    if vc_rs_reml:
        rows_vc.append(vc_rs_reml)

    df_vc = pd.DataFrame(rows_vc)
    df_vc.to_csv(OUTPUTS / "hlm_m3_random_slope_varcov.csv", index=False)
    logger.info(f"\nSalvo: {OUTPUTS / 'hlm_m3_random_slope_varcov.csv'}")

    # Coeficientes fixos do modelo final
    model_final = res_rs_reml if vc_rs_reml else (res_rs_ml if res_rs_ml else res_base_reml)
    coefs = model_final.params.reset_index()
    coefs.columns = ["variavel", "coeficiente"]
    coefs["se"] = model_final.bse.values
    coefs["z"]  = coefs["coeficiente"] / coefs["se"]
    coefs["p"]  = 2 * (1 - stats.norm.cdf(abs(coefs["z"])))
    coefs.to_csv(OUTPUTS / "hlm_m3_random_slope_coefs.csv", index=False)
    logger.info(f"Salvo: {OUTPUTS / 'hlm_m3_random_slope_coefs.csv'}")

    # LRT
    df_lrt = pd.DataFrame([lrt_result])
    df_lrt.to_csv(OUTPUTS / "hlm_m3_random_slope_lrt.csv", index=False)
    logger.info(f"Salvo: {OUTPUTS / 'hlm_m3_random_slope_lrt.csv'}")

    elapsed_total = time.time() - t_total
    logger.info(f"\nConcluído em {elapsed_total/60:.1f} min.")

    # ── Resumo final ────────────────────────────────────────────────────────────
    if vc_rs:
        t2 = vc_rs["tau2_negro_slope"]
        sig_status = "SIGNIFICATIVO" if lrt_result.get("tau2_negro_significativo") else "NÃO significativo"
        logger.info(
            f"\n{'='*60}\n"
            f"RESUMO FINAL\n"
            f"  b_negro (efeito fixo)    = {vc_rs['b_negro_fixo']}\n"
            f"  tau2_negro (entre UFs)   = {t2:.6f}  [{sig_status}]\n"
            f"  SD_negro  (entre UFs)    = {np.sqrt(t2):.4f}\n"
            f"  p_LRT (boundary mix)     = {lrt_result.get('p_boundary_mix', 'N/A')}\n"
            f"  rho(intercept, slope)    = {vc_rs['rho_int_negro']}\n"
            f"\n  Interpretação: o gap racial varia entre UFs com DP = "
            f"{np.sqrt(t2):.3f} log-pontos.\n"
            f"  Em 95% das UFs, o gap está no intervalo aprox. "
            f"[{vc_rs['b_negro_fixo'] - 1.96*np.sqrt(t2):.3f}, "
            f"{vc_rs['b_negro_fixo'] + 1.96*np.sqrt(t2):.3f}].\n"
            f"{'='*60}"
        )


if __name__ == "__main__":
    main()
