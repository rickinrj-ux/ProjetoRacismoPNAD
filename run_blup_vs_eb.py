"""
run_blup_vs_eb.py
=================
Comparação metodológica: OLS Fixo + Shrinkage Empirical Bayes  ×  BLUP do MixedLM
completo (random intercept + random slope de `negro` por UF), na POPULAÇÃO INTEIRA.

PERGUNTA
--------
A aproximação rápida (OLS por UF + shrinkage EB com τ² conhecido) reproduz os
BLUPs do modelo misto estimado conjuntamente? Em caso afirmativo, o atalho é
válido para a focalização da PO; caso contrário, o MixedLM é indispensável.

DESENHO (isola o efeito do *pooling*, não o da especificação)
-------------------------------------------------------------
Ambos os métodos usam a MESMA especificação M3 ao nível-1:
    individual (negro, sexo, idade, idade², 4 dummies de educação, log_horas,
    urbano) + contextuais de UPA (pct_negro, desemprego, educ média) + dummies
    de ano. As variáveis de UF são CONSTANTES dentro da UF (colineares com o
    intercepto por UF) e por isso são absorvidas em ambos os métodos.

  (A) MixedLM full  : log_renda ~ X + (1 + negro | UF)   → BLUP_j = β̂_negro + û₁ⱼ
  (B) OLS + EB      : 27 OLS por UF → β_j, SE_j; depois
                      λ_j = τ²/(τ²+SE_j²);  gap_j^EB = β̄ + λ_j(β_j − β̄)
                      onde τ² é o τ²_negro estimado em (A).

REPERCUSSÃO NA PO
-----------------
Re-executa a alocação regional (focalizada × uniforme) sob os gaps de (A) e (B)
e verifica se o veredito de valor da focalização territorial se mantém.

SAÍDA
-----
  outputs/tables/blup_per_uf.csv            — BLUPs (u0, u1) e gap por UF
  outputs/tables/blup_vs_eb_comparacao.csv  — correlações, diffs, concordância
  outputs/tables/po_regional_blup_alocacao.csv
  outputs/figures/blup_vs_eb.png            — scatter + curvas de ganho da PO
  logs/blup_vs_eb.log

Referência: Raudenbush & Bryk (2002), cap. 3 (EB) e 4 (random slope);
            Robinson (1991) "That BLUP is a good thing".
"""

import sys
import time
import logging
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from scipy.optimize import linprog

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

ROOT    = Path(__file__).parent
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/blup_vs_eb.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

FEATURES = ROOT / "data" / "processed" / "features.parquet"

UF_MAP = {
    11: ("RO", "Norte"),     12: ("AC", "Norte"),     13: ("AM", "Norte"),
    14: ("RR", "Norte"),     15: ("PA", "Norte"),     16: ("AP", "Norte"),
    17: ("TO", "Norte"),     21: ("MA", "Nordeste"),  22: ("PI", "Nordeste"),
    23: ("CE", "Nordeste"),  24: ("RN", "Nordeste"),  25: ("PB", "Nordeste"),
    26: ("PE", "Nordeste"),  27: ("AL", "Nordeste"),  28: ("SE", "Nordeste"),
    29: ("BA", "Nordeste"),  31: ("MG", "Sudeste"),   32: ("ES", "Sudeste"),
    33: ("RJ", "Sudeste"),   35: ("SP", "Sudeste"),   41: ("PR", "Sul"),
    42: ("SC", "Sul"),       43: ("RS", "Sul"),       50: ("MS", "Centro-Oeste"),
    51: ("MT", "Centro-Oeste"), 52: ("GO", "Centro-Oeste"), 53: ("DF", "Centro-Oeste"),
}

# Nível-1: individual + contextuais de UPA (variam dentro da UF). As variáveis de
# UF são constantes dentro da UF → omitidas (absorvidas pelo intercepto por UF).
IND_VARS = [
    "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "log_horas", "urbano",
]
UPA_CTX = ["pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z"]
LEVEL1  = IND_VARS + UPA_CTX

# Fórmula do MixedLM: inclui também contextuais de UF (a parte fixa pode usá-las;
# o random slope é só para negro). Idêntica em espírito a run_hlm_m3_random_slope.
_FE = (" + ".join(LEVEL1)
       + " + educ_missing + pct_negro_uf_z + tx_desemprego_uf_z + media_educ_uf_z + C(Ano)")
FORMULA_M3 = f"log_renda ~ {_FE}"


# ── 1. Dados ─────────────────────────────────────────────────────────────────

