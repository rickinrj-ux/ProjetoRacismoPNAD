"""
heckman_selecao.py
==================
Correção de seleção amostral — Heckman two-step (1979) para o gap salarial racial.

Problema:
    O dataset analítico filtra trabalhadores com renda positiva (log_renda > 0),
    excluindo desempregados da PEA. Como negros têm taxa de desemprego ~2× maior,
    o subsample de negros *empregados* é positivamente selecionado — os mais
    produtivos/privilegiados entre os negros chegam ao dataset. Isso potencialmente
    *subestima* o gap observado no mercado de trabalho como um todo.

Método (Heckman, 1979):
    Estágio 1 — Probit de seleção:
        Pr(y_sel=1 | X, Z) = Φ(Xγ + δ·Z)
        onde X = covariáveis individuais (também no modelo de renda)
              Z = variável de exclusão (não incluída na equação de renda)

    Estágio 2 — OLS com Razão de Mills Inversa (IMR):
        log_renda = α + β·negro + X'θ + λ·IMR + ε
        IMR = φ(X̂γ) / Φ(X̂γ)    (razão de Mills)

    Se λ (coef. do IMR) ≠ 0 → viés de seleção confirmado.
    β_Heckman é a estimativa corrigida do gap.

Variável de exclusão:
    media_renda_upa_z — renda média da UPA (z-padronizada).
    Justificativa:
      • Forte preditor de seleção: UPAs mais ricas → mais oportunidades de trabalho
        → maior probabilidade de estar empregado com renda positiva.
      • Excluída da equação de renda (M1–M3 usam pct_negro_upa, tx_desemprego_upa
        e media_educ_upa — mas NÃO media_renda_upa como preditor direto).
      • Assumption de exclusão: conditional on individual characteristics and UPA
        unemployment rate, neighborhood average income affects JOB AVAILABILITY
        more than the individual wage level once employed.

Referências:
    Heckman, J. J. (1979). Sample selection bias as a specification error.
        Econometrica, 47(1), 153–161.
    Wooldridge, J. M. (2010). Econometric Analysis of Cross Section and
        Panel Data (2nd ed.). MIT Press. Cap. 19.
    Greene, W. H. (2012). Econometric Analysis (7th ed.). Pearson. Cap. 24.
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
from scipy import stats
from scipy.stats import norm

logger = logging.getLogger(__name__)

ROOT          = Path(__file__).parent.parent
FEATURES_PATH = ROOT / "data" / "processed" / "features.parquet"
OUT_FIG       = ROOT / "outputs" / "figures"
OUT_TAB       = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

# Colunas necessárias — carregamento seletivo para controle de memória
_SEL_COLS = [
    "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "log_renda", "log_horas", "urbano", "Ano", "UF",
    "pea", "empregado",
    "pct_negro_upa_z", "tx_desemprego_upa_z",
    "media_educ_upa_z", "media_renda_upa_z",   # media_renda_upa_z = exclusão
]

# Fórmula do probit de seleção (Estágio 1)
FORMULA_PROBIT = (
    "y_sel ~ negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
    " + urbano + C(Ano) + C(UF)"
    " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
    " + media_renda_upa_z"   # variável de exclusão
)

# Fórmula OLS baseline — Estágio 2 sem IMR (referência)
FORMULA_OLS = (
    "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
    " + log_horas + urbano + C(Ano) + C(UF)"
    " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
)

# Fórmula Heckman — Estágio 2 com IMR
FORMULA_HECKMAN = FORMULA_OLS + " + imr"


# ── Carregamento e preparação ─────────────────────────────────────────────────

def _load_pea_sample(sample_frac_probit: float = 0.20) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Carrega features.parquet e devolve dois DataFrames:
      (1) df_pea_sample — amostra estratificada da PEA para o Probit (Estágio 1)
      (2) df_empregados — subsample de empregados com renda para o OLS (Estágio 2)

    Estratificação no sample para o probit: mantém proporção de y_sel=0 e y_sel=1,
    garantindo que desempregados não sejam sub-representados na amostra.
    """
    cols_to_load = [c for c in _SEL_COLS if c not in ("UF",)]  # UF carregado como int
    cols_to_load += ["UF"]

    logger.info(f"Carregando features.parquet (colunas selecionadas)...")
    df = pd.read_parquet(FEATURES_PATH, columns=cols_to_load)
    logger.info(f"  Total bruto: {len(df):,}")

    # Filtro racial
    df = df[df["negro"].isin([0.0, 1.0])].copy()
    logger.info(f"  Após filtro racial: {len(df):,}")

    # Filtro PEA (pea == 1)
    df["pea_bool"] = df["pea"].fillna(0).astype(bool)
    df = df[df["pea_bool"]].copy()
    logger.info(f"  PEA (pea==1): {len(df):,}")

    # Variável de seleção: empregado com renda positiva
    df["y_sel"] = (
        df["log_renda"].notna() & (df["log_renda"] > 0)
    ).astype("int8")
    logger.info(f"  y_sel=1 (empregados c/ renda): {df['y_sel'].sum():,}  "
                f"({df['y_sel'].mean():.1%})")
    logger.info(f"  y_sel=0 (desempregados/sem renda): {(df['y_sel']==0).sum():,}")

    # Remove NaN nas covariáveis do probit (exceto log_renda e log_horas — só existem para empregados)
    probit_vars = [
        "y_sel", "negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_fund_completo", "educ_medio_completo",
        "educ_superior_completo", "educ_pos_graduacao",
        "urbano", "Ano", "UF",
        "pct_negro_upa_z", "tx_desemprego_upa_z",
        "media_educ_upa_z", "media_renda_upa_z",
    ]
    df_clean = df.dropna(subset=probit_vars).copy()
    logger.info(f"  Após dropna nas vars probit: {len(df_clean):,}")

    # Amostra estratificada para o probit (Estágio 1)
    emp     = df_clean[df_clean["y_sel"] == 1]
    desemp  = df_clean[df_clean["y_sel"] == 0]
    n_emp   = int(len(emp) * sample_frac_probit)
    n_desemp= int(len(desemp) * sample_frac_probit)
    sample  = pd.concat([
        emp.sample(n=n_emp, random_state=42),
        desemp.sample(n=n_desemp, random_state=42),
    ]).reset_index(drop=True)
    logger.info(
        f"  Amostra probit ({sample_frac_probit:.0%} estratificada): "
        f"{len(sample):,} obs "
        f"({n_emp:,} empregados + {n_desemp:,} desempregados)"
    )

    # Dataset de empregados para Estágio 2 (com todos os dados necessários)
    ols_vars = [
        "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_fund_completo", "educ_medio_completo",
        "educ_superior_completo", "educ_pos_graduacao",
        "log_horas", "urbano", "Ano", "UF",
        "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
        "media_renda_upa_z",
    ]
    df_emp = df_clean[df_clean["y_sel"] == 1].dropna(subset=ols_vars).copy()
    logger.info(f"  Dataset OLS (empregados completos): {len(df_emp):,}")

    return sample, df_emp, df_clean


