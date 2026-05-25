"""
rif_decomp.py
=============
Decomposição de Oaxaca-Blinder via Recentered Influence Function (RIF-OB).

Enquanto o OB clássico decompõe o gap na *média* em dotações e retornos,
a RIF-OB (Firpo, Fortin & Lemieux, 2018) faz o mesmo para *cada quantil*
da distribuição incondicional, respondendo:

    "O glass ceiling salarial racial é explicado por dotações piores
     dos negros nos quantis superiores, ou por retornos diferenciais?"

Metodologia:
    1. Para cada quantil τ, calcula a RIF:
       RIF(y; Qτ) = Qτ + [τ − 1(y ≤ Qτ)] / f_Y(Qτ)
       onde f_Y(Qτ) é a densidade marginal estimada por kernel Gaussiano.

    2. Regride RIF ~ X separadamente para Brancos e Negros (OLS).

    3. Aplica a decomposição twofold de OB nos coeficientes RIF:
       Gap(τ)    = X̄_B β_B − X̄_N β_N
       Dotações  = (X̄_B − X̄_N) β_B        [efeito composição]
       Retornos  = X̄_N (β_B − β_N)         [efeito estrutura]

Referência:
    Firpo, S., Fortin, N. M., & Lemieux, T. (2018). Decomposing wage
    distributions using recentered influence function regressions.
    Econometrics, 6(2), 28. doi:10.3390/econometrics6020028
"""

import logging
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import gaussian_kde

logger = logging.getLogger(__name__)

ROOT          = Path(__file__).parent.parent
FEATURES_PATH = ROOT / "data" / "processed" / "features.parquet"
OUT_FIG       = ROOT / "outputs" / "figures"
OUT_TAB       = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

QUANTIS_DEFAULT = [0.10, 0.25, 0.50, 0.75, 0.90]

CONTROLES = (
    "educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
    " + idade_c + idade_sq + sexo_fem"
    " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
    " + C(UF_str)"
)


# ── Dados ──────────────────────────────────────────────────────────────────────

def carregar_dados(sample_frac: Optional[float] = None) -> pd.DataFrame:
    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0) & df["negro"].notna()].copy()
    df["UF_str"] = df["UF"].astype(str)
    req = ["educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
           "idade_c", "idade_sq", "sexo_fem",
           "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z"]
    df = df.dropna(subset=req).reset_index(drop=True)
    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)
    logger.info(f"RIF-OB: {len(df):,} obs  |  "
                f"Brancos={int((df['negro']==0).sum()):,}  "
                f"Negros={int((df['negro']==1).sum()):,}")
    return df


# ── RIF ────────────────────────────────────────────────────────────────────────

def calcular_rif(y: np.ndarray, tau: float,
                 kde_sample: int = 200_000) -> np.ndarray:
    """
    Calcula o vetor RIF para o quantil tau.

    A densidade f_Y(Qτ) é estimada por kernel Gaussiano numa subamostra
    (kde_sample obs) para eficiência, depois avaliada no quantil amostral.
    """
    q_tau = np.quantile(y, tau)

    # KDE numa subamostra para estimar f_Y(Qτ)
    if len(y) > kde_sample:
        rng  = np.random.default_rng(42)
        ysub = rng.choice(y, size=kde_sample, replace=False)
    else:
        ysub = y

    kde    = gaussian_kde(ysub, bw_method="silverman")
    f_qtau = float(kde.evaluate([q_tau])[0])
    f_qtau = max(f_qtau, 1e-6)  # evita divisão por zero em caudas esparsas

    rif = q_tau + (tau - (y <= q_tau).astype(float)) / f_qtau
    return rif


# ── RIF-OB por quantil ────────────────────────────────────────────────────────

