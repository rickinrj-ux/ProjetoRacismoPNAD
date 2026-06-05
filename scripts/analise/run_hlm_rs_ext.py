"""
run_hlm_rs_ext.py
=================
Extensões do random slope no HLM de salário (statsmodels MixedLM, REAL — não proxy):

PARTE A — Random slope de `negro` por UF, estimado SEPARADAMENTE por setor
          (público vs privado). Completa a simetria com o GLMM de acesso:
          o setor público atenua/homogeneíza a heterogeneidade geográfica do
          gap SALARIAL racial, como (não) faz no acesso?

PARTE B — Random slope conjunto de `negro` E `sexo_fem` por UF (nível adicional):
          (1 + negro + sexo_fem | UF). Testa se o gap de GÊNERO também varia
          geograficamente (LRT vs. modelo só com slope de negro) e estima a
          correlação entre as heterogeneidades racial e de gênero entre UFs.

Especificação M3 idêntica a run_hlm_m3_random_slope.py / run_blup_vs_eb.py.
REML; otimizador powell. Desfecho contínuo (log_renda) → MixedLM é o modelo misto
REAL (não exige R/lme4).

SAÍDA:
  outputs/tables/hlm_rs_setor.csv    — β/τ²/ρ de negro por setor (privado, público)
  outputs/tables/hlm_rs_genero.csv   — variâncias negro+sexo_fem + LRT
  outputs/figures/hlm_rs_ext.png     — comparação setorial + gênero
  logs/hlm_rs_ext.log
"""

# --- bootstrap raiz do projeto (reorg estrutura) ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys, logging, time, warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

ROOT    = Path.cwd()
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.FileHandler("logs/hlm_rs_ext.log", encoding="utf-8"),
              logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

FEATURES = ROOT / "data" / "processed" / "features.parquet"

_IND = ("negro + sexo_fem + idade_c + idade_sq + educ_fund_completo + educ_medio_completo"
        " + educ_superior_completo + educ_pos_graduacao + educ_missing + log_horas + urbano + C(Ano)")
_UPA = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
_UF  = "pct_negro_uf_z + tx_desemprego_uf_z + media_educ_uf_z"
FORMULA_M3 = f"log_renda ~ {_IND} + {_UPA} + {_UF}"
MODEL_VARS = ["log_renda","negro","sexo_fem","idade_c","idade_sq","educ_fund_completo",
    "educ_medio_completo","educ_superior_completo","educ_pos_graduacao","educ_missing","log_horas",
    "urbano","Ano","pct_negro_upa_z","tx_desemprego_upa_z","media_educ_upa_z",
    "pct_negro_uf_z","tx_desemprego_uf_z","media_educ_uf_z","UPA","UF","setor_publico"]


def load():
    log.info("Carregando dados ...")
    df = pd.read_parquet(FEATURES)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df["educ_missing"] = df["educ_cat"].isna().astype("int8") if "educ_cat" in df.columns else 0
    if "log_horas" not in df.columns and "horas_trabalhadas" in df.columns:
        df["log_horas"] = np.log(df["horas_trabalhadas"].clip(lower=1))
    if "urbano" not in df.columns:
        df["urbano"] = (df["V1022"] == 1).astype("int8") if "V1022" in df.columns else 1
    if "setor_publico" in df.columns:
        df["setor_publico"] = df["setor_publico"].fillna(0).astype(int)
    df = df.dropna(subset=[c for c in MODEL_VARS if c != "setor_publico"]).reset_index(drop=True)
    upa = df["UPA"].value_counts()
    df = df[df["UPA"].isin(upa[upa >= 10].index)].reset_index(drop=True)
    df["UF_str"] = df["UF"].astype(str)
    df["log_renda"] = df["log_renda"].astype(float)
    log.info(f"  N efetivo: {len(df):,} | UFs: {df['UF_str'].nunique()}")
    return df


def fit_rs(df, re_formula, label, reml=True):
    t0 = time.time()
    m = smf.mixedlm(FORMULA_M3, data=df, groups=df["UF_str"], re_formula=re_formula)
    r = m.fit(method="powell", maxiter=1000, reml=reml)
    log.info(f"  [{label}] ok {(time.time()-t0)/60:.1f} min | llf={r.llf:.1f}")
    return r


def varcomp_negro(r):
    vc = r.cov_re
    tau2_int = float(vc.iloc[0, 0]); tau2_neg = float(vc.iloc[1, 1]); cov = float(vc.iloc[0, 1])
    rho = cov/np.sqrt(tau2_int*tau2_neg) if tau2_int > 0 and tau2_neg > 0 else 0.0
    return tau2_int, tau2_neg, rho, float(r.params.get("negro", np.nan))


