"""
tendencia_temporal.py
=====================
Teste formal de tendência no coeficiente β_negro ao longo de 2016–2025.

Métodos implementados:
  1. WLS (pesos = 1/SE²): slope β_negro ~ ano_c — pergunta: o gap está convergindo?
  2. Chow test com quebra estrutural em 2020 (COVID-19)
  3. Teste Mann-Kendall (não-paramétrico, robusto a autocorrelação em n pequeno)
  4. AR(1) para verificar autocorrelação nos resíduos da tendência

Todos os testes operam sobre os estimados anuais já disponíveis em
outputs/tables/validacao_temporal.csv — sem re-estimar HLMs.

Referências:
    Chow, G. C. (1960). Tests of equality between sets of coefficients in
        two linear regressions. Econometrica, 28(3), 591–605.
    Mann, H. B. (1945). Nonparametric tests against trend. Econometrica,
        13(3), 245–259.
    Kendall, M. G. (1955). Rank Correlation Methods. Charles Griffin.
"""

import logging
import warnings
from pathlib import Path
from typing import Dict, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

logger = logging.getLogger(__name__)

ROOT    = Path(__file__).parent.parent
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

TEMPORAL_CSV = OUT_TAB / "validacao_temporal.csv"
COVID_YEAR   = 2020
BASE_YEAR    = 2019


# ── Carregamento ──────────────────────────────────────────────────────────────

def _load_series() -> pd.DataFrame:
    df = pd.read_csv(TEMPORAL_CSV)
    df = df.rename(columns={"label": "ano", "beta_negro": "beta", "se_negro": "se"})
    df["ano"]   = df["ano"].astype(int)
    df["ano_c"] = df["ano"] - BASE_YEAR          # centralizado em 2019
    df["peso"]  = 1.0 / df["se"] ** 2            # inverse-variance weights
    df["gap_pct"] = (np.exp(df["beta"]) - 1) * 100
    df["ci95_lo"] = df["beta"] - 1.96 * df["se"]
    df["ci95_hi"] = df["beta"] + 1.96 * df["se"]
    return df.sort_values("ano").reset_index(drop=True)


# ── WLS Tendência Global ───────────────────────────────────────────────────────

def wls_tendencia(df: pd.DataFrame) -> Dict:
    """
    WLS:  β_negro = α + δ·ano_c + ε,  pesos = 1/SE²

    δ < 0 → gap diminuindo (convergência)
    δ > 0 → gap aumentando (divergência)
    δ = 0 (p > 0.05) → gap estruturalmente estável

    A ponderação por 1/SE² dá mais influência aos anos com estimativas
    mais precisas (N maior), corrigindo heteroscedasticidade que seria
    ignorada por OLS simples nos 10 pontos anuais.
    """
    model = smf.wls("beta ~ ano_c", data=df, weights=df["peso"])
    res   = model.fit()

    slope    = res.params["ano_c"]
    slope_se = res.bse["ano_c"]
    pval     = res.pvalues["ano_c"]
    ci_lo    = res.conf_int().loc["ano_c", 0]
    ci_hi    = res.conf_int().loc["ano_c", 1]

    # Projeções para 2016 e 2025
    pred_2016 = res.predict(pd.DataFrame({"ano_c": [2016 - BASE_YEAR]})).iloc[0]
    pred_2025 = res.predict(pd.DataFrame({"ano_c": [2025 - BASE_YEAR]})).iloc[0]
    slope_pct = ((np.exp(pred_2025) - 1) - (np.exp(pred_2016) - 1)) * 100

    return {
        "slope_log": round(slope, 6),
        "slope_se":  round(slope_se, 6),
        "slope_pct_por_ano": round(slope * 100, 4),   # em pontos percentuais
        "slope_total_2016_2025_pct": round(slope_pct, 2),
        "pvalor":    round(pval, 4),
        "ci95_lo":   round(ci_lo, 6),
        "ci95_hi":   round(ci_hi, 6),
        "r2_wls":    round(res.rsquared, 4),
        "resultado": model.fit(),
    }


# ── Chow Test — Quebra Estrutural em 2020 ────────────────────────────────────

