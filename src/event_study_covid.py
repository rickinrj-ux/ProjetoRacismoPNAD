"""
event_study_covid.py
====================
Event study do choque COVID-19 (2020) no gap salarial racial.

Motivação:
    Os dados anuais mostram β_negro = −0.108 (2019) → −0.098 (2020) → −0.102 (2021):
    uma queda de ~1pp no gap em 2020 seguida de recuperação parcial. Duas hipóteses:

    H1 — Preço: discriminação racial foi temporariamente atenuada pelo choque
         (salários brancos caíram mais → convergência genuína).
    H2 — Composição: trabalhadores informais negros saíram da amostra de empregados
         em 2020 (desemprego → seleção positiva → gap observado diminui mecanicamente).

Método:
    1. Event study pooled (OLS + interações negro × C(Ano)):
       log_renda_{it} = α + Σ_t γ_t·1(Ano=t) + Σ_{t≠2019} δ_t·(negro_i × 1(Ano=t))
                      + X_i'β + C(UF) + ε_{it}
       δ_t = gap racial no ano t relativo a 2019.

    2. Decomposição composicional (de Chaisemartin & D'Haultfoeuille, 2020):
       Variação observada no gap = mudança de preço + mudança composicional
       Identifica se negros informais saíram mais do emprego em 2020.

    3. DiD 2×2 (negro × {2019 vs 2020}):
       τ_DiD = (ȳ_negro,2020 − ȳ_negro,2019) − (ȳ_branco,2020 − ȳ_branco,2019)
       Teste se o CHOQUE diferencial foi estatisticamente significativo.

    4. Teste de pré-tendência: δ_{2016} = δ_{2017} = δ_{2018} = 0
       (exigência de paralelismo pré-COVID).

Referências:
    de Chaisemartin, C., & D'Haultfoeuille, X. (2020). Two-way fixed effects
        estimators with heterogeneous treatment effects. AER, 110(9), 2964–2996.
    Callaway, B., & Sant'Anna, P. H. C. (2021). Difference-in-differences with
        multiple time periods. JOE, 225(2), 200–230.
    Sun, L., & Abraham, S. (2021). Estimating dynamic treatment effects in event
        studies with heterogeneous treatment effects. JOE, 225(2), 175–199.
"""

import logging
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

logger = logging.getLogger(__name__)

ROOT          = Path(__file__).parent.parent
FEATURES_PATH = ROOT / "data" / "processed" / "features.parquet"
TEMPORAL_CSV  = ROOT / "outputs" / "tables" / "validacao_temporal.csv"
OUT_FIG       = ROOT / "outputs" / "figures"
OUT_TAB       = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

BASE_YEAR  = 2019
COVID_YEAR = 2020
ANOS       = list(range(2016, 2026))

_OLS_COLS = [
    "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "log_renda", "log_horas", "urbano", "Ano", "UF",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "emprego_formal", "pea", "empregado",
]

_COMP_COLS = [
    "negro", "Ano", "log_renda", "emprego_formal", "pea", "empregado",
]


# ── Carregamento ──────────────────────────────────────────────────────────────

def _load_empregados(sample_frac: Optional[float] = None) -> pd.DataFrame:
    logger.info("Carregando features.parquet (OLS event study)...")
    df = pd.read_parquet(FEATURES_PATH, columns=_OLS_COLS)
    df = df[df["negro"].isin([0.0, 1.0])].copy()
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    model_vars = [
        "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_fund_completo", "educ_medio_completo",
        "educ_superior_completo", "educ_pos_graduacao",
        "log_horas", "urbano", "Ano", "UF",
        "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    ]
    df = df.dropna(subset=model_vars).copy()
    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42)
    logger.info(f"  Dataset OLS: {len(df):,} obs")
    return df


def _load_pea_comp() -> pd.DataFrame:
    logger.info("Carregando features.parquet (decomposição composicional)...")
    df = pd.read_parquet(FEATURES_PATH, columns=_COMP_COLS)
    df = df[df["negro"].isin([0.0, 1.0])].copy()
    df["pea_bool"] = df["pea"].fillna(0).astype(bool)
    df["emp_bool"] = df["empregado"].fillna(0).astype(bool)
    df["y_sel"] = (df["log_renda"].notna() & (df["log_renda"] > 0)).astype(int)
    return df


# ── 1. Event Study OLS com Interações ────────────────────────────────────────