def rif_ob_quantil(
    df: pd.DataFrame,
    tau: float,
    formula_controles: str,
) -> Dict:
    """
    Decomposição OB twofold da diferença de quantis incondicionais via RIF.
    Retorna dict com gap, dotações, retornos, interação e percentuais.
    """
    y_all = df["log_renda"].values
    rif   = calcular_rif(y_all, tau)
    df    = df.copy()
    df["rif"] = rif

    formula = f"rif ~ {formula_controles}"

    df_b = df[df["negro"] == 0]
    df_n = df[df["negro"] == 1]

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        res_b = smf.ols(formula, data=df_b).fit()
        res_n = smf.ols(formula, data=df_n).fit()

    # Médias do vetor de covariáveis para cada grupo (alinhadas ao modelo de brancos)
    X_b = res_b.model.exog
    X_n = res_n.model.exog
    xbar_b = X_b.mean(axis=0)
    xbar_n = X_n.mean(axis=0)
    beta_b = res_b.params.values
    beta_n = res_n.params.values

    gap      = df_b["log_renda"].quantile(tau) - df_n["log_renda"].quantile(tau)
    rif_gap  = xbar_b @ beta_b - xbar_n @ beta_n
    end      = (xbar_b - xbar_n) @ beta_b
    ret      = xbar_n @ (beta_b - beta_n)
    inter    = (xbar_b - xbar_n) @ (beta_b - beta_n)

    def _pct(x):
        return x / gap * 100 if abs(gap) > 1e-6 else 0.0

    return {
        "tau":       tau,
        "q_label":   f"q{int(tau*100):02d}",
        "gap_obs":   gap,
        "gap_rif":   rif_gap,
        "end":       end,
        "ret":       ret,
        "inter":     inter,
        "end_pct":   _pct(end),
        "ret_pct":   _pct(ret),
        "inter_pct": _pct(inter),
        "n_b":       len(df_b),
        "n_n":       len(df_n),
    }


def run_rif_ob(
    df: pd.DataFrame,
    quantis: List[float] = QUANTIS_DEFAULT,
    formula_controles: str = CONTROLES,
) -> pd.DataFrame:
    """Executa RIF-OB para todos os quantis e retorna DataFrame de resultados."""
    rows = []
    for tau in quantis:
        logger.info(f"  RIF-OB q{int(tau*100):02d} ...")
        r = rif_ob_quantil(df, tau, formula_controles)
        rows.append(r)
        logger.info(f"    gap={r['gap_obs']:.4f}  dot={r['end_pct']:.1f}%  ret={r['ret_pct']:.1f}%")
    return pd.DataFrame(rows)


# ── Figuras ────────────────────────────────────────────────────────────────────

