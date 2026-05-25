"""
oster_bounds.py
===============
Sensibilidade de Oster (2019) ao viés de variável omitida.

Para cada par (modelo restrito, modelo completo) calcula:
  δ*  — quanto a seleção sobre não-observáveis precisaria ser, em relação
         à seleção sobre os observáveis, para zerar β_negro.
         δ* > 1 é o critério de robustez de Oster: seria necessário um
         viés maior do que toda a variação explicada pelos controles para
         anular o efeito estimado.
  β*(δ=1) — estimativa conservadora de β assumindo que não-observáveis
              têm o mesmo poder de seleção que os observáveis.
  β*(δ=2) — estimativa ainda mais conservadora.

Fórmulas (psacalc, Oster 2019 eq. simplificada para variâncias iguais):
  δ* = β̃(R̃² − Ṙ²) / [(β̃ − β̇)(R̄² − R̃²)]
  β*(δ) = β̃ − δ × (β̃ − β̇)(R̄² − R̃²) / (R̃² − Ṙ²)

  β̃ = coeficiente do modelo completo   β̇ = modelo restrito
  R̃² = R² completo                     Ṙ² = R² restrito
  R̄² = R²_max (padrão: 1,3 × R̃²)

Referência:
    Oster, E. (2019). Unobservable selection and coefficient stability.
    Journal of Business & Economic Statistics, 37(2), 187–204.
"""

import logging
import warnings
from pathlib import Path
from typing import Dict, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

logger = logging.getLogger(__name__)

ROOT          = Path(__file__).parent.parent
FEATURES_PATH = ROOT / "data" / "processed" / "features.parquet"
OUT_FIG       = ROOT / "outputs" / "figures"
OUT_TAB       = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

R2_MAX_MULT = 1.3


# ── Dados ──────────────────────────────────────────────────────────────────────

def carregar_dados(sample_frac: Optional[float] = None) -> pd.DataFrame:
    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0) & df["negro"].notna()].copy()
    df["UF_str"] = df["UF"].astype(str)
    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)
    logger.info(f"Oster bounds: {len(df):,} obs")
    return df


# ── Especificações OLS ─────────────────────────────────────────────────────────

def _build_formulas(df: pd.DataFrame) -> Dict[str, Tuple[str, str]]:
    """Retorna {nome: (formula, descricao)}. Adiciona controles de ocupação se disponíveis."""
    has_occ = all(c in df.columns for c in ["horas_c", "ocp_dirigente", "emprego_formal"])
    occ = (
        " + horas_c + emprego_formal + conta_propria"
        " + ocp_dirigente + ocp_profissional + ocp_tecnico"
        " + ocp_administrativo + ocp_servicos + ocp_agro"
        " + ocp_operario + ocp_operador"
        if has_occ else ""
    )
    return {
        "M0_bruto": (
            "log_renda ~ negro",
            "Negro (sem controles)",
        ),
        "M1_demografico": (
            "log_renda ~ negro + sexo_fem + idade_c + idade_sq",
            "Negro + demografia",
        ),
        "M2_capital_humano": (
            "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
            " + educ_fund_completo + educ_medio_completo"
            " + educ_superior_completo + educ_pos_graduacao",
            "Negro + dem. + educação",
        ),
        "M3_completo": (
            "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
            " + educ_fund_completo + educ_medio_completo"
            " + educ_superior_completo + educ_pos_graduacao"
            " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
            " + C(UF_str)" + occ,
            "Negro + todos os controles",
        ),
    }


# ── Estimação ──────────────────────────────────────────────────────────────────

