"""
analise_enem_contextual.py
==========================
HLM estendido com gap racial do ENEM como preditor contextual de Nível 3.

Modelo M3_ENEM adiciona gap_enem_uf_z ao M3 completo:

    γ_{00k} = δ_{000}
             + δ_{001}·PctNegro^{UF}_k
             + δ_{002}·TxDesemprego^{UF}_k
             + δ_{003}·MediaEduc^{UF}_k
             + δ_{004}·GapEnem^{UF}_k        ← novo preditor
             + v_{00k}

Pergunta de pesquisa:
    Estados com maior desigualdade de desempenho no ENEM entre brancos
    e negros também apresentam maior gap salarial racial, após controlar
    por características individuais e outros contextos de Nível 3?

Interpretação cautelosa (ver docstring ingestion_enem.py):
    gap_enem_uf_z NÃO é medida de discriminação de avaliadores.
    É proxy de desigualdade educacional racial acumulada ao nível estadual.
    Um coeficiente δ_{004} < 0 seria consistente com a hipótese de que
    desvantagem educacional estadual amplifica o gap salarial, mas NÃO
    prova causalidade nem isola o mecanismo de Botelho et al. (2015).

Outputs:
    outputs/tables/enem_contextual_coef.csv|.tex
    outputs/figures/enem_contextual_*.png
    MLflow: experimento "ENEM_Contextual"

Referência:
    Botelho, F., Madeira, R. A., & Rangel, M. A. (2015). Racial
    discrimination in grading: Evidence from Brazil.
    American Economic Journal: Applied Economics, 7(4), 37-52.
"""

import logging
import warnings
from pathlib import Path
from typing import Dict, Optional

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
ENEM_GAP_PATH = ROOT / "data" / "external" / "enem_gap_uf.parquet"
OUT_FIG       = ROOT / "outputs" / "figures"
OUT_TAB       = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

# Fórmula M3 base (sem ENEM) — espelho de multilevel_model.py
_IND = (
    "negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
    " + log_horas + urbano + C(Ano)"
)
_UPA = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
_UF  = "pct_negro_uf_z + tx_desemprego_uf_z + media_educ_uf_z"

FORMULA_M3      = f"log_renda ~ {_IND} + {_UPA} + {_UF}"
FORMULA_M3_ENEM = f"log_renda ~ {_IND} + {_UPA} + {_UF} + gap_enem_uf_z"

MODEL_VARS = [
    "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "log_horas", "urbano", "Ano",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "pct_negro_uf_z", "tx_desemprego_uf_z", "media_educ_uf_z",
    "UPA", "UF",
]


# ── Carregamento e merge ──────────────────────────────────────────────────────