def _criar_interacoes(df: pd.DataFrame, base_year: int = BASE_YEAR) -> pd.DataFrame:
    """Cria dummies negro × Ano para o event study (exclui base_year)."""
    df = df.copy()
    for yr in ANOS:
        if yr != base_year:
            df[f"negro_x_{yr}"] = df["negro"] * (df["Ano"] == yr).astype(int)
    return df


def estimar_event_study(df: pd.DataFrame) -> Dict:
    """
    OLS poolado com interações negro × C(Ano).

    Especificação:
        log_renda = α + Σ_t γ_t·1(Ano=t) + Σ_{t≠base} δ_t·(negro × 1(Ano=t))
                  + negro + controles + C(UF) + ε

    δ_t = gap racial no ano t RELATIVO a 2019.
    H₀ de pré-tendência: δ_{2016} = δ_{2017} = δ_{2018} = 0.
    """
    df_x = _criar_interacoes(df)

    # Termos de interação (excluindo ano base)
    int_terms = " + ".join(f"negro_x_{yr}" for yr in ANOS if yr != BASE_YEAR)

    formula = (
        "log_renda ~ negro"
        " + sexo_fem + idade_c + idade_sq"
        " + educ_fund_completo + educ_medio_completo"
        " + educ_superior_completo + educ_pos_graduacao"
        " + log_horas + urbano + C(Ano) + C(UF)"
        " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
        f" + {int_terms}"
    )

    logger.info("Estimando OLS event study (interações negro × Ano)...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = smf.ols(formula, data=df_x).fit(
            cov_type="cluster", cov_kwds={"groups": df_x["UF"]}
        )

    # Extrai δ_t
    rows = []
    for yr in ANOS:
        if yr == BASE_YEAR:
            rows.append({
                "ano": yr, "t": 0, "delta": 0.0, "se": 0.0, "pval": np.nan,
                "ci95_lo": 0.0, "ci95_hi": 0.0, "referencia": True
            })
        else:
            key = f"negro_x_{yr}"
            if key in res.params.index:
                b  = res.params[key]
                se = res.bse[key]
                pv = res.pvalues[key]
                rows.append({
                    "ano": yr, "t": yr - BASE_YEAR,
                    "delta": b, "se": se, "pval": pv,
                    "ci95_lo": b - 1.96 * se, "ci95_hi": b + 1.96 * se,
                    "referencia": False
                })

    df_es = pd.DataFrame(rows).sort_values("ano")

    # β_negro em 2019 (nível base)
    beta_2019 = res.params.get("negro", np.nan)
    logger.info(f"  β_negro (2019 base): {beta_2019:.5f}")

    # Teste de pré-tendência (Wald: δ_2016 = δ_2017 = δ_2018 = 0)
    pre_terms = [f"negro_x_{yr}" for yr in [2016, 2017, 2018]]
    try:
        r_matrix = np.zeros((len(pre_terms), len(res.params)))
        for i, t in enumerate(pre_terms):
            if t in res.params.index:
                r_matrix[i, list(res.params.index).index(t)] = 1
        # scalar=True evita FutureWarning no statsmodels ≥ 0.14
        try:
            wald = res.wald_test(r_matrix, scalar=True)
        except TypeError:
            wald = res.wald_test(r_matrix)
        stat_raw = wald.statistic
        # Compatibilidade: pode ser array 2D em versões antigas
        f_pre = float(np.squeeze(stat_raw))
        p_pre = float(wald.pvalue)
        df_num  = len(pre_terms)
        df_den  = res.df_resid
    except Exception as exc:
        logger.warning(f"Wald test pré-tendência falhou: {exc}")
        f_pre, p_pre, df_num, df_den = np.nan, np.nan, 3, len(df_x) - res.df_model - 1

    return {
        "res": res,
        "df_es": df_es,
        "beta_2019": beta_2019,
        "f_pre_trend": f_pre,
        "p_pre_trend": p_pre,
        "pre_trend_ok": (not np.isnan(p_pre)) and (p_pre >= 0.10),
    }


# ── 2. Decomposição Composicional ────────────────────────────────────────────