def chow_test(df: pd.DataFrame, break_year: int = COVID_YEAR) -> Dict:
    """
    Chow test para quebra estrutural no coeficiente β_negro em break_year.

    H₀: α_pré = α_pós  e  δ_pré = δ_pós  (sem quebra)
    H₁: pelo menos um parâmetro muda em break_year

    Estatística F:
        F = [(RSS_pool − RSS_pré − RSS_pós) / k] / [(RSS_pré + RSS_pós) / (n − 2k)]

    onde k = 2 (intercepto + slope) e n = total de observações.

    Interpretação do Chow no contexto do COVID:
        Rejeição → a relação temporal do gap mudou estruturalmente em 2020.
        Pode refletir: mudança na composição dos trabalhadores (canal de seleção),
        ajuste de política salarial, ou choques diferenciados por setor.
    """
    pre  = df[df["ano"] < break_year].copy()
    post = df[df["ano"] >= break_year].copy()

    def _rss(sub: pd.DataFrame) -> float:
        if len(sub) < 3:
            return np.nan
        r = smf.wls("beta ~ ano_c", data=sub, weights=sub["peso"]).fit()
        return float(np.sum(r.wresid ** 2))

    rss_pool = float(np.sum(smf.wls("beta ~ ano_c", data=df,   weights=df["peso"]).fit().wresid ** 2))
    rss_pre  = _rss(pre)
    rss_post = _rss(post)

    k  = 2                              # intercepto + slope
    n  = len(df)
    df_num = k
    df_den = n - 2 * k

    if np.isnan(rss_pre) or np.isnan(rss_post) or df_den <= 0:
        logger.warning("Chow test: graus de liberdade insuficientes.")
        return {"F": np.nan, "pvalor": np.nan, "break_year": break_year}

    F    = ((rss_pool - rss_pre - rss_post) / df_num) / ((rss_pre + rss_post) / df_den)
    pval = 1 - stats.f.cdf(F, df_num, df_den)

    # Slopes separados
    res_pre  = smf.wls("beta ~ ano_c", data=pre,  weights=pre["peso"]).fit()
    res_post = smf.wls("beta ~ ano_c", data=post, weights=post["peso"]).fit()

    return {
        "break_year":       break_year,
        "F":                round(F, 3),
        "pvalor":           round(pval, 4),
        "df_num":           df_num,
        "df_den":           df_den,
        "slope_pre":        round(res_pre.params.get("ano_c", np.nan), 6),
        "slope_post":       round(res_post.params.get("ano_c", np.nan), 6),
        "intercepto_pre":   round(res_pre.params["Intercept"], 6),
        "intercepto_post":  round(res_post.params["Intercept"], 6),
        "rejeita_H0_5pct":  pval < 0.05,
    }


# ── Teste de Mann-Kendall ─────────────────────────────────────────────────────

def mann_kendall(series: pd.Series) -> Dict:
    """
    Teste de Mann-Kendall para tendência monotônica (não-paramétrico).

    Mais robusto que WLS para n pequeno (n=10) com possível autocorrelação.
    Não assume normalidade dos resíduos.

    τ de Kendall: mede direção e força da tendência
        τ > 0 → tendência crescente
        τ < 0 → tendência decrescente
        |τ| → força da tendência
    """
    x = np.array(series)
    n = len(x)
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = x[j] - x[i]
            if diff > 0:
                s += 1
            elif diff < 0:
                s -= 1

    # Variância de S sob H₀
    var_s = n * (n - 1) * (2 * n + 5) / 18
    if var_s == 0:
        z = 0.0
    elif s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    pval = 2 * (1 - stats.norm.cdf(abs(z)))
    tau  = s / (n * (n - 1) / 2)

    return {
        "S":             s,
        "z":             round(z, 4),
        "tau_kendall":   round(tau, 4),
        "pvalor":        round(pval, 4),
        "tendencia":     "decrescente" if tau < 0 else ("crescente" if tau > 0 else "nula"),
        "rejeita_H0_5pct": pval < 0.05,
    }


# ── AR(1) — Autocorrelação nos Resíduos ───────────────────────────────────────

def teste_ar1(df: pd.DataFrame, res_wls) -> Dict:
    """
    Durbin-Watson e AR(1) nos resíduos da tendência WLS.

    dw < 1.5 → autocorrelação positiva nos resíduos.
    Se autocorrelação significativa → os t-test WLS precisam de HAC SEs.
    """
    resid = res_wls.resid.values
    dw    = float(np.sum(np.diff(resid) ** 2) / np.sum(resid ** 2))

    # AR(1) manual: regressão de resid_t sobre resid_{t-1}
    y_ar  = resid[1:]
    x_ar  = resid[:-1]
    rho   = np.corrcoef(y_ar, x_ar)[0, 1]
    n_ar  = len(y_ar)
    t_rho = rho * np.sqrt(n_ar - 2) / np.sqrt(1 - rho ** 2) if abs(rho) < 1 else 0
    p_rho = 2 * (1 - stats.t.cdf(abs(t_rho), df=n_ar - 2))

    return {
        "durbin_watson": round(dw, 4),
        "rho_ar1":       round(rho, 4),
        "t_rho":         round(t_rho, 4),
        "pvalor_rho":    round(p_rho, 4),
        "autocorr_sig":  p_rho < 0.05,
    }