def load_data():
    log.info(f"Carregando {FEATURES} ...")
    cols = (["log_renda", "UF", "UPA", "Ano", "educ_cat"] + IND_VARS + UPA_CTX
            + ["pct_negro_uf_z", "tx_desemprego_uf_z", "media_educ_uf_z"])
    df = pd.read_parquet(FEATURES, columns=list(dict.fromkeys(cols)))
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df["educ_missing"] = df["educ_cat"].isna().astype("int8")
    df = df.dropna(subset=["log_renda", "UF", "Ano"] + LEVEL1
                   + ["pct_negro_uf_z", "tx_desemprego_uf_z", "media_educ_uf_z"])
    upa_counts = df["UPA"].value_counts()
    df = df[df["UPA"].isin(upa_counts[upa_counts >= 10].index)]
    df["UF_int"] = df["UF"].astype(int)
    df["UF_str"] = df["UF"].astype(str)
    df["log_renda"] = df["log_renda"].astype(float)
    log.info(f"  N efetivo: {len(df):,} | UFs: {df['UF_int'].nunique()}")
    return df


# ── 2. (A) MixedLM full → BLUPs ──────────────────────────────────────────────

def fit_mixedlm_blup(df):
    log.info("══ (A) MixedLM full (random intercept + random slope de negro) ══")
    log.info("  Ajustando... (pop. completa; ~5 min)")
    t0 = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = smf.mixedlm(FORMULA_M3, data=df, groups=df["UF_str"],
                            re_formula="~negro")
        res = model.fit(method="powell", maxiter=1000, reml=True)
    log.info(f"  MixedLM ajustado em {(time.time()-t0)/60:.1f} min.")

    b_negro = float(res.params["negro"])
    cov_re  = res.cov_re
    tau2_int   = float(cov_re.iloc[0, 0])
    tau2_negro = float(cov_re.iloc[1, 1])
    cov01      = float(cov_re.iloc[0, 1])
    rho = cov01 / np.sqrt(tau2_int * tau2_negro) if tau2_int > 0 and tau2_negro > 0 else 0.0
    log.info(f"  β_negro(fixo)={b_negro:+.4f} | τ²_negro={tau2_negro:.6f} "
             f"| τ²_int={tau2_int:.6f} | ρ={rho:+.4f}")

    # Extrai BLUPs por UF: random_effects[uf] tem ['Intercept'(ou Group), 'negro']
    rows = []
    for uf_str, re in res.random_effects.items():
        slope_name = "negro" if "negro" in re.index else re.index[-1]
        u1 = float(re[slope_name])
        u0 = float(re.drop(index=slope_name).iloc[0])
        uf_int = int(uf_str)
        sigla, regiao = UF_MAP.get(uf_int, (uf_str, "?"))
        rows.append({
            "UF": uf_int, "sigla": sigla, "regiao": regiao,
            "u0_intercepto": round(u0, 5), "u1_slope": round(u1, 6),
            "gap_blup": round(b_negro + u1, 4),
        })
    df_blup = pd.DataFrame(rows)
    df_blup["gap_blup_pct"] = np.round((np.exp(df_blup["gap_blup"]) - 1) * 100, 2)
    return df_blup, {"b_negro": b_negro, "tau2_negro": tau2_negro,
                     "tau2_int": tau2_int, "rho": rho}


# ── 3. (B) OLS por UF (mesma especificação) + Shrinkage EB ───────────────────

def ols_eb_por_uf(df, tau2_negro):
    log.info("══ (B) OLS por UF (mesma especificação M3) + Shrinkage EB ══")
    anos = sorted(df["Ano"].unique())
    idx_negro = 1  # const=0; negro é a 1ª de LEVEL1
    rows = []
    for uf_int, g in df.groupby("UF_int", observed=True):
        n = len(g)
        X_l1 = g[LEVEL1].to_numpy(dtype=float)
        yr = pd.get_dummies(g["Ano"], drop_first=True).reindex(
            columns=anos[1:], fill_value=0).to_numpy(dtype=float)
        X = np.column_stack([np.ones(n), X_l1, yr])
        y = g["log_renda"].to_numpy(dtype=float)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        sigma2 = float(resid @ resid) / (n - X.shape[1])
        se = float(np.sqrt(sigma2 * np.linalg.inv(X.T @ X)[idx_negro, idx_negro]))
        sigla, regiao = UF_MAP.get(uf_int, (str(uf_int), "?"))
        rows.append({"UF": uf_int, "sigla": sigla, "regiao": regiao,
                     "beta_ols": float(beta[idx_negro]), "se": se,
                     "n": n, "n_negro": int(g["negro"].sum())})
    d = pd.DataFrame(rows)

    se2 = d["se"].to_numpy() ** 2
    b   = d["beta_ols"].to_numpy()
    w   = 1.0 / (tau2_negro + se2)
    beta_bar = float(np.sum(w * b) / np.sum(w))
    lam = tau2_negro / (tau2_negro + se2)
    d["beta_bar"]  = round(beta_bar, 4)
    d["shrinkage"] = np.round(lam, 4)
    d["gap_eb"]    = np.round(beta_bar + lam * (b - beta_bar), 4)
    d["gap_eb_pct"]= np.round((np.exp(d["gap_eb"]) - 1) * 100, 2)
    log.info(f"  β̄(precision-weighted)={beta_bar:+.4f} | shrinkage médio={lam.mean():.4f}")
    return d