def decomposicao_composicional(df_pea: pd.DataFrame) -> pd.DataFrame:
    """
    Decomposição da variação do gap em 2020:

        Δgap = Δ_preço + Δ_composição

    Onde:
        gap_t = ȳ_negro,t(empregados) − ȳ_branco,t(empregados)

        Δ_composição ≈ efeito de negros informais saírem da amostra em 2020
        Δ_preço ≈ mudança no gap condicional à composição constante

    Operacionalização:
        Computa taxa de emprego por (negro × formal × Ano)
        e renda média condicional por (negro × formal × Ano).
        Se em 2020 a proporção de informais negros cai mais → composição explica parte do gap.
    """
    df_pea["formal"] = df_pea["emprego_formal"].fillna(0).astype(int)

    agg = (
        df_pea[df_pea["pea_bool"]]
        .groupby(["Ano", "negro"])
        .agg(
            n_pea=("pea_bool", "sum"),
            n_emp=("y_sel", "sum"),
            n_formal=("formal", "sum"),
            renda_media_emp=("log_renda", lambda x: x[df_pea.loc[x.index, "y_sel"] == 1].mean()),
        )
        .reset_index()
    )
    agg["tx_emprego"]  = agg["n_emp"] / agg["n_pea"]
    agg["tx_formal"]   = agg["n_formal"] / agg["n_emp"].replace(0, np.nan)
    agg["gap_bruto"]   = np.nan

    # Gap bruto por ano (condicional a ser empregado)
    pivot = agg.pivot(index="Ano", columns="negro", values="renda_media_emp")
    pivot.columns = ["renda_branco", "renda_negro"]
    pivot["gap_bruto"] = pivot["renda_negro"] - pivot["renda_branco"]

    # Merge de volta
    result = (
        agg.pivot(index="Ano", columns="negro", values=["tx_emprego", "tx_formal", "renda_media_emp"])
        .reset_index()
    )
    result.columns = [
        "Ano",
        "tx_emp_branco", "tx_emp_negro",
        "tx_form_branco", "tx_form_negro",
        "renda_branco", "renda_negro",
    ]
    result["gap_bruto_log"] = result["renda_negro"] - result["renda_branco"]
    result["gap_bruto_pct"] = (np.exp(result["gap_bruto_log"]) - 1) * 100
    result["delta_emp_negro"]  = result["tx_emp_negro"].diff()
    result["delta_emp_branco"] = result["tx_emp_branco"].diff()
    result["delta_gap"] = result["gap_bruto_log"].diff()

    # Destaque 2019 e 2020
    result["marco"] = result["Ano"].map(
        {BASE_YEAR: "Pré-COVID", COVID_YEAR: "COVID (choque)", 2021: "Pós-COVID (recuperação)"}
    ).fillna("")

    return result


# ── 3. DiD 2×2 ───────────────────────────────────────────────────────────────

def did_covid(df: pd.DataFrame) -> Dict:
    """
    DiD clássico 2×2: negro × {2019 vs 2020}

        τ_DiD = (ȳ_negro,2020 − ȳ_negro,2019) − (ȳ_branco,2020 − ȳ_branco,2019)

    Também estima DiD via regressão com SE clusterizado:
        log_renda = α + β·negro + γ·post + τ·(negro × post) + controles + ε

    τ = efeito diferencial do COVID sobre negros vs brancos.
    τ > 0 → negros sofreram MENOS (aparente convergência)
    τ < 0 → negros sofreram MAIS (divergência)
    """
    df_did = df[df["Ano"].isin([BASE_YEAR, COVID_YEAR])].copy()
    df_did["post"] = (df_did["Ano"] == COVID_YEAR).astype(int)
    df_did["negro_x_post"] = df_did["negro"] * df_did["post"]

    formula_did = (
        "log_renda ~ negro + post + negro_x_post"
        " + sexo_fem + idade_c + idade_sq"
        " + educ_fund_completo + educ_medio_completo"
        " + educ_superior_completo + educ_pos_graduacao"
        " + log_horas + urbano + C(UF)"
        " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
    )

    logger.info("Estimando DiD 2×2 (2019 vs 2020)...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res_did = smf.ols(formula_did, data=df_did).fit(
            cov_type="cluster", cov_kwds={"groups": df_did["UF"]}
        )

    tau    = res_did.params.get("negro_x_post", np.nan)
    se_tau = res_did.bse.get("negro_x_post", np.nan)
    pv_tau = res_did.pvalues.get("negro_x_post", np.nan)

    # Média simples por célula
    means = (
        df_did.groupby(["negro", "post"])["log_renda"]
        .agg(["mean", "sem", "count"])
        .reset_index()
    )
    means.columns = ["negro", "post", "mean_log", "se_log", "n"]
    means["grupo"]  = means["negro"].map({0: "Branco", 1: "Negro"})
    means["period"] = means["post"].map({0: "2019 (pré)", 1: "2020 (COVID)"})

    tau_naive = (
        means.loc[(means["negro"]==1)&(means["post"]==1), "mean_log"].values[0]
      - means.loc[(means["negro"]==1)&(means["post"]==0), "mean_log"].values[0]
      - means.loc[(means["negro"]==0)&(means["post"]==1), "mean_log"].values[0]
      + means.loc[(means["negro"]==0)&(means["post"]==0), "mean_log"].values[0]
    )

    logger.info(
        f"  DiD τ = {tau:.5f}  (SE={se_tau:.5f}, p={pv_tau:.4f})  "
        f"  τ_naive = {tau_naive:.5f}"
    )

    return {
        "res_did": res_did,
        "tau": tau,
        "se_tau": se_tau,
        "pval_tau": pv_tau,
        "tau_naive": tau_naive,
        "means": means,
        "interpretacao": (
            "Negros sofreram MENOS com COVID → aparente convergência"
            if tau > 0 else
            "Negros sofreram MAIS com COVID → divergência"
        ),
    }