def carregar_dados_com_enem(
    sample_frac: Optional[float] = None,
    enem_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Carrega features PNAD e faz merge com gap ENEM por UF/ano.

    O merge é feito à esquerda (left join) por UF e Ano — observações
    sem gap ENEM correspondente recebem NaN e são excluídas da análise
    M3_ENEM, mas mantidas para estimação do M3_base de comparação.
    """
    enem_path = enem_path or ENEM_GAP_PATH
    if not enem_path.exists():
        raise FileNotFoundError(
            f"Gap ENEM não encontrado em: {enem_path}\n"
            "Execute: python run_ingestion_enem.py --project tcc-racismo-pnad"
        )

    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df = df.dropna(subset=MODEL_VARS).reset_index(drop=True)

    upa_cnt = df["UPA"].value_counts()
    df = df[df["UPA"].isin(upa_cnt[upa_cnt >= 10].index)].reset_index(drop=True)
    df["UPA_str"] = df["UPA"].astype(str)
    df["UF_str"]  = df["UF"].astype(str)
    df["log_renda"] = df["log_renda"].astype(float)

    # Merge com gap ENEM — normaliza tipos antes do join
    df_enem = pd.read_parquet(enem_path)[["ano", "UF_cod", "gap_enem_z"]]
    df_enem = df_enem.rename(columns={"ano": "Ano", "UF_cod": "UF",
                                       "gap_enem_z": "gap_enem_uf_z"})
    df_enem["Ano"] = df_enem["Ano"].astype("int16")
    df_enem["UF"]  = df_enem["UF"].astype("int64")

    df["UF_merge"] = df["UF"].astype("int64")

    if "Ano" in df.columns:
        df_enem = df_enem.rename(columns={"UF": "UF_merge"})
        df = df.merge(df_enem, on=["Ano", "UF_merge"], how="left")
        df = df.drop(columns=["UF_merge"])
        n_com_enem = df["gap_enem_uf_z"].notna().sum()
        logger.info(
            f"Merge ENEM: {n_com_enem:,}/{len(df):,} obs. com gap_enem_uf_z "
            f"({n_com_enem/len(df)*100:.1f}%)"
        )
    else:
        # Sem coluna Ano: usa média do gap por UF (cross-sectional)
        gap_medio = df_enem.groupby("UF")["gap_enem_uf_z"].mean().reset_index()
        df = df.merge(gap_medio, on="UF", how="left")
        logger.warning("Coluna 'Ano' ausente — usando gap_enem médio por UF.")

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)

    logger.info(f"Dataset final: {len(df):,} obs.")
    return df


# ── Ajuste dos modelos ────────────────────────────────────────────────────────

def _ajustar_hlm(df: pd.DataFrame, formula: str,
                 label: str, method: str = "lbfgs",
                 maxiter: int = 1000) -> Optional[Dict]:
    """
    Ajusta HLM 2-nível (individual → UF) para análise ENEM contextual.

    O preditor de interesse (gap_enem_uf_z) é medido no nível UF (Nível 3
    no modelo principal). Usar um modelo 2-nível individual→UF é
    metodologicamente correto para testar preditores de UF, evitando
    o custo de memória do vc_formula com 40k dummies de UPA (17.7 GiB).
    """
    df_fit = df.dropna(subset=["gap_enem_uf_z"] if "gap_enem_uf_z" in formula else [])
    n_ufs = df_fit["UF_str"].nunique()

    if len(df_fit) < 500 or n_ufs < 3:
        logger.warning(f"{label}: amostra insuficiente.")
        return None

    logger.info(f"Ajustando {label} (n={len(df_fit):,}, UFs={n_ufs})...")
    try:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("ignore")
            model  = smf.mixedlm(
                formula, data=df_fit,
                groups=df_fit["UF_str"],
            )
            result = model.fit(method=method, maxiter=maxiter, reml=False)
    except Exception as exc:
        logger.error(f"{label} falhou: {exc}")
        return None

    b_neg  = result.params.get("negro", np.nan)
    se_neg = result.bse.get("negro", np.nan)
    pv_neg = result.pvalues.get("negro", np.nan)
    b_enem = result.params.get("gap_enem_uf_z", np.nan)
    se_enem = result.bse.get("gap_enem_uf_z", np.nan)
    pv_enem = result.pvalues.get("gap_enem_uf_z", np.nan)

    try:
        var_uf = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] > 0 else 0.0
    except Exception:
        var_uf = 0.0
    var_res = float(result.scale)
    icc_uf  = var_uf / (var_uf + var_res) if (var_uf + var_res) > 0 else 0.0

    sig = lambda p: "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
    logger.info(
        f"  {label}: β_negro={b_neg:.4f}{sig(pv_neg)} | "
        f"β_enem={b_enem:.4f}{sig(pv_enem)} | "
        f"ICC_UF={icc_uf:.3f} | AIC={result.aic:.1f}"
    )
    return {
        "label":         label,
        "n_obs":         len(df_fit),
        "n_ufs":         n_ufs,
        "beta_negro":    b_neg,
        "se_negro":      se_neg,
        "pval_negro":    pv_neg,
        "gap_pct":       (np.exp(b_neg) - 1) * 100,
        "beta_enem":     b_enem,
        "se_enem":       se_enem,
        "pval_enem":     pv_enem,
        "icc_uf":        icc_uf,
        "aic":           result.aic,
        "bic":           result.bic,
        "log_likelihood": result.llf,
        "result_obj":    result,
    }


# ── Visualizações ─────────────────────────────────────────────────────────────

def plotar_gap_enem_por_uf(df: pd.DataFrame) -> None:
    """Scatter: gap ENEM × gap salarial por UF (correlação ecológica)."""
    if "gap_enem_uf_z" not in df.columns:
        return

    # Agrega por UF: gap salarial bruto e gap ENEM
    uf_gap = df.groupby("UF_str").agg(
        gap_salarial=("log_renda", lambda x:
                      x[df.loc[x.index, "negro"] == 0].mean() -
                      x[df.loc[x.index, "negro"] == 1].mean()
                      if (df.loc[x.index, "negro"] == 1).any() else np.nan),
        gap_enem=("gap_enem_uf_z", "mean"),
    ).dropna()

    if len(uf_gap) < 5:
        return

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(uf_gap["gap_enem"], uf_gap["gap_salarial"],
               color="#2c3e50", s=60, alpha=0.8, zorder=3)
    for uf, row in uf_gap.iterrows():
        ax.annotate(str(uf), (row["gap_enem"], row["gap_salarial"]),
                    fontsize=7, ha="left", va="bottom",
                    xytext=(3, 3), textcoords="offset points")

    # Linha de tendência
    z = np.polyfit(uf_gap["gap_enem"], uf_gap["gap_salarial"], 1)
    xline = np.linspace(uf_gap["gap_enem"].min(), uf_gap["gap_enem"].max(), 100)
    ax.plot(xline, np.polyval(z, xline), color="#c0392b",
            linewidth=1.5, linestyle="--", label="Tendência OLS")

    corr = uf_gap[["gap_enem", "gap_salarial"]].corr().iloc[0, 1]
    ax.set_xlabel("Gap ENEM por UF (z-score)\n(branco − negro)", fontsize=10)
    ax.set_ylabel("Gap salarial bruto por UF\n(log-renda branco − negro)", fontsize=10)
    ax.set_title(
        f"Desigualdade Educacional × Salarial Racial por UF\n"
        f"Correlação ecológica r={corr:.3f}  ·  NÃO implica causalidade",
        fontsize=10,
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "enem_scatter_uf.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: enem_scatter_uf.png")


def plotar_comparacao_modelos(res_base: Dict, res_enem: Dict) -> None:
    """Dot-plot comparando β_negro e β_enem entre M3_base e M3_ENEM."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    for ax, (label, b, se, titulo) in zip(axes, [
        ("M3_base",  res_base["beta_negro"],  res_base["se_negro"],  "β_negro"),
        ("M3_ENEM",  res_enem["beta_negro"],  res_enem["se_negro"],  "β_negro"),
    ]):
        pass  # replotamos abaixo com ambos os modelos juntos

    # Painel esquerdo: β_negro nos dois modelos
    for ax_i, (modelos, titulo, key_b, key_se) in enumerate([
        ([res_base, res_enem], "β_negro (gap salarial racial)", "beta_negro", "se_negro"),
        ([res_enem], "β_gap_enem_uf_z (desigualdade educacional)", "beta_enem", "se_enem"),
    ]):
        ax = axes[ax_i]
        labels = [r["label"] for r in modelos]
        betas  = [r[key_b] for r in modelos]
        ses    = [r[key_se] for r in modelos]
        cores  = ["#2980b9", "#c0392b"][:len(modelos)]

        for i, (lbl, b, se, cor) in enumerate(zip(labels, betas, ses, cores)):
            ax.errorbar(b, i, xerr=1.96 * se, fmt="o",
                        color=cor, markersize=9, linewidth=2, capsize=5)
            ax.text(b + 1.96 * se + 0.001, i,
                    f"{(np.exp(b)-1)*100:.1f}%" if key_b == "beta_negro" else f"{b:.4f}",
                    va="center", fontsize=9, color=cor)

        ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel(titulo + " · IC 95%", fontsize=9)

    plt.suptitle("Comparação M3_base × M3_ENEM — HLM 3 Níveis", fontsize=11)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "enem_comparacao_modelos.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: enem_comparacao_modelos.png")