# ── Estágio 1: Probit ─────────────────────────────────────────────────────────

def _estimar_probit(df_sample: pd.DataFrame) -> object:
    """
    Estima probit de seleção na amostra estratificada.

    Retorna o resultado ajustado do statsmodels.Probit — coeficientes
    serão aplicados ao dataset completo da PEA para calcular a IMR.
    """
    logger.info("Estágio 1: estimando Probit de seleção...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        probit_mod = smf.probit(FORMULA_PROBIT, data=df_sample)
        probit_res = probit_mod.fit(maxiter=200, disp=False)
    logger.info(
        f"  Probit convergiu: {probit_res.mle_retvals.get('converged', '?')}"
        f"  |  LL = {probit_res.llf:.1f}  |  N = {probit_res.nobs:,}"
    )
    return probit_res


def _calcular_imr(df_pea: pd.DataFrame, probit_res: object) -> pd.DataFrame:
    """
    Calcula a Razão de Mills Inversa (IMR) para TODOS os empregados.

    IMR = φ(Xγ̂) / Φ(Xγ̂)

    Onde:
        φ = densidade da normal padrão
        Φ = CDF da normal padrão
        Xγ̂ = índice probit predito (xb)

    Para empregados (y_sel=1), a IMR mede a intensidade da seleção
    positiva: maior IMR → observação mais improvável dado X
    (selecionado de uma cauda de distribuição estreita).
    """
    # which="linear" é a forma correta em statsmodels ≥ 0.14
    try:
        xb = probit_res.predict(df_pea, which="linear")
    except TypeError:
        xb = probit_res.predict(df_pea, linear=True)
    phi = norm.pdf(xb)
    Phi = norm.cdf(xb)
    # Evita divisão por zero em Φ muito pequena
    Phi = np.where(Phi < 1e-10, 1e-10, Phi)
    df_pea = df_pea.copy()
    df_pea["imr"] = phi / Phi
    return df_pea


# ── Estágio 2: OLS com IMR ────────────────────────────────────────────────────

def _estimar_ols_baseline(df_emp: pd.DataFrame) -> object:
    """OLS sem IMR — estimativa não corrigida (referência)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = smf.ols(FORMULA_OLS, data=df_emp).fit(
            cov_type="cluster", cov_kwds={"groups": df_emp["UF"]}
        )
    return res


def _estimar_heckman_ols(df_emp_imr: pd.DataFrame) -> object:
    """OLS com IMR — estimativa corrigida por seleção."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = smf.ols(FORMULA_HECKMAN, data=df_emp_imr).fit(
            cov_type="cluster", cov_kwds={"groups": df_emp_imr["UF"]}
        )
    return res