# ── Figura principal ──────────────────────────────────────────────────────────

def plotar_event_study(
    es_res: Dict,
    comp_res: pd.DataFrame,
    did_res: Dict,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # ── Painel A: Event study plot ────────────────────────────────────────────
    ax = axes[0, 0]
    df_es = es_res["df_es"]
    anos  = df_es["ano"].values
    delta = df_es["delta"].values
    ci_lo = df_es["ci95_lo"].values
    ci_hi = df_es["ci95_hi"].values

    ax.axvspan(COVID_YEAR - 0.3, COVID_YEAR + 0.3, alpha=0.15, color="#e74c3c",
               label="Choque COVID-19")
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.7)
    ax.axvline(BASE_YEAR, color="gray", linewidth=0.8, linestyle=":", alpha=0.7,
               label=f"Ano base ({BASE_YEAR})")
    ax.fill_between(anos, ci_lo, ci_hi, alpha=0.2, color="#3498db")
    ax.plot(anos, delta, "o-", color="#2c3e50", lw=2, ms=6, zorder=5)
    ax.scatter([BASE_YEAR], [0], color="#e67e22", s=80, zorder=6, label="Referência (2019)")

    # Anotação pré-tendência
    p_pre = es_res["p_pre_trend"]
    pre_ok = es_res["pre_trend_ok"]
    ax.text(0.02, 0.98,
            f"Pré-tendência: p = {p_pre:.3f}\n"
            f"{'✓ Paralelismo suportado (p≥0.10)' if pre_ok else '✗ Tendência pré-COVID detectada'}",
            transform=ax.transAxes, va="top", fontsize=8.5,
            bbox=dict(fc="lightgreen" if pre_ok else "lightyellow", ec="gray", alpha=0.85))

    ax.set_xticks(anos)
    ax.set_xticklabels(anos, rotation=45, fontsize=8)
    ax.set_xlabel("Ano")
    ax.set_ylabel("δ_t = gap racial relativo a 2019 (log-pontos)")
    ax.set_title("Event Study — Gap Racial Relativo a 2019\n(OLS Poolado com Interações negro × Ano)", fontsize=9.5)
    ax.legend(fontsize=8)

    # ── Painel B: Gap bruto por ano ───────────────────────────────────────────
    ax = axes[0, 1]
    ax.axvspan(COVID_YEAR - 0.3, COVID_YEAR + 0.3, alpha=0.15, color="#e74c3c")
    ax.plot(comp_res["Ano"], comp_res["gap_bruto_pct"], "s-", color="#8e44ad",
            lw=2, ms=6, label="Gap bruto (%)")
    ax.set_xticks(comp_res["Ano"].values)
    ax.set_xticklabels(comp_res["Ano"].values, rotation=45, fontsize=8)
    ax.set_xlabel("Ano")
    ax.set_ylabel("Gap salarial bruto (%)")
    ax.set_title("Gap Salarial Racial Bruto por Ano\n(ȳ_negro − ȳ_branco em log, empregados)", fontsize=9.5)
    ax.legend()

    # ── Painel C: Taxa de emprego por grupo racial ────────────────────────────
    ax = axes[1, 0]
    ax.axvspan(COVID_YEAR - 0.3, COVID_YEAR + 0.3, alpha=0.15, color="#e74c3c",
               label="COVID-19")
    ax.plot(comp_res["Ano"], comp_res["tx_emp_negro"] * 100, "o-",
            color="#e74c3c", lw=2, ms=6, label="Taxa emprego negros (%)")
    ax.plot(comp_res["Ano"], comp_res["tx_emp_branco"] * 100, "s-",
            color="#3498db", lw=2, ms=6, label="Taxa emprego brancos (%)")
    ax.set_xticks(comp_res["Ano"].values)
    ax.set_xticklabels(comp_res["Ano"].values, rotation=45, fontsize=8)
    ax.set_xlabel("Ano")
    ax.set_ylabel("Taxa de emprego (%)")
    ax.set_title("Taxa de Emprego por Grupo Racial\nDecomposição Composicional — Saída do Emprego", fontsize=9.5)
    ax.legend(fontsize=8)

    # ── Painel D: DiD 2×2 ────────────────────────────────────────────────────
    ax = axes[1, 1]
    means = did_res["means"]
    for neg, cor, mks in [(0, "#3498db", "s"), (1, "#e74c3c", "o")]:
        sub = means[means["negro"] == neg].sort_values("post")
        ys  = sub["mean_log"].values
        xs  = [0, 1]
        lbl = "Branco" if neg == 0 else "Negro"
        ax.plot(xs, ys, marker=mks, color=cor, lw=2, ms=8, label=lbl)
        ax.errorbar(xs, ys,
                    yerr=1.96 * sub["se_log"].values,
                    fmt="none", color=cor, capsize=4)

    tau = did_res["tau"]
    pv  = did_res["pval_tau"]
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["2019 (pré-COVID)", "2020 (COVID)"])
    ax.set_ylabel("log_renda média")
    ax.set_title(
        f"DiD 2×2 — Efeito COVID no Gap Racial\n"
        f"τ_DiD = {tau:.5f}  (p = {pv:.4f})",
        fontsize=9.5,
    )
    ax.legend(fontsize=9)
    ax.text(0.5, 0.05, did_res["interpretacao"], ha="center",
            transform=ax.transAxes, fontsize=8.5,
            bbox=dict(fc="lightyellow", ec="gray", alpha=0.9))

    plt.suptitle(
        "Event Study COVID-19 — Gap Salarial Racial (PNAD Contínua 2016–2025)\n"
        "OLS Poolado × Decomposição Composicional × DiD 2×2",
        fontsize=11,
    )
    plt.tight_layout()
    fig.savefig(OUT_FIG / "event_study_covid.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: event_study_covid.png")