# ── LaTeX ─────────────────────────────────────────────────────────────────────

def _gerar_latex(res_base: Dict, res_enem: Dict) -> None:
    """Tabela comparativa M3_base × M3_ENEM para o TCC."""
    sig = lambda p: ("$^{***}$" if p < 0.001 else
                     "$^{**}$"  if p < 0.01  else
                     "$^{*}$"   if p < 0.05  else "")

    rows = []
    for res in [res_base, res_enem]:
        rows.append({
            "Modelo":               res["label"],
            "$\\beta_{negro}$":     f"{res['beta_negro']:.4f}{sig(res['pval_negro'])}",
            "SE ($\\beta_{negro}$)": f"({res['se_negro']:.4f})",
            "Gap (\\%)":            f"{res['gap_pct']:.1f}",
            "$\\beta_{GapEnem}$":   (f"{res['beta_enem']:.4f}{sig(res['pval_enem'])}"
                                     if not np.isnan(res.get("beta_enem", np.nan)) else "—"),
            "ICC\\_UF":             f"{res['icc_uf']:.3f}",
            "AIC":                  f"{res['aic']:.1f}",
            "N":                    f"{res['n_obs']:,}",
        })

    tex = pd.DataFrame(rows).to_latex(
        index=False, escape=False,
        caption=(
            "Comparação entre M3 completo e M3 com gap educacional racial do ENEM "
            "como preditor contextual de Nível 3. "
            "$\\beta_{GapEnem}$ positivo indicaria que estados com maior desigualdade "
            "educacional apresentam maior gap salarial racial. "
            "*** p$<$0,001; ** p$<$0,01; * p$<$0,05. "
            "Nota: $\\beta_{GapEnem}$ não deve ser interpretado como efeito causal "
            "da discriminação de avaliadores (Botelho et al., 2015), mas como "
            "correlação entre desigualdade educacional e salarial ao nível estadual."
        ),
        label="tab:enem_contextual",
    )
    path = OUT_TAB / "enem_contextual_coef.tex"
    path.write_text(tex, encoding="utf-8")
    logger.info("LaTeX: enem_contextual_coef.tex")


