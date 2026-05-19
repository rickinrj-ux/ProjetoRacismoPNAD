"""
analise_retornos_raciais.py
===========================
Dois módulos complementares para o TCC:

1. DECOMPOSIÇÃO DE OAXACA-BLINDER (twofold)
   Decompõe o gap salarial racial em:
       (a) Efeito dotação  : quanto do gap é explicado por diferenças em
           características observáveis (educação, idade, sexo).
           → Argumento meritocrático: "negros ganham menos porque têm menos
             escolaridade". Se verdadeiro, (a) domina o gap.
       (b) Efeito coeficiente: quanto do gap persiste mesmo quando negros
           têm as MESMAS características que brancos — retornos diferentes
           para idênticas dotações.
           → Limite inferior da discriminação: diferença inexplicada por
             capital humano. Complementa β_negro do HLM.

   Decomposição twofold (Blinder, 1973; Oaxaca, 1973):
       Δȳ = (X̄_B − X̄_N)·β_B  +  X̄_N·(β_B − β_N)
              ─────────────────    ───────────────────
                 efeito dotação      efeito coeficiente

2. INTERAÇÃO NEGRO × ESCOLARIDADE
   Testa se o retorno monetário à educação é menor para trabalhadores
   negros ("desconto de credencial") — hipótese central no debate sobre
   por que o investimento educacional da comunidade negra não se converte
   em mobilidade salarial proporcional.

   Modelo OLS com efeitos fixos de UF:
       log_renda ~ negro + educ_* + negro:educ_* + controles + C(UF)

   Interpretação dos coeficientes de interação:
       β_{negro:educ_superior} < 0 → retorno ao ensino superior é MENOR
       para negros que para brancos com o mesmo grau — discriminação opera
       descontando credenciais de trabalhadores negros.

   Conexão com glass ceiling (análise regional já existente):
       Regressão quantílica com interações: se o desconto cresce do τ=0.10
       para τ=0.90, o "teto de vidro" é confirmado — discriminação é mais
       intensa justamente onde os retornos à educação deveriam ser maiores.

Referências:
    Blinder, A. S. (1973). Wage Discrimination: Reduced Form and Structural
        Estimates. Journal of Human Resources, 8(4), 436-455.
    Oaxaca, R. (1973). Male-Female Wage Differentials in Urban Labor Markets.
        International Economic Review, 14(3), 693-709.
    Altonji, J. G., & Blank, R. M. (1999). Race and Gender in the Labor
        Market. Handbook of Labor Economics, 3, 3143-3259.
    Carneiro, P., Heckman, J. J., & Masterov, D. V. (2005). Labor market
        discrimination and racial differences in premarket factors.
        Journal of Law and Economics, 48(1), 1-39.
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
from scipy import stats as scipy_stats

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

FORMULA_OLS = (
    "log_renda ~ sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
    " + log_horas + urbano + C(Ano)"
)

FORMULA_INTERACAO = (
    "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
    " + negro:educ_medio_completo"
    " + negro:educ_superior_completo"
    " + negro:educ_pos_graduacao"
    " + log_horas + urbano + C(Ano) + C(UF)"
)

FORMULA_QR_INTERACAO = (
    "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
    " + educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
    " + negro:educ_medio_completo"
    " + negro:educ_superior_completo"
    " + negro:educ_pos_graduacao"
    " + log_horas + urbano + C(Ano)"
)

MODEL_VARS = [
    "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "log_horas", "urbano", "Ano",
    "UF",
]

NIVEIS_EDUC = {
    "educ_fund_completo":    "Fund. Completo",
    "educ_medio_completo":   "Médio Completo",
    "educ_superior_completo":"Superior Completo",
    "educ_pos_graduacao":    "Pós-Graduação",
}
QUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]


# ── Carregamento ───────────────────────────────────────────────────────────────

def carregar_dados(sample_frac: Optional[float] = None) -> pd.DataFrame:
    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    # Fallback: recria colunas ausentes se features.parquet foi gerado antes
    if "log_horas" not in df.columns and "horas_trabalhadas" in df.columns:
        df["log_horas"] = np.log(df["horas_trabalhadas"].clip(lower=1))
    if "urbano" not in df.columns:
        df["urbano"] = (df["V1022"] == 1).astype("int8") if "V1022" in df.columns else 1
    df = df.dropna(subset=MODEL_VARS).reset_index(drop=True)
    df["log_renda"] = df["log_renda"].astype(float)
    df["UF_str"]    = df["UF"].astype(str)
    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)
    n_neg = (df["negro"] == 1).sum()
    n_bra = (df["negro"] == 0).sum()
    logger.info(f"Dataset: {len(df):,} obs. | negros={n_neg:,} | brancos={n_bra:,}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 1. OAXACA-BLINDER
# ══════════════════════════════════════════════════════════════════════════════

def _ols_grupo(df: pd.DataFrame, formula: str) -> object:
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("ignore")
        return smf.ols(formula, data=df).fit()


def oaxaca_blinder(
    df: pd.DataFrame,
    n_bootstrap: int = 200,
) -> Dict:
    """
    Decomposição twofold de Oaxaca-Blinder com erros-padrão bootstrap.

    Referência ponderada: usa coeficientes do grupo de referência (brancos)
    — padrão para decomposição de discriminação contra minoria (Oaxaca, 1973).

    Bootstrap por UF (cluster bootstrap) para preservar estrutura de
    correlação intra-estado nos erros-padrão.
    """
    logger.info("── Oaxaca-Blinder ──────────────────────────────────────────")
    df_b = df[df["negro"] == 0].copy()
    df_n = df[df["negro"] == 1].copy()

    # Estimativas pontuais
    res_b = _ols_grupo(df_b, FORMULA_OLS)
    res_n = _ols_grupo(df_n, FORMULA_OLS)

    # Usa a matriz de design expandida pelo modelo (correto para C(Ano), C(UF) etc.)
    mean_b = pd.Series(
        res_b.model.exog[:, 1:].mean(axis=0),
        index=res_b.model.exog_names[1:],
    )
    mean_n = pd.Series(
        res_n.model.exog[:, 1:].mean(axis=0),
        index=res_n.model.exog_names[1:],
    )

    coef_b = res_b.params.drop("Intercept", errors="ignore")
    coef_n = res_n.params.drop("Intercept", errors="ignore")

    gap_total    = df_b["log_renda"].mean() - df_n["log_renda"].mean()
    ef_dotacao   = float((mean_b - mean_n) @ coef_b)
    ef_coef      = float(mean_n @ (coef_b - coef_n))
    # Verificação: ef_dotacao + ef_coef ≈ gap_total (pequena diferença por intercepto)

    pct_dotacao  = ef_dotacao / gap_total * 100 if gap_total != 0 else np.nan
    pct_coef     = ef_coef   / gap_total * 100 if gap_total != 0 else np.nan

    logger.info(f"  Gap total    : {gap_total:+.4f} ({(np.exp(gap_total)-1)*100:+.1f}%)")
    logger.info(f"  Efeito dotação (explicado)    : {ef_dotacao:+.4f} ({pct_dotacao:.1f}%)")
    logger.info(f"  Efeito coeficiente (não explicado): {ef_coef:+.4f} ({pct_coef:.1f}%)")

    # Bootstrap por cluster (UF)
    boot_dot, boot_coef = [], []
    ufs = df["UF"].unique()
    rng = np.random.default_rng(42)

    for _ in range(n_bootstrap):
        ufs_boot = rng.choice(ufs, size=len(ufs), replace=True)
        frames   = [df[df["UF"] == u] for u in ufs_boot]
        df_boot  = pd.concat(frames, ignore_index=True)

        db = df_boot[df_boot["negro"] == 0]
        dn = df_boot[df_boot["negro"] == 1]
        if len(db) < 100 or len(dn) < 100:
            continue
        try:
            rb = _ols_grupo(db, FORMULA_OLS)
            rn = _ols_grupo(dn, FORMULA_OLS)
            cb = rb.params.drop("Intercept", errors="ignore")
            cn = rn.params.drop("Intercept", errors="ignore")
            mb = pd.Series(
                rb.model.exog[:, 1:].mean(axis=0),
                index=rb.model.exog_names[1:],
            )
            mn = pd.Series(
                rn.model.exog[:, 1:].mean(axis=0),
                index=rn.model.exog_names[1:],
            )
            boot_dot.append(float((mb - mn) @ cb))
            boot_coef.append(float(mn @ (cb - cn)))
        except Exception:
            continue

    se_dot  = np.std(boot_dot)  if boot_dot  else np.nan
    se_coef = np.std(boot_coef) if boot_coef else np.nan

    resultado = {
        "gap_total":     gap_total,
        "gap_pct":       (np.exp(gap_total) - 1) * 100,
        "ef_dotacao":    ef_dotacao,
        "se_dotacao":    se_dot,
        "pct_dotacao":   pct_dotacao,
        "ef_coeficiente": ef_coef,
        "se_coeficiente": se_coef,
        "pct_coeficiente": pct_coef,
        "n_brancos":     len(df_b),
        "n_negros":      len(df_n),
        "coef_branco":   coef_b.to_dict(),
        "coef_negro":    coef_n.to_dict(),
        "n_bootstrap":   len(boot_dot),
    }
    return resultado


def plotar_oaxaca(resultado: Dict) -> None:
    """Gráfico de barras horizontais da decomposição OB."""
    ef_dot  = resultado["ef_dotacao"]
    ef_coef = resultado["ef_coeficiente"]
    se_dot  = resultado["se_dotacao"]
    se_coef = resultado["se_coeficiente"]
    gap     = resultado["gap_total"]

    labels = ["Efeito Dotação\n(características observáveis)",
              "Efeito Coeficiente\n(retornos diferentes / discriminação)"]
    values = [ef_dot, ef_coef]
    ses    = [se_dot, se_coef]
    pcts   = [resultado["pct_dotacao"], resultado["pct_coeficiente"]]
    cores  = ["#2980b9", "#c0392b"]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(labels, values, xerr=[1.96 * s for s in ses],
                   color=cores, edgecolor="black", linewidth=0.5,
                   capsize=5, alpha=0.85)

    for bar, pct, val in zip(bars, pcts, values):
        ax.text(val + 0.003 if val >= 0 else val - 0.003,
                bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}% do gap",
                va="center", ha="left" if val >= 0 else "right",
                fontsize=9, fontweight="bold")

    ax.axvline(0, color="black", linewidth=0.8)
    ax.axvline(gap, color="gray", linewidth=1, linestyle=":",
               label=f"Gap total = {gap:+.4f} ({(np.exp(gap)-1)*100:.1f}%)")
    ax.set_xlabel("Contribuição ao gap de log-renda", fontsize=10)
    ax.set_title(
        "Decomposição de Oaxaca-Blinder do Gap Salarial Racial\n"
        "Barras = IC 95% bootstrap por cluster (UF)",
        fontsize=11,
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "ob_decomposicao.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: ob_decomposicao.png")


def plotar_retornos_educacao_ob(resultado: Dict) -> None:
    """Compara retornos à educação entre brancos e negros (da OLS separada)."""
    coef_b = resultado["coef_branco"]
    coef_n = resultado["coef_negro"]
    niveis = list(NIVEIS_EDUC.keys())
    labels = list(NIVEIS_EDUC.values())

    x  = np.arange(len(niveis))
    w  = 0.35
    rb = [coef_b.get(n, np.nan) for n in niveis]
    rn = [coef_n.get(n, np.nan) for n in niveis]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - w/2, rb, w, label="Brancos", color="#2980b9",
           edgecolor="black", linewidth=0.5)
    ax.bar(x + w/2, rn, w, label="Negros",  color="#c0392b",
           edgecolor="black", linewidth=0.5)

    for xi, (b_val, n_val) in enumerate(zip(rb, rn)):
        if not np.isnan(b_val) and not np.isnan(n_val):
            diff = n_val - b_val
            ax.annotate(
                f"Δ={diff:+.3f}",
                xy=(xi, max(b_val, n_val) + 0.005),
                ha="center", fontsize=8, color="#7f8c8d",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Retorno à escolaridade (log-renda)", fontsize=10)
    ax.set_title(
        "Retorno à Educação por Raça — OLS separada\n"
        "Δ negativo = desconto de credencial para trabalhadores negros",
        fontsize=11,
    )
    ax.legend(fontsize=10)
    ax.axhline(0, color="black", linewidth=0.7)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "ob_retornos_educacao.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: ob_retornos_educacao.png")


# ══════════════════════════════════════════════════════════════════════════════
# 2. INTERAÇÃO NEGRO × ESCOLARIDADE
# ══════════════════════════════════════════════════════════════════════════════

def interacao_raca_escolaridade(df: pd.DataFrame) -> pd.DataFrame:
    """
    OLS com efeitos fixos de UF e interações negro × nível de educação.

    Coeficientes de interação interpretados como 'desconto de credencial':
        β_{negro:educ_superior} < 0 → negro com superior completo tem retorno
        MENOR que branco com superior completo, após controlar por idade,
        sexo e demais níveis.

    Efeitos fixos de UF absorvem heterogeneidade estadual não observada,
    garantindo que os coeficientes de interação não capturem apenas diferenças
    regionais na composição racial × educacional.
    """
    logger.info("── Interação Negro × Escolaridade ──────────────────────────")
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("ignore")
        res = smf.ols(FORMULA_INTERACAO, data=df).fit(
            cov_type="cluster", cov_kwds={"groups": df["UF"]}
        )

    interacoes = {}
    for nivel, label in NIVEIS_EDUC.items():
        chave = f"negro:educ_{nivel.split('_', 1)[1]}" if "fund" not in nivel else None
        # Monta o nome da interação como statsmodels gera
        for nome in res.params.index:
            if "negro" in nome and nivel.split("educ_")[1] in nome:
                chave = nome
                break
        if chave and chave in res.params:
            b  = res.params[chave]
            se = res.bse[chave]
            pv = res.pvalues[chave]
            interacoes[label] = {
                "nivel":         nivel,
                "label":         label,
                "beta_interacao": b,
                "se_interacao":   se,
                "pval":           pv,
                "desconto_pct":   (np.exp(b) - 1) * 100,
                "sig": "***" if pv < 0.001 else "**" if pv < 0.01 else "*" if pv < 0.05 else "ns",
            }
            logger.info(
                f"  negro × {label:<22}: β={b:+.4f}  "
                f"({(np.exp(b)-1)*100:+.1f}%)  p={pv:.4f}"
            )

    # Também extrai o β_negro base (sem interação, = retorno para fund_incompleto)
    b_negro_base = res.params.get("negro", np.nan)
    logger.info(f"  negro base (ref=fund_incompleto): β={b_negro_base:+.4f}")

    df_int = pd.DataFrame(interacoes).T.reset_index(drop=True)
    df_int["beta_negro_base"] = b_negro_base
    df_int["beta_total_negro"] = df_int["beta_negro_base"] + df_int["beta_interacao"]

    return df_int


def interacao_quantilica(
    df: pd.DataFrame,
    quantiles: List[float] = QUANTILES,
) -> pd.DataFrame:
    """
    Regressão quantílica com interações negro × educação.

    Testa se o desconto de credencial é maior no topo da distribuição
    (glass ceiling) ou na base (sticky floor).
    """
    logger.info("── Interação Quantílica ────────────────────────────────────")
    rows = []
    for q in quantiles:
        try:
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("ignore")
                res = smf.quantreg(FORMULA_QR_INTERACAO, data=df).fit(
                    q=q, max_iter=3000
                )
            for nivel, label in {
                "educ_medio_completo":    "Médio",
                "educ_superior_completo": "Superior",
                "educ_pos_graduacao":     "Pós-Grad.",
            }.items():
                for nome in res.params.index:
                    if "negro" in nome and nivel.split("educ_")[1] in nome:
                        b  = res.params[nome]
                        ci = res.conf_int()
                        rows.append({
                            "quantil": q,
                            "nivel":   label,
                            "beta":    b,
                            "ci_low":  ci.loc[nome, 0] if nome in ci.index else np.nan,
                            "ci_high": ci.loc[nome, 1] if nome in ci.index else np.nan,
                        })
                        break
        except Exception as exc:
            logger.warning(f"  QuantReg τ={q}: {exc}")

    return pd.DataFrame(rows)


def plotar_interacao(df_int: pd.DataFrame) -> None:
    """Dot-plot dos coeficientes de interação negro × escolaridade com IC95%."""
    if df_int.empty:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    cores = ["#c0392b" if p < 0.05 else "#95a5a6"
             for p in df_int["pval"].astype(float)]

    for i, (_, row) in enumerate(df_int.iterrows()):
        b  = row["beta_interacao"]
        se = row["se_interacao"]
        ax.errorbar(b, i, xerr=1.96 * se, fmt="o",
                    color=cores[i], markersize=9, linewidth=2, capsize=5)
        ax.text(b + 1.96 * se + 0.003, i,
                f"{row['desconto_pct']:+.1f}%  ({row['sig']})",
                va="center", fontsize=9)

    ax.axvline(0, color="black", linewidth=1, linestyle="--")
    ax.set_yticks(range(len(df_int)))
    ax.set_yticklabels(df_int["label"].tolist(), fontsize=10)
    ax.set_xlabel("β interação negro × escolaridade (log-renda) · IC 95%", fontsize=10)
    ax.set_title(
        "Desconto de Credencial por Nível de Escolaridade\n"
        "Quanto MENOR o retorno adicional à educação para trabalhadores negros\n"
        "Vermelho = significativo  ·  OLS com EF de UF e SE clusterizado",
        fontsize=10,
    )
    plt.tight_layout()
    fig.savefig(OUT_FIG / "interacao_negro_escolaridade.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: interacao_negro_escolaridade.png")


def plotar_interacao_quantilica(df_qint: pd.DataFrame) -> None:
    """Perfil dos coeficientes de interação ao longo dos quantis."""
    if df_qint.empty:
        return

    niveis = df_qint["nivel"].unique()
    cores  = {"Médio": "#3498db", "Superior": "#e74c3c", "Pós-Grad.": "#2ecc71"}

    fig, ax = plt.subplots(figsize=(9, 5))
    for nivel in niveis:
        sub = df_qint[df_qint["nivel"] == nivel].sort_values("quantil")
        cor = cores.get(nivel, "#555")
        ax.plot(sub["quantil"], sub["beta"], "o-", color=cor,
                linewidth=2, markersize=7, label=f"negro × {nivel}")
        ax.fill_between(sub["quantil"], sub["ci_low"], sub["ci_high"],
                        color=cor, alpha=0.12)

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Quantil de renda", fontsize=11)
    ax.set_ylabel("β interação negro × escolaridade", fontsize=11)
    ax.set_title(
        "Desconto de Credencial por Quantil de Renda\n"
        "Queda no topo = glass ceiling  ·  Queda na base = sticky floor",
        fontsize=11,
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "interacao_quantilica.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: interacao_quantilica.png")


def _gerar_latex_ob(resultado: Dict) -> None:
    gap  = resultado["gap_total"]
    rows = [
        {"Componente": "Gap Total (branco − negro)",
         "Magnitude": f"{gap:+.4f}",
         "\\% do Gap": "100,0",
         "SE (bootstrap)": "—"},
        {"Componente": "Efeito Dotação (características)",
         "Magnitude": f"{resultado['ef_dotacao']:+.4f}",
         "\\% do Gap": f"{resultado['pct_dotacao']:.1f}",
         "SE (bootstrap)": f"({resultado['se_dotacao']:.4f})"},
        {"Componente": "Efeito Coeficiente (retornos / discriminação)",
         "Magnitude": f"{resultado['ef_coeficiente']:+.4f}",
         "\\% do Gap": f"{resultado['pct_coeficiente']:.1f}",
         "SE (bootstrap)": f"({resultado['se_coeficiente']:.4f})"},
    ]
    tex = pd.DataFrame(rows).to_latex(
        index=False, escape=False,
        caption=(
            "Decomposição de Oaxaca-Blinder (twofold) do gap salarial racial. "
            "Efeito dotação: parcela explicada por diferenças em características "
            "observáveis (educação, idade, sexo). "
            "Efeito coeficiente: parcela inexplicada por capital humano — "
            "limite inferior da discriminação salarial racial. "
            "Erros-padrão obtidos por bootstrap com 200 replicações "
            "agrupadas por UF."
        ),
        label="tab:oaxaca_blinder",
    )
    (OUT_TAB / "ob_decomposicao.tex").write_text(tex, encoding="utf-8")
    logger.info("LaTeX: ob_decomposicao.tex")


def _gerar_latex_interacao(df_int: pd.DataFrame) -> None:
    if df_int.empty:
        return
    sig = lambda p: ("$^{***}$" if p < 0.001 else "$^{**}$" if p < 0.01
                     else "$^{*}$" if p < 0.05 else "")
    rows = []
    for _, r in df_int.iterrows():
        p = float(r["pval"])
        rows.append({
            "Nível":                r["label"],
            "$\\beta_{interacao}$": f"{r['beta_interacao']:.4f}{sig(p)}",
            "SE":                   f"({r['se_interacao']:.4f})",
            "Desconto (\\%)":       f"{r['desconto_pct']:+.1f}",
            "p-valor":              f"{p:.4f}",
        })
    tex = pd.DataFrame(rows).to_latex(
        index=False, escape=False,
        caption=(
            "Desconto de credencial por nível de escolaridade — "
            "coeficientes de interação negro $\\times$ escolaridade. "
            "$\\beta_{interacao} < 0$ indica que o retorno à escolaridade "
            "é menor para trabalhadores negros que para brancos com o mesmo grau, "
            "evidência de desvalorização de credenciais educacionais por raça. "
            "OLS com efeitos fixos de UF e erros-padrão clusterizados por UF. "
            "*** p$<$0,001; ** p$<$0,01; * p$<$0,05."
        ),
        label="tab:interacao_escolaridade",
    )
    (OUT_TAB / "interacao_escolaridade.tex").write_text(tex, encoding="utf-8")
    logger.info("LaTeX: interacao_escolaridade.tex")


# ── Pipeline principal ─────────────────────────────────────────────────────────

def run_analise_retornos_raciais(
    sample_frac: Optional[float] = None,
    n_bootstrap: int = 200,
) -> Dict:
    """
    Pipeline completo: Oaxaca-Blinder + Interação negro × escolaridade.

    Returns
    -------
    dict com 'oaxaca', 'interacao', 'interacao_quantilica'
    """
    df = carregar_dados(sample_frac=sample_frac)

    with run_context("pipeline_retornos_raciais", "Retornos_Raciais",
                     tags={"sample_frac": str(sample_frac or "completo"),
                           "n_obs": str(len(df))}):
        log_params({"sample_frac": sample_frac, "n_obs": len(df),
                    "n_bootstrap": n_bootstrap})

        # ── Oaxaca-Blinder ────────────────────────────────────────────
        resultado_ob = oaxaca_blinder(df, n_bootstrap=n_bootstrap)
        log_metrics({
            "ob_gap_total":       resultado_ob["gap_total"],
            "ob_ef_dotacao":      resultado_ob["ef_dotacao"],
            "ob_pct_dotacao":     resultado_ob["pct_dotacao"],
            "ob_ef_coeficiente":  resultado_ob["ef_coeficiente"],
            "ob_pct_coeficiente": resultado_ob["pct_coeficiente"],
        })
        set_tag("discriminacao_nao_explicada_pct",
                f"{resultado_ob['pct_coeficiente']:.1f}%")

        pd.DataFrame([{k: v for k, v in resultado_ob.items()
                       if not isinstance(v, dict)}]).to_csv(
            OUT_TAB / "ob_decomposicao.csv", index=False)
        _gerar_latex_ob(resultado_ob)
        plotar_oaxaca(resultado_ob)
        plotar_retornos_educacao_ob(resultado_ob)

        # ── Interação negro × escolaridade ────────────────────────────
        df_int  = interacao_raca_escolaridade(df)
        df_qint = interacao_quantilica(df)

        if not df_int.empty:
            df_int.to_csv(OUT_TAB / "interacao_escolaridade.csv", index=False)
            _gerar_latex_interacao(df_int)
            plotar_interacao(df_int)
            log_metrics({
                f"desconto_{row['label'].replace(' ', '_')}":
                    row["desconto_pct"]
                for _, row in df_int.iterrows()
            })

        if not df_qint.empty:
            df_qint.to_csv(OUT_TAB / "interacao_quantilica.csv", index=False)
            plotar_interacao_quantilica(df_qint)

        log_artifacts_dir(OUT_TAB, subfolder="tables")
        log_artifacts_dir(OUT_FIG, subfolder="figures")

    # Sumário
    print("\n── SUMÁRIO: Retornos Raciais ──")
    print(f"  Gap total       : {resultado_ob['gap_total']:+.4f} "
          f"({resultado_ob['gap_pct']:+.1f}%)")
    print(f"  Efeito dotação  : {resultado_ob['ef_dotacao']:+.4f} "
          f"({resultado_ob['pct_dotacao']:.1f}% do gap) — parte explicável")
    print(f"  Efeito coef.    : {resultado_ob['ef_coeficiente']:+.4f} "
          f"({resultado_ob['pct_coeficiente']:.1f}% do gap) — discriminação")
    if not df_int.empty:
        print("\n  Desconto de credencial (β interação):")
        for _, row in df_int.iterrows():
            print(f"    {row['label']:<24}: {row['beta_interacao']:+.4f} "
                  f"({row['desconto_pct']:+.1f}%)  {row['sig']}")

    return {
        "oaxaca":              resultado_ob,
        "interacao":           df_int,
        "interacao_quantilica": df_qint,
    }