# ── Salvar tabelas ────────────────────────────────────────────────────────────

def _salvar_tabelas(es_res: Dict, comp_res: pd.DataFrame, did_res: Dict) -> None:
    # Event study coefficients
    es_res["df_es"].to_csv(OUT_TAB / "event_study_covid_coef.csv", index=False, encoding="utf-8")

    es_tab = es_res["df_es"][["ano", "t", "delta", "se", "pval", "ci95_lo", "ci95_hi"]].copy()
    es_tab.columns = ["Ano", "t (rel. 2019)", "δ_t", "SE", "p-valor", "IC95 lo", "IC95 hi"]
    tex = es_tab.to_latex(
        index=False, float_format="%.5f",
        caption=(
            r"Event study do gap salarial racial relativo a 2019 "
            r"($\delta_t = \hat{\beta}_{negro \times t}$). "
            r"Especificação OLS poolada com interações \textit{negro} $\times$ \texttt{C(Ano)}, "
            r"controles individuais e efeitos fixos de UF. "
            r"SEs clusterizados por UF. "
            r"$\delta_t = 0$ para 2019 (ano de referência). "
            r"Pré-tendência: hipótese $\delta_{2016}=\delta_{2017}=\delta_{2018}=0$ "
            r"testada via Wald test. PNAD Contínua 2016--2025."
        ),
        label="tab:event_study_covid",
    )
    (OUT_TAB / "event_study_covid_coef.tex").write_text(tex, encoding="utf-8")

    # Composição
    comp_out = comp_res[[
        "Ano", "gap_bruto_log", "gap_bruto_pct",
        "tx_emp_negro", "tx_emp_branco",
        "tx_form_negro", "tx_form_branco",
        "delta_emp_negro", "delta_emp_branco", "delta_gap", "marco",
    ]].copy()
    comp_out.to_csv(OUT_TAB / "event_study_composicao.csv", index=False, encoding="utf-8")

    # DiD
    did_tab = pd.DataFrame([{
        "Estimador": "DiD regressão (negro × post)",
        "τ": round(did_res["tau"], 5),
        "SE (cluster-UF)": round(did_res["se_tau"], 5),
        "p-valor": round(did_res["pval_tau"], 4),
        "τ_naive (diferença de médias)": round(did_res["tau_naive"], 5),
        "Interpretação": did_res["interpretacao"],
    }])
    did_tab.to_csv(OUT_TAB / "event_study_did.csv", index=False, encoding="utf-8")
    tex_did = did_tab.to_latex(
        index=False, escape=True,
        caption=(
            r"DiD 2$\times$2 — efeito diferencial do COVID-19 sobre o gap salarial racial. "
            r"Compara trabalhadores negros vs.\ brancos em 2019 (pré) vs.\ 2020 (COVID). "
            r"Regressão: $\log\_renda = \alpha + \beta_{negro} + \gamma_{post} + "
            r"\tau (negro \times post) + X'\theta + C(UF) + \varepsilon$. "
            r"$\tau > 0$: convergência aparente (negros sofreram menos). "
            r"$\tau < 0$: divergência (negros sofreram mais). "
            r"SEs clusterizados por UF. PNAD Contínua 2019--2020."
        ),
        label="tab:did_covid",
    )
    (OUT_TAB / "event_study_did.tex").write_text(tex_did, encoding="utf-8")


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_event_study_covid(sample_frac: Optional[float] = None) -> Dict:
    logger.info("=== Event Study COVID-19 — Gap Salarial Racial ===")

    # Carregamento
    df_emp = _load_empregados(sample_frac=sample_frac)
    df_pea = _load_pea_comp()

    # 1. Event study pooled
    es_res = estimar_event_study(df_emp)
    logger.info(
        f"Event study: β_2019 = {es_res['beta_2019']:.5f}  "
        f"| Pré-tendência p = {es_res['p_pre_trend']:.4f}"
    )

    # 2. Decomposição composicional
    logger.info("Calculando decomposição composicional...")
    comp_res = decomposicao_composicional(df_pea)

    # 3. DiD 2×2
    did_res = did_covid(df_emp)

    # Figura e tabelas
    plotar_event_study(es_res, comp_res, did_res)
    _salvar_tabelas(es_res, comp_res, did_res)

    # Sumário
    df_es   = es_res["df_es"]
    d_2020  = df_es.loc[df_es["ano"] == COVID_YEAR, "delta"].values[0]
    p_2020  = df_es.loc[df_es["ano"] == COVID_YEAR, "pval"].values[0]
    comp_20 = comp_res[comp_res["Ano"] == COVID_YEAR].iloc[0]

    print("\n── SUMÁRIO: Event Study COVID-19 ──")
    print(f"  Gap relativo em 2020 (δ_2020): {d_2020:+.5f} log-pt  (p={p_2020:.4f})")
    print(f"  Interpretação δ: gap em 2020 foi "
          f"{'MENOR' if d_2020 > 0 else 'MAIOR'} que em 2019 em {abs(d_2020)*100:.3f}pp")
    print(f"  Pré-tendência: p = {es_res['p_pre_trend']:.4f}  "
          f"({'✓ OK' if es_res['pre_trend_ok'] else '✗ Tendência pré-COVID'})")
    print(f"  DiD τ = {did_res['tau']:+.5f}  p = {did_res['pval_tau']:.4f}")
    print(f"  {did_res['interpretacao']}")
    print(f"  Composição 2020:")
    print(f"    Δtx_emprego_negro:  {comp_20['delta_emp_negro']:+.4f}")
    print(f"    Δtx_emprego_branco: {comp_20['delta_emp_branco']:+.4f}")
    print(f"    Δgap_bruto (log):   {comp_20['delta_gap']:+.5f}")

    return {
        "event_study": es_res,
        "composicao": comp_res,
        "did": did_res,
    }