def estimar_modelos(df: pd.DataFrame) -> Dict:
    """Estima OLS para cada especificação e retorna métricas de β_negro."""
    formulas = _build_formulas(df)
    resultados = {}
    for nome, (formula, desc) in formulas.items():
        logger.info(f"  OLS {nome} ...")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            res = smf.ols(formula, data=df).fit()
        resultados[nome] = {
            "beta":      res.params.get("negro", np.nan),
            "se":        res.bse.get("negro", np.nan),
            "r2":        res.rsquared,
            "descricao": desc,
            "n":         int(res.nobs),
        }
        m = resultados[nome]
        logger.info(f"    β={m['beta']:.4f}  SE={m['se']:.4f}  R²={m['r2']:.4f}")
    return resultados


# ── Cálculo de Oster ───────────────────────────────────────────────────────────

def calcular_oster(
    b_rest: float, r2_rest: float,
    b_full: float, r2_full: float,
    r2_max: Optional[float] = None,
) -> Tuple[float, float, float]:
    """
    Retorna (delta_star, beta_star_d1, beta_star_d2).
    Fórmulas do psacalc (Oster, 2019): variância normalizada de X.
    """
    if r2_max is None:
        r2_max = min(R2_MAX_MULT * r2_full, 0.99)

    dR_full_rest = r2_full - r2_rest
    dR_max_full  = r2_max  - r2_full
    db           = b_full  - b_rest

    if abs(db) < 1e-10 or abs(dR_full_rest) < 1e-10:
        return np.nan, np.nan, np.nan

    delta_star   = (b_full * dR_full_rest) / (db * dR_max_full)
    beta_star_d1 = b_full - db * dR_max_full / dR_full_rest
    beta_star_d2 = b_full - 2 * db * dR_max_full / dR_full_rest

    return delta_star, beta_star_d1, beta_star_d2


def tabela_oster(modelos: Dict) -> pd.DataFrame:
    b_full  = modelos["M3_completo"]["beta"]
    r2_full = modelos["M3_completo"]["r2"]
    r2_max  = min(R2_MAX_MULT * r2_full, 0.99)

    rows = []
    for nome in ["M0_bruto", "M1_demografico", "M2_capital_humano"]:
        m = modelos[nome]
        delta, b1, b2 = calcular_oster(m["beta"], m["r2"], b_full, r2_full, r2_max)
        rows.append({
            "Modelo restrito":  m["descricao"],
            "β̇ (restrito)":    f"{m['beta']:.4f}",
            "Ṙ²":              f"{m['r2']:.4f}",
            "β̃ (completo)":   f"{b_full:.4f}",
            "R̃²":             f"{r2_full:.4f}",
            "R̄² (max)":       f"{r2_max:.4f}",
            "δ*":              f"{delta:.2f}" if not np.isnan(delta) else "—",
            "β*(δ=1)":         f"{b1:.4f}" if not np.isnan(b1) else "—",
            "β*(δ=2)":         f"{b2:.4f}" if not np.isnan(b2) else "—",
            "Robusto":         "Sim ✓" if (not np.isnan(delta) and abs(delta) > 1) else "Não",
        })
    return pd.DataFrame(rows)


# ── Figura ─────────────────────────────────────────────────────────────────────