# ── Figura ────────────────────────────────────────────────────────────────────

def plotar_tendencia(
    df: pd.DataFrame,
    wls_res: Dict,
    chow_res: Dict,
    mk_res: Dict,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # ── Painel 1: β_negro por ano com tendência WLS ───────────────────────────
    ax = axes[0]
    anos    = df["ano"].values
    beta    = df["beta"].values
    ci_lo   = df["ci95_lo"].values
    ci_hi   = df["ci95_hi"].values
    gap_pct = df["gap_pct"].values

    # Fundo COVID
    ax.axvspan(COVID_YEAR - 0.4, COVID_YEAR + 0.4, alpha=0.12,
               color="#e74c3c", label="Ano COVID-19 (2020)")
    ax.axvspan(COVID_YEAR + 0.4, COVID_YEAR + 2.4, alpha=0.06,
               color="#e67e22", label="Recuperação (2021-22)")

    # IC 95%
    ax.fill_between(anos, ci_lo, ci_hi, alpha=0.2, color="#3498db")

    # Série observada
    ax.plot(anos, beta, "o-", color="#2c3e50", lw=2, ms=7, zorder=5,
            label="β_negro (HLM anual)")

    # Linha de tendência WLS
    ano_seq   = np.linspace(anos.min(), anos.max(), 100)
    ano_c_seq = ano_seq - BASE_YEAR
    r = wls_res["resultado"]
    pred_seq = r.predict(pd.DataFrame({"ano_c": ano_c_seq}))
    lbl_slope = (
        f"WLS: δ = {wls_res['slope_log']:.5f}/ano "
        f"(p = {wls_res['pvalor']:.3f})"
    )
    line_style = "-" if wls_res["pvalor"] < 0.05 else "--"
    ax.plot(ano_seq, pred_seq, line_style, color="#e74c3c", lw=1.8, label=lbl_slope)

    # Anotação Mann-Kendall
    mk_txt = (
        f"Mann-Kendall τ = {mk_res['tau_kendall']:.3f}  "
        f"(p = {mk_res['pvalor']:.3f})"
    )
    ax.text(0.02, 0.04, mk_txt, transform=ax.transAxes, fontsize=8.5,
            color="#555", bbox=dict(fc="white", ec="gray", alpha=0.8, pad=3))

    ax.set_xlabel("Ano")
    ax.set_ylabel("β_negro (log-pontos)")
    ax.set_title(
        "Tendência Temporal do Gap Salarial Racial\n"
        "Coeficiente HLM Anual — PNAD Contínua 2016–2025",
        fontsize=10,
    )
    ax.legend(fontsize=8, loc="upper right")
    ax.set_xticks(anos)
    ax.set_xticklabels(anos, rotation=45)

    # Eixo secundário (%)
    ax2 = ax.twinx()
    ax2.set_ylim(
        (np.exp(ax.get_ylim()[0]) - 1) * 100,
        (np.exp(ax.get_ylim()[1]) - 1) * 100,
    )
    ax2.set_ylabel("Gap salarial (%)", color="#7f8c8d")
    ax2.tick_params(axis="y", labelcolor="#7f8c8d")

    # ── Painel 2: slopes pré vs pós COVID ────────────────────────────────────
    ax2p = axes[1]
    periods = ["2016–2019\n(pré-COVID)", "2020–2025\n(pós-COVID)"]
    slopes  = [chow_res["slope_pre"], chow_res["slope_post"]]
    colors  = ["#27ae60" if s < 0 else "#e74c3c" for s in slopes]
    bars = ax2p.bar(periods, slopes, color=colors, alpha=0.8, edgecolor="black", linewidth=0.7)
    ax2p.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax2p.set_ylabel("Slope WLS (log-pontos / ano)")
    chow_txt = (
        f"Chow test: F = {chow_res['F']:.3f}  "
        f"(p = {chow_res['pvalor']:.3f})\n"
        f"{'Quebra estrutural detectada' if chow_res['rejeita_H0_5pct'] else 'Sem evidência de quebra estrutural'} "
        f"em {chow_res['break_year']}"
    )
    ax2p.set_title(
        "Chow Test — Quebra Estrutural (2020)\n"
        "Slopes WLS Pré vs Pós COVID-19",
        fontsize=10,
    )
    ax2p.text(0.03, 0.92, chow_txt, transform=ax2p.transAxes, fontsize=8.5,
              va="top", bbox=dict(fc="white", ec="gray", alpha=0.85, pad=4))
    for bar, sl in zip(bars, slopes):
        ax2p.text(bar.get_x() + bar.get_width() / 2, sl + 0.00001,
                  f"{sl:.6f}", ha="center", va="bottom" if sl >= 0 else "top",
                  fontsize=9, fontweight="bold")

    patch_conv = mpatches.Patch(color="#27ae60", alpha=0.8, label="Convergência (slope < 0)")
    patch_div  = mpatches.Patch(color="#e74c3c", alpha=0.8, label="Divergência (slope > 0)")
    ax2p.legend(handles=[patch_conv, patch_div], fontsize=8)

    plt.suptitle(
        "Teste Formal de Tendência — Gap Salarial Racial (β_negro)\n"
        "WLS Ponderado × Chow × Mann-Kendall — PNAD Contínua 2016–2025",
        fontsize=11,
    )
    plt.tight_layout()
    fig.savefig(OUT_FIG / "tendencia_temporal.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: tendencia_temporal.png")


# ── Saída LaTeX ───────────────────────────────────────────────────────────────

def _salvar_tabela_wls(wls_res: Dict, chow_res: Dict, mk_res: Dict, ar1_res: Dict) -> pd.DataFrame:
    rows = [
        {"Teste": "WLS (Ponderado por 1/SE²)",
         "Estatística": f"δ = {wls_res['slope_log']:.6f} log-pt/ano",
         "IC 95%": f"[{wls_res['ci95_lo']:.6f}, {wls_res['ci95_hi']:.6f}]",
         "p-valor": f"{wls_res['pvalor']:.4f}",
         "Conclusão": "Gap estável (p>0.05)" if wls_res["pvalor"] >= 0.05 else f"Slope significativo ({wls_res['slope_total_2016_2025_pct']:+.1f}pp em 10 anos)"},
        {"Teste": "Chow (quebra 2020)",
         "Estatística": f"F({chow_res['df_num']}, {chow_res['df_den']}) = {chow_res['F']:.3f}",
         "IC 95%": "—",
         "p-valor": f"{chow_res['pvalor']:.4f}",
         "Conclusão": "Quebra estrutural detectada" if chow_res["rejeita_H0_5pct"] else "Sem quebra estrutural em 2020"},
        {"Teste": "Mann-Kendall",
         "Estatística": f"τ = {mk_res['tau_kendall']:.4f}  (Z = {mk_res['z']:.3f})",
         "IC 95%": "—",
         "p-valor": f"{mk_res['pvalor']:.4f}",
         "Conclusão": f"Tendência {mk_res['tendencia']} {'significativa' if mk_res['rejeita_H0_5pct'] else '(não significativa)'}"},
        {"Teste": "AR(1) nos resíduos WLS",
         "Estatística": f"ρ = {ar1_res['rho_ar1']:.4f}  (DW = {ar1_res['durbin_watson']:.3f})",
         "IC 95%": "—",
         "p-valor": f"{ar1_res['pvalor_rho']:.4f}",
         "Conclusão": "Autocorrelação presente — SEs conservadores preferíveis" if ar1_res["autocorr_sig"] else "Sem autocorrelação significativa"},
    ]
    df_tab = pd.DataFrame(rows)
    df_tab.to_csv(OUT_TAB / "tendencia_temporal_testes.csv", index=False, encoding="utf-8")

    tex = df_tab.to_latex(
        index=False, escape=True,
        caption=(
            r"Testes formais de tendência no coeficiente $\hat{\beta}_{negro}$ "
            r"(HLM anual, PNAD Contínua 2016--2025). "
            r"WLS: ponderação por $1/SE^2$ corrige heteroscedasticidade entre anos. "
            r"Chow: quebra estrutural em 2020 (choque COVID-19). "
            r"Mann-Kendall: teste não-paramétrico robusto a autocorrelação. "
            r"AR(1): teste de autocorrelação dos resíduos WLS."
        ),
        label="tab:tendencia_temporal",
    )
    (OUT_TAB / "tendencia_temporal_testes.tex").write_text(tex, encoding="utf-8")
    return df_tab


def _salvar_serie_anual(df: pd.DataFrame) -> None:
    out = df[["ano", "beta", "se", "gap_pct", "ci95_lo", "ci95_hi",
              "n_obs", "icc_uf"]].copy()
    out.columns = ["Ano", "β_negro", "SE", "Gap (%)", "IC95 lo", "IC95 hi",
                   "N obs", "ICC_UF"]
    out.to_csv(OUT_TAB / "tendencia_temporal_serie.csv", index=False, encoding="utf-8")

    tex = out.to_latex(
        index=False, float_format="%.4f",
        caption=(
            r"Série anual do coeficiente $\hat{\beta}_{negro}$ — HLM de intercepto "
            r"aleatório por UF, PNAD Contínua 2016--2025. "
            r"Gap (\%) = $(\exp(\hat{\beta}_{negro}) - 1) \times 100$. "
            r"IC~95\% baseado no SE do HLM anual. "
            r"ICC\_UF = variância explicada pelo estado de residência."
        ),
        label="tab:tendencia_serie_anual",
    )
    (OUT_TAB / "tendencia_temporal_serie.tex").write_text(tex, encoding="utf-8")


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_tendencia_temporal() -> Dict:
    logger.info("=== Análise de Tendência Temporal — β_negro 2016–2025 ===")

    df = _load_series()
    logger.info(f"Série carregada: {len(df)} anos ({df['ano'].min()}–{df['ano'].max()})")

    # 1. WLS global
    wls_res = wls_tendencia(df)
    logger.info(
        f"WLS slope: {wls_res['slope_log']:.6f} log-pt/ano "
        f"(p={wls_res['pvalor']:.4f})"
    )

    # 2. Chow test 2020
    chow_res = chow_test(df, break_year=COVID_YEAR)
    logger.info(
        f"Chow F={chow_res['F']:.3f} (p={chow_res['pvalor']:.4f}) "
        f"— quebra em {COVID_YEAR}: {chow_res['rejeita_H0_5pct']}"
    )

    # 3. Mann-Kendall
    mk_res = mann_kendall(df["beta"])
    logger.info(
        f"Mann-Kendall τ={mk_res['tau_kendall']:.4f} (p={mk_res['pvalor']:.4f})"
    )

    # 4. AR(1) nos resíduos
    ar1_res = teste_ar1(df, wls_res["resultado"])
    logger.info(
        f"AR(1) ρ={ar1_res['rho_ar1']:.4f} "
        f"(DW={ar1_res['durbin_watson']:.3f}, p={ar1_res['pvalor_rho']:.4f})"
    )

    # Salvar tabelas
    tab_testes = _salvar_tabela_wls(wls_res, chow_res, mk_res, ar1_res)
    _salvar_serie_anual(df)

    # Figura
    plotar_tendencia(df, wls_res, chow_res, mk_res)

    # Sumário para o TCC
    print("\n── SUMÁRIO: Tendência Temporal β_negro ──")
    print(f"  WLS slope: {wls_res['slope_log']:.6f} log-pt/ano "
          f"({wls_res['slope_pct_por_ano']:+.4f}pp/ano)  p={wls_res['pvalor']:.4f}")
    print(f"  Variação acumulada 2016→2025: {wls_res['slope_total_2016_2025_pct']:+.2f}pp")
    print(f"  Chow F={chow_res['F']:.3f} (p={chow_res['pvalor']:.4f}) — "
          f"{'quebra em 2020' if chow_res['rejeita_H0_5pct'] else 'sem quebra estrutural em 2020'}")
    print(f"  Mann-Kendall τ={mk_res['tau_kendall']:.4f} — "
          f"tendência {mk_res['tendencia']} "
          f"({'significativa' if mk_res['rejeita_H0_5pct'] else 'não significativa'})")
    print(f"  AR(1) ρ={ar1_res['rho_ar1']:.4f} "
          f"({'autocorrelação presente' if ar1_res['autocorr_sig'] else 'sem autocorrelação'})")

    return {
        "serie": df,
        "wls": wls_res,
        "chow": chow_res,
        "mann_kendall": mk_res,
        "ar1": ar1_res,
        "tabela_testes": tab_testes,
    }