# ── Tabelas de resultados ─────────────────────────────────────────────────────

def _tabela_comparacao(
    probit_res,
    ols_base,
    ols_heck,
) -> pd.DataFrame:
    """
    Tabela comparativa: β_negro sem e com correção de Heckman.

    A diferença Δβ quantifica a direção e magnitude do viés de seleção:
        Δβ > 0 → gap subestimado (seleção positiva: negros empregados são mais qualificados)
        Δβ < 0 → gap superestimado (seleção negativa: os mais fracos permanecem empregados)
    """
    def _extract(res, coef: str) -> Tuple[float, float, float, float]:
        b   = res.params.get(coef, np.nan)
        se  = res.bse.get(coef, np.nan)
        pv  = res.pvalues.get(coef, np.nan)
        gpp = (np.exp(b) - 1) * 100 if not np.isnan(b) else np.nan
        return b, se, pv, gpp

    b_base, se_base, pv_base, gpp_base = _extract(ols_base, "negro")
    b_heck, se_heck, pv_heck, gpp_heck = _extract(ols_heck, "negro")
    b_imr,  se_imr,  pv_imr,  _        = _extract(ols_heck, "imr")

    delta = b_heck - b_base
    delta_pct = gpp_heck - gpp_base

    rows = [
        {
            "Modelo": "OLS (sem correção)",
            "β_negro": round(b_base, 5),
            "SE (cluster-UF)": round(se_base, 5),
            "p-valor": round(pv_base, 4),
            "Gap (%)": round(gpp_base, 2),
            "IMR (λ)": "—",
            "IMR p-valor": "—",
            "Nota": "Estimativa convencional — não corrige seleção",
        },
        {
            "Modelo": "Heckman (com IMR)",
            "β_negro": round(b_heck, 5),
            "SE (cluster-UF)": round(se_heck, 5),
            "p-valor": round(pv_heck, 4),
            "Gap (%)": round(gpp_heck, 2),
            "IMR (λ)": round(b_imr, 5),
            "IMR p-valor": round(pv_imr, 4),
            "Nota": (
                "Corrigido por seleção — "
                f"λ {'significativo (viés confirmado)' if pv_imr < 0.05 else 'não significativo'}"
            ),
        },
        {
            "Modelo": "Δ (Heckman − OLS)",
            "β_negro": round(delta, 5),
            "SE (cluster-UF)": "—",
            "p-valor": "—",
            "Gap (%)": round(delta_pct, 3),
            "IMR (λ)": "—",
            "IMR p-valor": "—",
            "Nota": (
                "Δ > 0 → OLS superestima o gap: negros empregados aceitam salários mais baixos "
                "(seleção por tolerância à discriminação salarial) → OLS confunde discriminação "
                "com mecanismo de seleção no acesso ao emprego"
                if delta > 0 else
                "Δ < 0 → OLS subestima o gap: negros empregados são positivamente selecionados "
                "em produtividade (os mais qualificados entre os negros conseguem emprego)"
            ),
        },
    ]
    return pd.DataFrame(rows)