def plotar_oster(modelos: Dict, tab: pd.DataFrame) -> None:
    b_full  = modelos["M3_completo"]["beta"]
    r2_full = modelos["M3_completo"]["r2"]
    r2_max  = min(R2_MAX_MULT * r2_full, 0.99)

    nomes = ["M0_bruto", "M1_demografico", "M2_capital_humano", "M3_completo"]
    labels = ["M0\n(bruto)", "M1\n(+ demog.)", "M2\n(+ educ.)", "M3\n(completo)"]
    betas = [modelos[n]["beta"] for n in nomes]
    ses   = [modelos[n]["se"]   for n in nomes]

    bstar_d1 = []
    deltas   = []
    for nome in nomes[:-1]:
        d, b1, _ = calcular_oster(modelos[nome]["beta"], modelos[nome]["r2"],
                                   b_full, r2_full, r2_max)
        bstar_d1.append(b1)
        deltas.append(d)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Painel 1 — coeficientes e bounds
    x = np.arange(len(nomes))
    ax1.bar(x, betas, color="#2980b9", alpha=0.75, label="β_negro (OLS)")
    ax1.errorbar(x, betas, yerr=[1.96 * s for s in ses],
                 fmt="none", color="black", capsize=4)
    for i, b1 in enumerate(bstar_d1):
        if not np.isnan(b1):
            ax1.scatter(x[i], b1, marker="D", color="#c0392b", zorder=5, s=60,
                        label="β*(δ=1)" if i == 0 else "")
    ax1.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel("β_negro (log-renda)")
    ax1.set_title("Estabilidade de β_negro por modelo\nDiamante vermelho = bound δ=1")
    ax1.legend(fontsize=9)

    # Painel 2 — δ*
    x2 = np.arange(len(deltas))
    cores = ["#27ae60" if (not np.isnan(d) and abs(d) > 1) else "#e74c3c"
             for d in deltas]
    ax2.bar(x2, deltas, color=cores, alpha=0.85)
    ax2.axhline(1, color="black", linewidth=1.2, linestyle="--",
                label="δ* = 1 (limiar de robustez)")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(["M0→M3", "M1→M3", "M2→M3"])
    ax2.set_ylabel("δ* (Oster, 2019)")
    ax2.set_title("Seleção relativa sobre não-observáveis\nnecessária para anular β_negro")
    ax2.legend(fontsize=9)
    for xi, dv in zip(x2, deltas):
        if not np.isnan(dv):
            ax2.text(xi, dv + max(abs(dv) * 0.03, 0.05),
                     f"{dv:.2f}", ha="center", fontsize=10, fontweight="bold")

    plt.suptitle(
        "Oster (2019) — Robustez do Gap Salarial Racial a Variáveis Omitidas\n"
        f"R̄² = {r2_max:.3f} ({R2_MAX_MULT}× R̃²)  ·  Verde = δ* > 1 (robusto)",
        fontsize=11,
    )
    plt.tight_layout()
    fig.savefig(OUT_FIG / "oster_bounds.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: oster_bounds.png")


# ── Pipeline principal ─────────────────────────────────────────────────────────

def run_oster_bounds(sample_frac: Optional[float] = None) -> Dict:
    df = carregar_dados(sample_frac=sample_frac)

    logger.info("Estimando modelos OLS para Oster bounds ...")
    modelos = estimar_modelos(df)

    tab = tabela_oster(modelos)
    tab.to_csv(OUT_TAB / "oster_bounds.csv", index=False)
    (OUT_TAB / "oster_bounds.tex").write_text(
        tab.to_latex(
            index=False, escape=False,
            caption=(
                r"Análise de Sensibilidade de Oster (2019) --- Gap Salarial Racial. "
                r"$\delta^*$: razão mínima de seleção sobre não-observáveis vs.\ observáveis "
                r"para zerar $\hat{\beta}_{\text{negro}}$. "
                r"$\beta^*(\delta{=}1)$: bound conservador assumindo seleção igual. "
                r"$\bar{R}^2 = 1{,}3 \times \tilde{R}^2$. PNAD Contínua 2016--2025."
            ),
            label="tab:oster_bounds",
        ),
        encoding="utf-8",
    )
    plotar_oster(modelos, tab)

    m3 = modelos["M3_completo"]
    r2_max = min(R2_MAX_MULT * m3["r2"], 0.99)
    print("\n── SUMÁRIO: Oster Bounds ──")
    print(f"  β_negro M3 (completo) : {m3['beta']:.4f}  →  {(np.exp(m3['beta'])-1)*100:.1f}%")
    print(f"  n={m3['n']:,}  R²={m3['r2']:.4f}  R̄²={r2_max:.4f}")
    print()
    print(tab[["Modelo restrito", "δ*", "β*(δ=1)", "Robusto"]].to_string(index=False))

    return {"modelos": modelos, "tabela": tab}
