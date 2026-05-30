"""
run_segregacao_ci.py
=====================
Adiciona intervalos de confiança (bootstrap) ao gap racial por tipo de área.
Complementa run_segregacao_espacial.py com inferência estatística formal.

METODOLOGIA:
    Bootstrap não-paramétrico (1000 replicações) para calcular IC 95%
    do gap salarial racial (log-renda) por tipo de área:
    Capital, RM (exceto capital), Interior.

    Também realiza teste de diferença entre áreas (permutação).
"""
import sys
import logging
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/segregacao_ci.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

FEATURES_PATH = Path("data/processed/features.parquet")
OUTPUTS_TB    = Path("outputs/tables")
OUTPUTS_FIG   = Path("outputs/figures")
OUTPUTS_TB.mkdir(parents=True, exist_ok=True)
OUTPUTS_FIG.mkdir(parents=True, exist_ok=True)

N_BOOT         = 1000
SUBSAMPLE_FRAC = 0.10   # 10% para velocidade (N~760k)
SEED           = 42
AREA_ORDER     = ["Capital", "RM (exceto\ncapital)", "Interior"]
AREA_LABELS    = {"Capital": "Capital", "RM (exceto\ncapital)": "RM", "Interior": "Interior"}


def load_data():
    logger.info("Carregando dados ...")
    cols = ["negro", "log_renda", "renda_bruta", "pea", "V1023",
            "educ_fund_completo", "educ_medio_completo",
            "educ_superior_completo", "educ_pos_graduacao",
            "sexo_fem", "log_horas", "urbano"]
    df = pd.read_parquet(FEATURES_PATH, columns=cols)
    df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0)].dropna(
        subset=["negro", "log_renda", "V1023"]
    ).copy()

    area_map = {1: "Capital", 2: "RM (exceto\ncapital)", 3: "Interior", 4: "Interior"}
    df["area_tipo"] = df["V1023"].map(area_map)
    df = df.dropna(subset=["area_tipo"])

    # Subsample para velocidade do bootstrap
    df_sample = df.sample(frac=SUBSAMPLE_FRAC, random_state=SEED)
    logger.info(f"  N total={len(df):,} | Subsample={len(df_sample):,}")
    return df_sample


def gap_log(grp):
    """Gap médio de log-renda (negro − branco)."""
    b = grp.loc[grp["negro"] == 0, "log_renda"]
    n = grp.loc[grp["negro"] == 1, "log_renda"]
    if len(b) < 2 or len(n) < 2:
        return np.nan
    return float(n.mean() - b.mean())


def gap_pct(g):
    return (np.exp(g) - 1) * 100 if not np.isnan(g) else np.nan


def bootstrap_gap(grp, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    gaps = []
    for _ in range(n_boot):
        sample = grp.sample(n=len(grp), replace=True, random_state=rng.integers(0, 2**31))
        g = gap_log(sample)
        if not np.isnan(g):
            gaps.append(g)
    arr = np.array(gaps)
    return float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5)), float(arr.std())


def run_analysis(df):
    logger.info("Calculando gap + bootstrap IC 95% por tipo de área ...")
    results = []
    for area in AREA_ORDER:
        sub = df[df["area_tipo"] == area]
        n_total = len(sub)
        n_neg   = (sub["negro"] == 1).sum()
        n_bra   = (sub["negro"] == 0).sum()
        g       = gap_log(sub)
        lo, hi, se = bootstrap_gap(sub, n_boot=N_BOOT)
        results.append({
            "area_tipo":   area,
            "n_total":     n_total,
            "n_negros":    int(n_neg),
            "n_brancos":   int(n_bra),
            "gap_log":     round(g, 6),
            "gap_pct":     round(gap_pct(g), 4),
            "ci_lo_log":   round(lo, 6),
            "ci_hi_log":   round(hi, 6),
            "ci_lo_pct":   round(gap_pct(lo), 4),
            "ci_hi_pct":   round(gap_pct(hi), 4),
            "se_boot":     round(se, 6),
        })
        logger.info(f"  {area}: gap={gap_pct(g):.1f}% "
                    f"[{gap_pct(lo):.1f}%; {gap_pct(hi):.1f}%]")

    # Teste de diferença Capital vs. Interior (permutação)
    cap = df[df["area_tipo"] == "Capital"]
    inter = df[df["area_tipo"] == "Interior"]
    obs_diff = abs(gap_log(cap) - gap_log(inter))
    combined = pd.concat([cap.assign(group="Capital"),
                          inter.assign(group="Interior")])
    perm_diffs = []
    rng = np.random.default_rng(SEED + 1)
    for _ in range(N_BOOT):
        shuffled = combined.copy()
        shuffled["area_tipo"] = rng.permutation(
            ["Capital"] * len(cap) + ["Interior"] * len(inter)
        )
        d = abs(gap_log(shuffled[shuffled["area_tipo"] == "Capital"]) -
                gap_log(shuffled[shuffled["area_tipo"] == "Interior"]))
        perm_diffs.append(d)
    p_perm = float(np.mean(np.array(perm_diffs) >= obs_diff))
    logger.info(f"\n  Teste permutação Capital vs Interior: "
                f"Δgap={gap_pct(obs_diff):.2f}pp, p={p_perm:.4f}")

    df_res = pd.DataFrame(results)
    df_res["p_permut_cap_int"] = [p_perm] + [np.nan] * (len(df_res) - 1)
    df_res.to_csv(OUTPUTS_TB / "segreg_gap_por_area_ci.csv", index=False, encoding="utf-8")
    logger.info("  segreg_gap_por_area_ci.csv salvo.")
    return df_res, p_perm


def plot_ci(df_res):
    logger.info("Gerando figura com IC ...")
    areas = [AREA_LABELS.get(a, a) for a in df_res["area_tipo"]]
    gaps  = df_res["gap_pct"].values
    lo    = df_res["ci_lo_pct"].values
    hi    = df_res["ci_hi_pct"].values
    yerr  = np.array([gaps - lo, hi - gaps])

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#C0392B", "#E67E22", "#8E44AD"]
    bars = ax.bar(areas, gaps, color=colors, alpha=0.8, width=0.55, edgecolor="white", zorder=3)
    ax.errorbar(areas, gaps, yerr=yerr, fmt="none",
                ecolor="black", capsize=8, elinewidth=2, capthick=2, zorder=4)

    for bar, g, l, h in zip(bars, gaps, lo, hi):
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                f"{g:.1f}%\n[{l:.1f}; {h:.1f}]",
                ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    ax.set_ylabel("Gap racial de log-renda (%)", fontsize=10)
    ax.set_title("Gap Salarial Racial por Tipo de Área\nIC 95% Bootstrap (1.000 replicações)",
                 fontsize=11, pad=12)
    ax.set_ylim(0, max(hi) * 1.25)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(OUTPUTS_FIG / "segregacao_gap_area_ci.png", dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("  segregacao_gap_area_ci.png salvo.")


def main():
    logger.info("=" * 60)
    logger.info("  SEGREGAÇÃO ESPACIAL — Gap com Bootstrap IC 95%")
    logger.info("=" * 60)
    df      = load_data()
    df_res, p_perm = run_analysis(df)
    plot_ci(df_res)
    logger.info("\nSegregação CI concluída.")
    return df_res


if __name__ == "__main__":
    main()