# ── 4. Comparação A × B ──────────────────────────────────────────────────────

def comparar(df_blup, df_eb):
    m = df_blup.merge(df_eb[["UF", "beta_ols", "se", "n", "n_negro",
                             "shrinkage", "gap_eb", "gap_eb_pct"]], on="UF")
    r_pearson = float(np.corrcoef(m["gap_eb"], m["gap_blup"])[0, 1])
    rho_spear = float(stats.spearmanr(m["gap_eb"], m["gap_blup"]).correlation)
    # Concordância nos desvios em torno da média (objeto relevante p/ focalização)
    dev_eb   = m["gap_eb"]   - m["gap_eb"].mean()
    dev_blup = m["gap_blup"] - m["gap_blup"].mean()
    r_dev = float(np.corrcoef(dev_eb, dev_blup)[0, 1])
    mad   = float(np.mean(np.abs(m["gap_eb"] - m["gap_blup"])))
    diff_nivel = float(m["gap_eb"].mean() - m["gap_blup"].mean())

    top_eb   = set(m.nsmallest(5, "gap_eb")["sigla"])
    top_blup = set(m.nsmallest(5, "gap_blup")["sigla"])
    overlap5 = len(top_eb & top_blup)

    log.info("══ Comparação OLS+EB × BLUP MixedLM ══")
    log.info(f"  Pearson r(gap_eb, gap_blup)   = {r_pearson:+.3f}")
    log.info(f"  Spearman ρ (ranking)          = {rho_spear:+.3f}")
    log.info(f"  Pearson dos DESVIOS (padrão)  = {r_dev:+.3f}")
    log.info(f"  MAD |gap_eb − gap_blup|       = {mad:.4f} log-pontos")
    log.info(f"  Diferença de NÍVEL (EB−BLUP)  = {diff_nivel:+.4f} (efeito especificação)")
    log.info(f"  Overlap top-5 piores UFs      = {overlap5}/5")

    comp = pd.DataFrame([{
        "pearson_r": round(r_pearson, 4), "spearman_rho": round(rho_spear, 4),
        "pearson_desvios": round(r_dev, 4), "mad_logpts": round(mad, 4),
        "diff_nivel_eb_menos_blup": round(diff_nivel, 4),
        "overlap_top5_piores": overlap5,
    }])
    return m, comp


# ── 5. PO regional sob A e B ─────────────────────────────────────────────────

def po_regional(gap, n_negro, alpha=0.30, label=""):
    """Ganho da focalização sobre o uniforme, por orçamento (nº UFs financiáveis)."""
    s = np.abs(gap)
    w = n_negro / n_negro.sum()
    impacto = alpha * s * w
    J = len(gap)
    out = []
    for B in [3, 6, 9, 12, 15, 18, 27]:
        cap = min(B, J)
        res = linprog(-impacto, A_ub=[np.ones(J)], b_ub=[cap],
                      bounds=[(0, 1)] * J, method="highs")
        red_focal = float(impacto @ res.x)
        red_unif  = float(impacto @ np.full(J, cap / J))
        ganho = (red_focal / red_unif - 1) * 100 if red_unif > 0 else 0.0
        out.append({"metodo": label, "orcamento_ufs": B,
                    "reducao_focalizada": round(red_focal, 5),
                    "reducao_uniforme": round(red_unif, 5),
                    "ganho_focalizacao_pct": round(ganho, 1)})
    return pd.DataFrame(out)


# ── 6. Figura ────────────────────────────────────────────────────────────────