def plotar_rif_ob(df_rif: pd.DataFrame) -> None:
    """
    Dois painéis:
    (1) Gap observado e gap RIF por quantil — valida a aproximação.
    (2) Decomposição dotações vs. retornos (barras empilhadas) por quantil.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    xticks = [r["q_label"] for _, r in df_rif.iterrows()]

    # Painel 1 — gaps
    ax1.plot(xticks, df_rif["gap_obs"] * (-1) * 100, marker="o",
             color="#2980b9", label="Gap observado (%) — Branco − Negro")
    ax1.plot(xticks, df_rif["gap_rif"] * (-1) * 100, marker="s",
             linestyle="--", color="#e67e22", label="Gap via RIF (OB)")
    ax1.axhline(0, color="black", linewidth=0.6, linestyle=":")
    ax1.set_xlabel("Quantil")
    ax1.set_ylabel("Gap salarial racial (%)")
    ax1.set_title("Gap racial por quantil\n(positivo = brancos ganham mais)")
    ax1.legend(fontsize=9)

    # Painel 2 — decomposição empilhada
    x  = np.arange(len(df_rif))
    w  = 0.35
    e  = df_rif["end_pct"].values
    r  = df_rif["ret_pct"].values
    i  = df_rif["inter_pct"].values

    ax2.bar(x - w/2, e, w, label="Dotações (%)", color="#3498db", alpha=0.85)
    ax2.bar(x + w/2, r, w, label="Retornos (%)", color="#e74c3c", alpha=0.85)
    ax2.bar(x + w/2 + w, i, w * 0.6, label="Interação (%)",
            color="#95a5a6", alpha=0.7)
    ax2.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax2.axhline(100, color="#7f8c8d", linewidth=0.5, linestyle=":")
    ax2.set_xticks(x)
    ax2.set_xticklabels(xticks)
    ax2.set_ylabel("Parcela do gap (%)")
    ax2.set_title("Decomposição RIF-OB por quantil\nDotações vs. Retornos")
    ax2.legend(fontsize=9)

    plt.suptitle(
        "RIF-OB (Firpo, Fortin & Lemieux, 2018) — Gap Racial por Quantil Incondicional\n"
        "PNAD Contínua 2016–2025  ·  Desfecho: log-renda  ·  Tratamento: negro",
        fontsize=11,
    )
    plt.tight_layout()
    fig.savefig(OUT_FIG / "rif_ob_decomposicao.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: rif_ob_decomposicao.png")


def plotar_rif_retornos_detalhe(df_rif: pd.DataFrame) -> None:
    """Foco na parcela de retornos por quantil — ilustra o glass ceiling discriminatório."""
    fig, ax = plt.subplots(figsize=(8, 5))
    xticks = [r["q_label"] for _, r in df_rif.iterrows()]
    ax.plot(xticks, df_rif["ret_pct"], marker="o", color="#c0392b",
            linewidth=2, label="Retornos (% do gap)")
    ax.plot(xticks, df_rif["end_pct"], marker="s", color="#2980b9",
            linewidth=2, label="Dotações (% do gap)")
    ax.axhline(0, color="black", linewidth=0.6, linestyle="--")
    ax.axhline(100, color="#7f8c8d", linewidth=0.5, linestyle=":")
    for x_i, (_, row) in enumerate(df_rif.iterrows()):
        ax.annotate(f"{row['ret_pct']:.0f}%",
                    (x_i, row["ret_pct"]),
                    textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=9, color="#c0392b")
    ax.set_xlabel("Quantil")
    ax.set_ylabel("Parcela do gap explicada (%)")
    ax.set_title(
        "Parcela discriminatória (retornos) cresce nos quantis superiores?\n"
        "RIF-OB — PNAD Contínua 2016–2025",
        fontsize=11,
    )
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "rif_ob_retornos_quantis.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: rif_ob_retornos_quantis.png")


# ── Pipeline principal ─────────────────────────────────────────────────────────

def run_rif_decomp(
    sample_frac: Optional[float] = None,
    quantis: Optional[List[float]] = None,
) -> Dict:
    if quantis is None:
        quantis = QUANTIS_DEFAULT

    df = carregar_dados(sample_frac=sample_frac)

    logger.info("Executando RIF-OB por quantil ...")
    df_rif = run_rif_ob(df, quantis=quantis)

    df_rif.to_csv(OUT_TAB / "rif_ob_decomposicao.csv", index=False)
    (OUT_TAB / "rif_ob_decomposicao.tex").write_text(
        df_rif[["q_label", "gap_obs", "end_pct", "ret_pct", "inter_pct", "n_b", "n_n"]]
        .rename(columns={
            "q_label":   "Quantil",
            "gap_obs":   "Gap obs.",
            "end_pct":   "Dotações (%)",
            "ret_pct":   "Retornos (%)",
            "inter_pct": "Interação (%)",
            "n_b":       "n (brancos)",
            "n_n":       "n (negros)",
        })
        .round({"Gap obs.": 4, "Dotações (%)": 1, "Retornos (%)": 1, "Interação (%)": 1})
        .to_latex(
            index=False, escape=False,
            caption=(
                r"Decomposição RIF-OB (Firpo, Fortin \& Lemieux, 2018) do Gap Salarial Racial "
                r"por Quantil Incondicional. "
                r"Dotações: diferença de capital humano e contexto. "
                r"Retornos: diferença nos retornos às características observáveis "
                r"(componente discriminatório). PNAD Contínua 2016--2025."
            ),
            label="tab:rif_ob",
        ),
        encoding="utf-8",
    )

    plotar_rif_ob(df_rif)
    plotar_rif_retornos_detalhe(df_rif)

    print("\n── SUMÁRIO: RIF-OB (Firpo, Fortin & Lemieux, 2018) ──")
    print(df_rif[["q_label", "gap_obs", "end_pct", "ret_pct", "inter_pct"]].
          rename(columns={"q_label": "Quantil", "gap_obs": "Gap",
                          "end_pct": "Dotações%", "ret_pct": "Retornos%",
                          "inter_pct": "Interação%"}).
          round({"Gap": 4, "Dotações%": 1, "Retornos%": 1, "Interação%": 1}).
          to_string(index=False))

    q10 = df_rif[df_rif["tau"] == 0.10].iloc[0]
    q90 = df_rif[df_rif["tau"] == 0.90].iloc[0]
    print(f"\n  Glass ceiling discriminatório: "
          f"retornos q10={q10['ret_pct']:.1f}% → q90={q90['ret_pct']:.1f}%")

    return {"rif": df_rif}