def main():
    t0 = time.time()
    log.info("="*64); log.info("HLM random slope — setor (A) + gênero (B)"); log.info("="*64)
    df = load()

    # ── PARTE A: random slope de negro por setor ──────────────────────────────
    log.info("\n══ PARTE A — random slope de negro por UF, por setor ══")
    rows_a = []
    for nome, sub in [("Privado", df[df["setor_publico"] == 0]),
                      ("Público", df[df["setor_publico"] == 1])]:
        r = fit_rs(sub, "~negro", f"setor={nome}")
        ti, tn, rho, b = varcomp_negro(r)
        sd = np.sqrt(max(tn, 0))
        rows_a.append({"setor": nome, "b_negro": round(b, 4), "OR_equiv_pct": round((np.exp(b)-1)*100, 1),
                       "tau2_negro": round(tn, 6), "sd_negro": round(sd, 4), "rho_int_negro": round(rho, 4),
                       "sigma2": round(float(r.scale), 4), "n_obs": len(sub), "n_uf": sub["UF_str"].nunique()})
        log.info(f"    {nome}: b_negro={b:+.4f} ({(np.exp(b)-1)*100:+.1f}%) | "
                 f"tau2_negro={tn:.5f} (SD={sd:.4f}) | rho={rho:+.3f}")
    pd.DataFrame(rows_a).to_csv(OUT_TAB / "hlm_rs_setor.csv", index=False)
    log.info("  hlm_rs_setor.csv salvo.")

    # ── PARTE B: random slope conjunto negro + sexo_fem (nível adicional) ──────
    log.info("\n══ PARTE B — random slope conjunto (negro + sexo_fem) por UF ══")
    r_base = fit_rs(df, "~negro", "base: (1+negro|UF)")
    r_gen  = fit_rs(df, "~negro + sexo_fem", "gênero: (1+negro+sexo_fem|UF)")

    lr = 2 * max(r_gen.llf - r_base.llf, 0)
    # adicionar slope de sexo_fem: +var(sexo) +2 cov => mistura boundary 0.5*chi2(2)+0.5*chi2(3)
    p_mix = 0.5 * stats.chi2.sf(lr, 2) + 0.5 * stats.chi2.sf(lr, 3)

    vc = r_gen.cov_re
    # ordem das REs: Intercept, negro, sexo_fem
    tau2_int = float(vc.iloc[0, 0]); tau2_neg = float(vc.iloc[1, 1]); tau2_sex = float(vc.iloc[2, 2])
    rho_ns = float(vc.iloc[1, 2]) / np.sqrt(tau2_neg*tau2_sex) if tau2_neg > 0 and tau2_sex > 0 else 0.0
    b_neg = float(r_gen.params.get("negro", np.nan)); b_sex = float(r_gen.params.get("sexo_fem", np.nan))
    sig = "***" if p_mix < 0.001 else ("**" if p_mix < 0.01 else ("*" if p_mix < 0.05 else "ns"))
    log.info(f"    b_negro={b_neg:+.4f} | b_sexo_fem={b_sex:+.4f}")
    log.info(f"    tau2_negro={tau2_neg:.5f} (SD={np.sqrt(max(tau2_neg,0)):.4f}) | "
             f"tau2_sexo={tau2_sex:.5f} (SD={np.sqrt(max(tau2_sex,0)):.4f})")
    log.info(f"    rho(slope_negro, slope_sexo)={rho_ns:+.3f} | LRT(+slope sexo) LR={lr:.1f} p={p_mix:.3g} {sig}")

    pd.DataFrame([{
        "b_negro": round(b_neg, 4), "b_sexo_fem": round(b_sex, 4),
        "tau2_intercepto": round(tau2_int, 6),
        "tau2_negro": round(tau2_neg, 6), "sd_negro": round(np.sqrt(max(tau2_neg, 0)), 4),
        "tau2_sexo": round(tau2_sex, 6), "sd_sexo": round(np.sqrt(max(tau2_sex, 0)), 4),
        "rho_negro_sexo": round(rho_ns, 4), "LR_add_sexo": round(lr, 1),
        "p_boundary": p_mix, "sig": sig, "n_obs": len(df), "n_uf": df["UF_str"].nunique(),
    }]).to_csv(OUT_TAB / "hlm_rs_genero.csv", index=False)
    log.info("  hlm_rs_genero.csv salvo.")

    figura(rows_a, tau2_neg, tau2_sex)
    log.info(f"\nConcluído em {(time.time()-t0)/60:.1f} min.")
    log.info("="*64)


def figura(rows_a, tau2_neg_gen, tau2_sex_gen):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    # (a) setor: SD do gap salarial racial entre UFs
    ax = axes[0]
    setores = [r["setor"] for r in rows_a]; sds = [r["sd_negro"] for r in rows_a]
    ors = [abs(r["OR_equiv_pct"]) for r in rows_a]
    x = np.arange(len(setores))
    ax.bar(x-0.2, ors, 0.4, label="|gap salarial| médio (%)", color="#C62828")
    ax.bar(x+0.2, [s*100 for s in sds], 0.4, label="DP entre UFs (×100 log)", color="#E66101")
    ax.set_xticks(x); ax.set_xticklabels(setores)
    ax.set_title("HLM salário: gap racial e sua heterogeneidade por setor", fontsize=11, fontweight="bold")
    ax.legend(fontsize=9); ax.grid(alpha=0.3, axis="y")
    # (b) gênero vs raça: DP entre UFs (heterogeneidade geográfica)
    ax2 = axes[1]
    ax2.bar(["Raça (negro)","Gênero (mulher)"], [np.sqrt(max(tau2_neg_gen,0)), np.sqrt(max(tau2_sex_gen,0))],
            color=["#2166AC","#7B3294"])
    ax2.set_ylabel("DP do slope entre UFs (log-renda)")
    ax2.set_title("Heterogeneidade geográfica: raça vs gênero\n(random slope conjunto)", fontsize=11, fontweight="bold")
    ax2.grid(alpha=0.3, axis="y")
    plt.tight_layout(); plt.savefig(OUT_FIG / "hlm_rs_ext.png", dpi=150, bbox_inches="tight"); plt.close()
    log.info("  hlm_rs_ext.png salvo.")


if __name__ == "__main__":
    main()