def _tabela_probit(probit_res) -> pd.DataFrame:
    """
    Coeficientes e AME aproximado do probit de seleção.

    AME ≈ φ(mean Xγ̂) × β  (aproximação de 1ª ordem, válida como ordem de magnitude).
    O φ(mean Xγ̂) é computado a partir das previsões do modelo sobre a amostra
    de estimação, não de uma matriz exog manipulada diretamente.
    """
    params = probit_res.params
    bse    = probit_res.bse
    pvals  = probit_res.pvalues

    # Índice probit médio usando as previsões sobre a amostra de treinamento
    try:
        try:
            xb_all = probit_res.predict(which="linear")
        except TypeError:
            xb_all = probit_res.predict(linear=True)
        phi_mean = float(norm.pdf(np.mean(xb_all)))
    except Exception:
        phi_mean = norm.pdf(0.0)  # fallback: φ(0) ≈ 0.399

    rows = []
    for k in params.index:
        b, s, p = params[k], bse[k], pvals[k]
        ame = phi_mean * b
        rows.append({
            "Variável": k,
            "Coeficiente": round(b, 5),
            "SE": round(s, 5),
            "p-valor": round(p, 4),
            "AME (aprox.)": round(ame, 5),
            "Sig": "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "")),
        })
    df_probit = pd.DataFrame(rows)
    df_probit.to_csv(OUT_TAB / "heckman_probit_coef.csv", index=False, encoding="utf-8")
    return df_probit


# ── Figura ────────────────────────────────────────────────────────────────────