def figura(m, aloc_eb, aloc_blup):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))

    # (a) Scatter gap_eb × gap_blup
    ax = axes[0]
    cores = {"Norte": "#4DAC26", "Nordeste": "#D01C8B", "Sudeste": "#2166AC",
             "Sul": "#7B3294", "Centro-Oeste": "#E66101"}
    ax.scatter(m["gap_blup"], m["gap_eb"],
               c=m["regiao"].map(cores), s=55, zorder=3)
    for _, r in m.iterrows():
        ax.annotate(r["sigla"], (r["gap_blup"], r["gap_eb"]),
                    fontsize=7, xytext=(3, 3), textcoords="offset points")
    lo = min(m["gap_blup"].min(), m["gap_eb"].min()) - 0.01
    hi = max(m["gap_blup"].max(), m["gap_eb"].max()) + 0.01
    ax.plot([lo, hi], [lo, hi], "k--", lw=1, alpha=0.6, label="identidade (45°)")
    # reta de regressão
    b1, b0 = np.polyfit(m["gap_blup"], m["gap_eb"], 1)
    xs = np.array([lo, hi])
    ax.plot(xs, b0 + b1 * xs, color="red", lw=1.2, alpha=0.7,
            label=f"ajuste: incl.={b1:.2f}")
    ax.set_xlabel("Gap por UF — BLUP MixedLM (log-renda)", fontsize=10)
    ax.set_ylabel("Gap por UF — OLS + EB (log-renda)", fontsize=10)
    ax.set_title("Concordância dos métodos por UF", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # (b) Curvas de ganho da focalização
    ax2 = axes[1]
    ax2.plot(aloc_eb["orcamento_ufs"], aloc_eb["ganho_focalizacao_pct"],
             "o-", color="#2166AC", lw=2, label="OLS + EB")
    ax2.plot(aloc_blup["orcamento_ufs"], aloc_blup["ganho_focalizacao_pct"],
             "s--", color="#D01C8B", lw=2, label="BLUP MixedLM")
    ax2.axhline(0, color="gray", lw=1)
    ax2.set_xlabel("Orçamento (nº de UFs financiáveis)", fontsize=10)
    ax2.set_ylabel("Ganho da focalização sobre uniforme (%)", fontsize=10)
    ax2.set_title("Repercussão na PO: veredito sob os dois métodos",
                  fontsize=11, fontweight="bold")
    ax2.legend(fontsize=9); ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUT_FIG / "blup_vs_eb.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  blup_vs_eb.png salvo.")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    log.info("=" * 64)
    log.info("BLUP MixedLM  ×  OLS Fixo + Shrinkage EB  (população completa)")
    log.info("=" * 64)

    df = load_data()
    df_blup, mix = fit_mixedlm_blup(df)
    df_eb = ols_eb_por_uf(df, mix["tau2_negro"])

    m, comp = comparar(df_blup, df_eb)
    m.to_csv(OUT_TAB / "blup_per_uf.csv", index=False)
    comp.to_csv(OUT_TAB / "blup_vs_eb_comparacao.csv", index=False)

    aloc_eb   = po_regional(m["gap_eb"].to_numpy(),   m["n_negro"].to_numpy(), label="OLS+EB")
    aloc_blup = po_regional(m["gap_blup"].to_numpy(), m["n_negro"].to_numpy(), label="BLUP")
    pd.concat([aloc_eb, aloc_blup]).to_csv(
        OUT_TAB / "po_regional_blup_alocacao.csv", index=False)

    figura(m, aloc_eb, aloc_blup)

    # ── Veredito ──────────────────────────────────────────────────────────────
    g9_eb   = aloc_eb.loc[aloc_eb["orcamento_ufs"] == 9, "ganho_focalizacao_pct"].values[0]
    g9_blup = aloc_blup.loc[aloc_blup["orcamento_ufs"] == 9, "ganho_focalizacao_pct"].values[0]
    log.info("\n" + "=" * 64)
    log.info("VEREDITO")
    log.info(f"  Ranking idêntico? Spearman ρ = {comp['spearman_rho'].iloc[0]:+.3f}")
    log.info(f"  Padrão de heterogeneidade   r_desvios = {comp['pearson_desvios'].iloc[0]:+.3f}")
    log.info(f"  Ganho focalização B=9:  OLS+EB={g9_eb:+.1f}%  |  BLUP={g9_blup:+.1f}%")
    log.info(f"  Tempo total: {(time.time()-t0)/60:.1f} min.")
    log.info("=" * 64)


if __name__ == "__main__":
    main()