# ── Pipeline principal ─────────────────────────────────────────────────────────

def run_analise_enem_contextual(
    sample_frac: Optional[float] = None,
    enem_path: Optional[Path] = None,
) -> Dict:
    """
    Estima M3_base e M3_ENEM e compara via LRT e visualizações.

    Returns
    -------
    dict com 'M3_base', 'M3_ENEM', 'lrt'
    """
    df = carregar_dados_com_enem(sample_frac=sample_frac, enem_path=enem_path)

    with run_context("pipeline_enem_contextual", "ENEM_Contextual",
                     tags={"sample_frac": str(sample_frac or "completo"),
                           "n_obs": str(len(df))}):
        log_params({"sample_frac": sample_frac, "n_obs": len(df)})

        # M3 base (sem ENEM) — referência para LRT
        res_base = _ajustar_hlm(df, FORMULA_M3, "M3_base")
        # M3 com gap ENEM (apenas obs com gap_enem_uf_z disponível)
        res_enem = _ajustar_hlm(df, FORMULA_M3_ENEM, "M3_ENEM")

        if res_base is None or res_enem is None:
            logger.error("Um dos modelos falhou — abortando análise.")
            return {}

        # LRT: M3_base vs M3_ENEM (1 parâmetro adicional)
        from scipy import stats as scipy_stats
        lr_stat = 2 * (res_enem["log_likelihood"] - res_base["log_likelihood"])
        p_lrt   = scipy_stats.chi2.sf(lr_stat, df=1)
        lrt = {"LR": lr_stat, "df": 1, "p_valor": p_lrt,
               "significativo": "Sim" if p_lrt < 0.05 else "Não"}

        logger.info(
            f"LRT M3_base → M3_ENEM: LR={lr_stat:.3f}  p={p_lrt:.4f}  "
            f"({'significativo' if p_lrt < 0.05 else 'não significativo'})"
        )

        log_metrics({
            "beta_negro_M3_base":   res_base["beta_negro"],
            "beta_negro_M3_ENEM":   res_enem["beta_negro"],
            "beta_enem":            res_enem["beta_enem"],
            "pval_enem":            res_enem["pval_enem"],
            "lrt_LR":               lr_stat,
            "lrt_pval":             p_lrt,
            "delta_aic":            res_enem["aic"] - res_base["aic"],
        })
        set_tag("lrt_significativo", lrt["significativo"])

        # Outputs
        pd.DataFrame([
            {k: v for k, v in res_base.items() if k != "result_obj"},
            {k: v for k, v in res_enem.items() if k != "result_obj"},
        ]).to_csv(OUT_TAB / "enem_contextual_coef.csv", index=False)
        pd.DataFrame([lrt]).to_csv(OUT_TAB / "enem_lrt.csv", index=False)

        _gerar_latex(res_base, res_enem)
        plotar_gap_enem_por_uf(df)
        plotar_comparacao_modelos(res_base, res_enem)

        log_artifacts_dir(OUT_TAB, subfolder="tables")
        log_artifacts_dir(OUT_FIG, subfolder="figures")

    print("\n── SUMÁRIO: Análise ENEM Contextual ──")
    print(f"  M3_base  β_negro = {res_base['beta_negro']:+.4f}  "
          f"gap={res_base['gap_pct']:+.1f}%")
    print(f"  M3_ENEM  β_negro = {res_enem['beta_negro']:+.4f}  "
          f"gap={res_enem['gap_pct']:+.1f}%")
    print(f"  β_gap_enem = {res_enem['beta_enem']:+.4f}  "
          f"p={res_enem['pval_enem']:.4f}")
    print(f"  LRT: LR={lr_stat:.3f}  p={p_lrt:.4f}  → {lrt['significativo']}")
    print(f"\n  Atenção: β_gap_enem reflete correlação ecológica (UF), "
          f"não causalidade individual.")

    return {"M3_base": res_base, "M3_ENEM": res_enem, "lrt": lrt}