def plotar_heckman(tab_comp: pd.DataFrame, df_emp_imr: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Painel 1: comparação β_negro
    ax = axes[0]
    modelos  = ["OLS\n(sem correção)", "Heckman\n(com IMR)"]
    betas    = [
        float(tab_comp.loc[tab_comp["Modelo"] == "OLS (sem correção)", "β_negro"].iloc[0]),
        float(tab_comp.loc[tab_comp["Modelo"] == "Heckman (com IMR)",  "β_negro"].iloc[0]),
    ]
    gap_pcts = [
        float(tab_comp.loc[tab_comp["Modelo"] == "OLS (sem correção)", "Gap (%)"].iloc[0]),
        float(tab_comp.loc[tab_comp["Modelo"] == "Heckman (com IMR)",  "Gap (%)"].iloc[0]),
    ]
    colors = ["#3498db", "#e74c3c"]
    bars   = ax.bar(modelos, betas, color=colors, alpha=0.85, edgecolor="black", linewidth=0.6)
    ax.axhline(0, color="black", linewidth=0.5)
    for bar, b, gp in zip(bars, betas, gap_pcts):
        ax.text(bar.get_x() + bar.get_width() / 2, b - 0.002,
                f"{b:.4f}\n({gp:.1f}%)", ha="center", va="top", fontsize=9.5, fontweight="bold")
    ax.set_ylabel("β_negro (log-pontos)")
    ax.set_title("Comparação: OLS vs Heckman\nβ_negro (gap racial)", fontsize=10)

    # Painel 2: distribuição IMR por grupo racial
    ax2 = axes[1]
    bins = np.linspace(0, df_emp_imr["imr"].quantile(0.99), 60)
    ax2.hist(df_emp_imr.loc[df_emp_imr["negro"] == 0, "imr"],
             bins=bins, alpha=0.6, color="#3498db", density=True, label="Branco")
    ax2.hist(df_emp_imr.loc[df_emp_imr["negro"] == 1, "imr"],
             bins=bins, alpha=0.6, color="#e74c3c", density=True, label="Negro")
    ax2.set_xlabel("IMR (Razão de Mills Inversa)")
    ax2.set_ylabel("Densidade")
    ax2.set_title("Distribuição da IMR por Grupo Racial\n(quanto maior → mais selecionado)", fontsize=10)
    ax2.legend()
    # Linhas de média
    for grp, cor in [(0, "#2980b9"), (1, "#c0392b")]:
        m = df_emp_imr.loc[df_emp_imr["negro"] == grp, "imr"].mean()
        ax2.axvline(m, color=cor, linewidth=1.5, linestyle="--",
                    label=f"Média {'branco' if grp==0 else 'negro'} = {m:.4f}")
    ax2.legend(fontsize=8)

    # Painel 3: Δβ decomposto em seleção vs. discriminação
    ax3 = axes[2]
    beta_ols  = betas[0]
    beta_heck = betas[1]
    delta     = beta_heck - beta_ols

    labels_d  = ["OLS\n(sem correção)", "Viés de\nseleção (Δ)", "Heckman\n(corrigido)"]
    vals      = [beta_ols, delta, beta_heck]
    bottoms   = [0, beta_ols, 0]
    cols_d    = ["#3498db", "#f39c12" if delta > 0 else "#27ae60", "#e74c3c"]
    for i, (v, b, c) in enumerate(zip(vals, bottoms, cols_d)):
        ax3.bar(i, v, bottom=b if i == 1 else 0, color=c, alpha=0.85,
                edgecolor="black", linewidth=0.6, width=0.5)
        ax3.text(i, (b + v / 2) if i == 1 else (v / 2),
                 f"{v:+.4f}", ha="center", va="center", fontsize=9.5, fontweight="bold",
                 color="white" if abs(v) > 0.005 else "black")
    ax3.set_xticks([0, 1, 2])
    ax3.set_xticklabels(labels_d)
    ax3.axhline(0, color="black", linewidth=0.5)
    ax3.set_ylabel("β_negro (log-pontos)")
    ax3.set_title(
        "Decomposição do Gap:\nDiscriminação + Viés de Seleção", fontsize=10
    )
    direction = "superestimado" if delta > 0 else "subestimado"
    ax3.text(0.5, 0.05,
             f"OLS {direction} o gap em {abs(delta)*100:.3f} log-pt\n(seleção por tolerância salarial dos negros)",
             ha="center", transform=ax3.transAxes, fontsize=8.5,
             bbox=dict(fc="lightyellow", ec="gray", alpha=0.9))

    plt.suptitle(
        "Correção de Seleção Amostral — Heckman Two-Step\n"
        "Gap Salarial Racial — PNAD Contínua 2016–2025",
        fontsize=11,
    )
    plt.tight_layout()
    fig.savefig(OUT_FIG / "heckman_selecao.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: heckman_selecao.png")


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_heckman_selecao(sample_frac_probit: float = 0.20) -> Dict:
    logger.info("=== Correção Heckman Two-Step — Gap Salarial Racial ===")

    # Carregamento
    df_sample, df_emp, df_pea_clean = _load_pea_sample(sample_frac_probit)

    # Estágio 1: Probit
    probit_res = _estimar_probit(df_sample)

    # IMR para os empregados
    logger.info("Calculando IMR para dataset de empregados...")
    df_emp_imr = _calcular_imr(df_emp, probit_res)
    logger.info(f"  IMR média: {df_emp_imr['imr'].mean():.5f}  "
                f"  IMR negro: {df_emp_imr.loc[df_emp_imr['negro']==1,'imr'].mean():.5f}  "
                f"  IMR branco: {df_emp_imr.loc[df_emp_imr['negro']==0,'imr'].mean():.5f}")

    # Estágio 2: OLS baseline e Heckman
    logger.info("Estágio 2: OLS baseline (sem IMR)...")
    ols_base = _estimar_ols_baseline(df_emp)
    logger.info(f"  β_negro OLS: {ols_base.params.get('negro', np.nan):.5f} "
                f"  SE: {ols_base.bse.get('negro', np.nan):.5f}")

    logger.info("Estágio 2: OLS com IMR (Heckman)...")
    ols_heck = _estimar_heckman_ols(df_emp_imr)
    logger.info(f"  β_negro Heckman: {ols_heck.params.get('negro', np.nan):.5f} "
                f"  SE: {ols_heck.bse.get('negro', np.nan):.5f}")
    logger.info(f"  λ (IMR): {ols_heck.params.get('imr', np.nan):.5f} "
                f"  p: {ols_heck.pvalues.get('imr', np.nan):.4f}")

    # Tabelas
    tab_comp   = _tabela_comparacao(probit_res, ols_base, ols_heck)
    tab_probit = _tabela_probit(probit_res)

    tab_comp.to_csv(OUT_TAB / "heckman_comparacao.csv", index=False, encoding="utf-8")
    tex_comp = tab_comp.to_latex(
        index=False, escape=True,
        caption=(
            r"Correção de Seleção Amostral — Heckman Two-Step. "
            r"OLS (sem correção): estimativa convencional que ignora que desempregados "
            r"são excluídos da amostra. Heckman (com IMR): $\hat{\beta}_{negro}$ "
            r"corrigido pela Razão de Mills Inversa $\lambda = \hat{\phi}(X\hat{\gamma}) "
            r"/ \hat{\Phi}(X\hat{\gamma})$. "
            r"Variável de exclusão: \texttt{media\_renda\_upa\_z} "
            r"(renda média da UPA, não incluída na equação de salários). "
            r"SEs clusterizados por UF. "
            r"$\lambda$ significativo implica viés de seleção confirmado. "
            r"PNAD Contínua 2016--2025."
        ),
        label="tab:heckman_comparacao",
    )
    (OUT_TAB / "heckman_comparacao.tex").write_text(tex_comp, encoding="utf-8")

    # Figura
    plotar_heckman(tab_comp, df_emp_imr)

    # Sumário
    b_ols  = ols_base.params.get("negro", np.nan)
    b_heck = ols_heck.params.get("negro", np.nan)
    b_imr  = ols_heck.params.get("imr", np.nan)
    p_imr  = ols_heck.pvalues.get("imr", np.nan)
    delta  = b_heck - b_ols

    print("\n── SUMÁRIO: Heckman Two-Step ──")
    print(f"  β_negro OLS (sem correção): {b_ols:.5f}  "
          f"  ({(np.exp(b_ols)-1)*100:.2f}%)")
    print(f"  β_negro Heckman (corrigido): {b_heck:.5f}  "
          f"  ({(np.exp(b_heck)-1)*100:.2f}%)")
    print(f"  Δβ (Heckman − OLS): {delta:+.5f}")
    print(f"  λ (IMR): {b_imr:.5f}  p={p_imr:.4f}  "
          f"  → {'viés de seleção CONFIRMADO' if p_imr < 0.05 else 'viés de seleção NÃO detectado'}")
    direction = "superestimado" if delta > 0 else "subestimado"
    mecanismo = (
        "OLS captura discriminação + tolerância salarial dos negros ao acesso ao emprego"
        if delta > 0 else
        "OLS não captura que negros empregados são positivamente selecionados"
    )
    print(f"  Conclusão: gap salarial racial está {direction} pelo OLS em {abs(delta)*100:.3f} log-pt")
    print(f"             → {mecanismo}")

    return {
        "probit_res":    probit_res,
        "ols_baseline":  ols_base,
        "ols_heckman":   ols_heck,
        "df_emp_imr":    df_emp_imr,
        "tab_comparacao": tab_comp,
        "tab_probit":    tab_probit,
    }
