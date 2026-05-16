"""
analise_regional.py
===================
Heterogeneidade espacial do gap salarial racial por macrorregião brasileira.

Para cada uma das 5 macrorregiões:
    1. HLM (indivíduo → UF como RE, contexto UPA como slopes fixos)
       → extrai β_negro, ICC_UF e componentes de variância por região
    2. Regressão quantílica (τ = 0.10, 0.25, 0.50, 0.75, 0.90)
       → perfil do gap ao longo da distribuição de renda

Hipóteses testadas:
    H1: β_negro varia significativamente entre regiões (heterogeneidade espacial)
    H2: glass ceiling (gap maior no topo) predomina no Sudeste/Sul (mais formal)
    H3: sticky floor (gap maior na base) predomina no Nordeste/Norte
        — discriminação na entrada do mercado formal

Referências:
    Darity & Mason (1998). Evidence on discrimination in employment.
        Journal of Economic Perspectives, 12(2), 63-90.
    Koenker & Bassett (1978). Regression quantiles. Econometrica, 46(1), 33-50.
    Raudenbush & Bryk (2002). Hierarchical Linear Models (2nd ed.). Sage.
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

from mlflow_utils import (
    log_artifacts_dir, log_metrics, log_params, run_context, set_tag,
)

logger = logging.getLogger(__name__)

ROOT          = Path(__file__).parent.parent
FEATURES_PATH = ROOT / "data" / "processed" / "features.parquet"
OUT_FIG       = ROOT / "outputs" / "figures"
OUT_TAB       = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

# Códigos IBGE: UF → macrorregião
REGIOES: Dict[str, List[int]] = {
    "Norte":        [11, 12, 13, 14, 15, 16, 17],
    "Nordeste":     [21, 22, 23, 24, 25, 26, 27, 28, 29],
    "Sudeste":      [31, 32, 33, 35],
    "Sul":          [41, 42, 43],
    "Centro-Oeste": [50, 51, 52, 53],
}
QUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]

# Fórmula base — consistent com multilevel_model.py
_IND = (
    "negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
    " + log_horas + urbano + C(Ano)"
)
_CTX = " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
FORMULA_HLM = f"log_renda ~ {_IND}{_CTX}"
FORMULA_QR  = f"log_renda ~ {_IND}"

MODEL_VARS = [
    "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "log_horas", "urbano", "Ano",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "UPA", "UF",
]


# ── Carregamento ──────────────────────────────────────────────────────────────

def carregar_dados(sample_frac: Optional[float] = None) -> pd.DataFrame:
    """Carrega features.parquet, aplica filtros e adiciona coluna 'regiao'."""
    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    # Fallback: recria colunas ausentes se features.parquet foi gerado antes
    if "log_horas" not in df.columns and "horas_trabalhadas" in df.columns:
        df["log_horas"] = np.log(df["horas_trabalhadas"].clip(lower=1))
    if "urbano" not in df.columns:
        df["urbano"] = (df["V1022"] == 1).astype("int8") if "V1022" in df.columns else 1
    df = df.dropna(subset=MODEL_VARS).reset_index(drop=True)

    # Filtra UPAs com n mínimo para estimação estável (Raudenbush & Bryk, cap. 4)
    upa_cnt = df["UPA"].value_counts()
    df = df[df["UPA"].isin(upa_cnt[upa_cnt >= 10].index)].reset_index(drop=True)

    df["UPA_str"] = df["UPA"].astype(str)
    df["UF_str"]  = df["UF"].astype(str)
    df["log_renda"] = df["log_renda"].astype(float)

    # Cria coluna de macrorregião
    uf_int = df["UF"].astype(int)
    df["regiao"] = "Outra"
    for nome, ufs in REGIOES.items():
        df.loc[uf_int.isin(ufs), "regiao"] = nome

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)

    logger.info(
        f"Dataset: {len(df):,} obs. | "
        + " | ".join(f"{r}:{(df['regiao']==r).sum():,}" for r in REGIOES)
    )
    return df


# ── HLM por região ────────────────────────────────────────────────────────────

def ajustar_hlm_regional(df: pd.DataFrame, nome_regiao: str) -> Optional[Dict]:
    """
    Ajusta HLM para uma região: RE por UF, slopes fixos de contexto UPA.

    Segue o mesmo padrão de run_hlm_serie_completa.py (REML + Powell)
    para consistência com os modelos da série completa do TCC.

    Returns dict com β_negro, SE, ICC_UF e métricas de ajuste, ou None.
    """
    df_r = df[df["regiao"] == nome_regiao].copy()
    n_ufs = df_r["UF"].nunique()

    if len(df_r) < 1000 or n_ufs < 2:
        logger.warning(f"{nome_regiao}: n={len(df_r):,}, UFs={n_ufs} — insuficiente.")
        return None

    logger.info(f"Ajustando HLM — {nome_regiao} (n={len(df_r):,}, UFs={n_ufs})")
    try:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            model  = smf.mixedlm(FORMULA_HLM, data=df_r, groups=df_r["UF_str"])
            result = model.fit(method="powell", maxiter=500, reml=True)
    except Exception as exc:
        logger.error(f"{nome_regiao} — falha no HLM: {exc}")
        return None

    # Componentes de variância
    try:
        var_uf = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] > 0 else 0.0
    except (IndexError, AttributeError):
        var_uf = 0.0
    var_res  = float(result.scale)
    total    = var_uf + var_res
    icc_uf   = var_uf / total if total > 0 else 0.0

    b  = result.params.get("negro", np.nan)
    se = result.bse.get("negro", np.nan)
    pv = result.pvalues.get("negro", np.nan)
    stars = "***" if pv < 0.001 else "**" if pv < 0.01 else "*" if pv < 0.05 else "ns"

    logger.info(
        f"  {nome_regiao}: beta_negro={b:.4f}{stars}  ICC_UF={icc_uf:.3f}  "
        f"gap={(np.exp(b)-1)*100:.1f}%"
    )
    row = {
        "regiao":     nome_regiao,
        "n_obs":      len(df_r),
        "n_ufs":      n_ufs,
        "beta_negro": b,
        "se_negro":   se,
        "pval":       pv,
        "gap_pct":    (np.exp(b) - 1) * 100,
        "icc_uf":     icc_uf,
        "var_uf":     var_uf,
        "var_res":    var_res,
        "aic":        result.aic,
    }
    with run_context(f"HLM_{nome_regiao}", "Analise_Regional", nested=True):
        log_params({
            "regiao": nome_regiao, "method": "powell",
            "maxiter": 500, "reml": True,
            "n_obs": len(df_r), "n_ufs": n_ufs,
        })
        log_metrics({
            "beta_negro": b, "se_negro": se, "pval_negro": pv,
            "gap_pct": row["gap_pct"], "icc_uf": icc_uf,
            "var_uf": var_uf, "var_res": var_res, "aic": result.aic,
        })
    return row


def tabela_hlm_regional(resultados: List[Dict]) -> pd.DataFrame:
    """Formata resultados dos HLMs regionais em tabela para LaTeX."""
    df = pd.DataFrame(resultados)
    df["stars"] = df["pval"].apply(
        lambda p: "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    )
    df["celula"] = (
        df["beta_negro"].round(4).astype(str)
        + df["stars"]
        + "\n(" + df["se_negro"].round(4).astype(str) + ")"
    )
    return df


# ── Regressão quantílica por região ──────────────────────────────────────────

def ajustar_quantilica_regional(
    df: pd.DataFrame,
    nome_regiao: str,
    quantiles: List[float] = QUANTILES,
) -> pd.DataFrame:
    """
    Regressão quantílica para mapear o gap racial ao longo da distribuição.

    Gap crescente do τ=0.10 para τ=0.90 → glass ceiling (barreiras no topo).
    Gap decrescente → sticky floor (discriminação na entrada do mercado formal).
    Gap constante   → discriminação uniforme em toda a distribuição.
    """
    df_r = df[df["regiao"] == nome_regiao].copy()
    if len(df_r) < 500:
        return pd.DataFrame()

    rows = []
    for q in quantiles:
        try:
            res  = smf.quantreg(FORMULA_QR, data=df_r).fit(q=q, max_iter=2000)
            b    = res.params.get("negro", np.nan)
            ci   = res.conf_int()
            ci_l = ci.loc["negro", 0] if "negro" in ci.index else np.nan
            ci_h = ci.loc["negro", 1] if "negro" in ci.index else np.nan
            row_q = {
                "regiao":     nome_regiao,
                "quantil":    q,
                "beta_negro": b,
                "ci_low":     ci_l,
                "ci_high":    ci_h,
                "gap_pct":    (np.exp(b) - 1) * 100,
            }
            rows.append(row_q)
            with run_context(f"QR_{nome_regiao}_q{int(q*100)}", "Analise_Regional",
                             nested=True):
                log_params({"regiao": nome_regiao, "quantil": q, "max_iter": 2000})
                log_metrics({
                    "beta_negro": b, "ci_low": ci_l,
                    "ci_high": ci_h, "gap_pct": row_q["gap_pct"],
                })
        except Exception as exc:
            logger.warning(f"  QuantReg {nome_regiao} τ={q:.2f}: {exc}")
    return pd.DataFrame(rows)


# ── Visualizações ─────────────────────────────────────────────────────────────

def plotar_coeficientes_regionais(tabela: pd.DataFrame) -> None:
    """Barras horizontais com IC95% do β_negro por macrorregião."""
    df = tabela.dropna(subset=["beta_negro"]).copy()
    df["ic95_l"] = df["beta_negro"] - 1.96 * df["se_negro"]
    df["ic95_h"] = df["beta_negro"] + 1.96 * df["se_negro"]
    df = df.sort_values("beta_negro")

    cores = ["#c0392b" if p < 0.05 else "#95a5a6" for p in df["pval"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(
        df["regiao"], df["beta_negro"],
        xerr=[df["beta_negro"] - df["ic95_l"], df["ic95_h"] - df["beta_negro"]],
        color=cores, edgecolor="black", linewidth=0.5, capsize=4,
    )
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    for _, row in df.iterrows():
        ax.text(
            row["beta_negro"] - 0.002, row["regiao"],
            f"{row['gap_pct']:+.1f}%",
            ha="right", va="center", fontsize=9,
        )
    ax.set_xlabel("β_negro (log-renda)", fontsize=11)
    ax.set_title(
        "Gap Salarial Racial por Macrorregião — HLM\n"
        "Vermelho = p<0,05  ·  Barras = IC 95%",
        fontsize=11,
    )
    plt.tight_layout()
    fig.savefig(OUT_FIG / "regional_coef_negro.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: regional_coef_negro.png")


def plotar_perfil_quantilico(df_qr: pd.DataFrame) -> None:
    """Perfil do gap racial por quantil de renda, separado por região."""
    regioes = [r for r in REGIOES if r in df_qr["regiao"].values]
    cores   = plt.cm.Set2(np.linspace(0, 1, len(regioes)))

    fig, ax = plt.subplots(figsize=(9, 5))
    for regiao, cor in zip(regioes, cores):
        sub = df_qr[df_qr["regiao"] == regiao].sort_values("quantil")
        if sub.empty:
            continue
        ax.plot(sub["quantil"], sub["beta_negro"],
                marker="o", color=cor, label=regiao, linewidth=2)
        ax.fill_between(sub["quantil"], sub["ci_low"], sub["ci_high"],
                        color=cor, alpha=0.12)

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Quantil de renda", fontsize=11)
    ax.set_ylabel("β_negro (regressão quantílica)", fontsize=11)
    ax.set_title(
        "Perfil do Gap Racial por Quantil e Macrorregião\n"
        "Faixa sombreada = IC 95%",
        fontsize=11,
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "regional_perfil_quantilico.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: regional_perfil_quantilico.png")


def plotar_icc_regional(tabela: pd.DataFrame) -> None:
    """Gráfico de barras do ICC_UF por região — variância explicada pelo estado."""
    df = tabela.dropna(subset=["icc_uf"]).sort_values("icc_uf", ascending=False)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(df["regiao"], df["icc_uf"] * 100, color="#2980b9", edgecolor="black", linewidth=0.5)
    ax.axhline(5, color="red", linewidth=1, linestyle="--", label="Limiar 5% (R&B, 2002)")
    ax.set_ylabel("ICC_UF (%)", fontsize=11)
    ax.set_title("Variância de Log-Renda Atribuível ao Estado (ICC_UF)\npor Macrorregião — HLM", fontsize=11)
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "regional_icc.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: regional_icc.png")


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_analise_regional(sample_frac: Optional[float] = None) -> Dict:
    """
    Executa análise de heterogeneidade regional completa.

    Args:
        sample_frac: Fração da amostra (None = dados completos).

    Returns:
        dict com 'hlm' (DataFrame de resultados HLM) e 'qr' (DataFrame QR).
    """
    df = carregar_dados(sample_frac=sample_frac)

    with run_context("pipeline_regional", "Analise_Regional",
                     tags={"sample_frac": str(sample_frac or "completo"),
                           "n_obs": str(len(df))}):
        log_params({"sample_frac": sample_frac, "n_obs": len(df),
                    "n_regioes": len(REGIOES), "quantiles": str(QUANTILES)})

        # ── HLM por região ────────────────────────────────────────────────
        rows_hlm = []
        for regiao in REGIOES:
            res = ajustar_hlm_regional(df, regiao)
            if res:
                rows_hlm.append(res)

        hlm_tab = pd.DataFrame(rows_hlm)
        hlm_tab.to_csv(OUT_TAB / "regional_hlm.csv", index=False)

        latex = (
            hlm_tab[["regiao", "n_obs", "n_ufs", "beta_negro", "se_negro",
                     "pval", "gap_pct", "icc_uf"]]
            .rename(columns={
                "regiao": "Região", "n_obs": "N", "n_ufs": "UFs",
                "beta_negro": "β_negro", "se_negro": "SE",
                "pval": "p-valor", "gap_pct": "Gap (%)", "icc_uf": "ICC_UF",
            })
            .to_latex(
                index=False, float_format="%.4f",
                caption=(
                    "Modelos HLM por Macrorregião — Gap Salarial Racial (β_negro) "
                    "com RE por UF. PNAD Contínua. "
                    "*** p<0,001; ** p<0,01; * p<0,05."
                ),
                label="tab:regional_hlm",
            )
        )
        (OUT_TAB / "regional_hlm.tex").write_text(latex, encoding="utf-8")
        plotar_coeficientes_regionais(hlm_tab)
        plotar_icc_regional(hlm_tab)

        # ── Regressão quantílica por região ──────────────────────────────
        qr_frames = [ajustar_quantilica_regional(df, r) for r in REGIOES]
        qr_tab = pd.concat([f for f in qr_frames if not f.empty], ignore_index=True)
        qr_tab.to_csv(OUT_TAB / "regional_qr.csv", index=False)
        plotar_perfil_quantilico(qr_tab)

        # Métricas resumo na run pai
        if not hlm_tab.empty:
            maior_gap = hlm_tab.loc[hlm_tab["beta_negro"].idxmin(), "regiao"]
            menor_gap = hlm_tab.loc[hlm_tab["beta_negro"].idxmax(), "regiao"]
            log_metrics({
                "beta_negro_min": hlm_tab["beta_negro"].min(),
                "beta_negro_max": hlm_tab["beta_negro"].max(),
                "gap_pct_min":    hlm_tab["gap_pct"].min(),
                "gap_pct_max":    hlm_tab["gap_pct"].max(),
                "icc_uf_max":     hlm_tab["icc_uf"].max(),
            })
            set_tag("maior_gap_regiao", maior_gap)
            set_tag("menor_gap_regiao", menor_gap)
            log_artifacts_dir(OUT_TAB, subfolder="tables")
            log_artifacts_dir(OUT_FIG, subfolder="figures")

        # ── Sumário narrativo ─────────────────────────────────────────────
        if not hlm_tab.empty:
            print("\n--- SUMARIO: Analise Regional ---")
            print(hlm_tab[["regiao", "beta_negro", "gap_pct", "icc_uf", "pval"]]
                  .to_string(index=False))
            print(f"\nMaior gap racial: {maior_gap}")
            print(f"Menor gap racial: {menor_gap}")

    return {"hlm": hlm_tab, "qr": qr_tab}
