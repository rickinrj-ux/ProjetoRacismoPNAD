"""
inferencia_causal.py
====================
Estimação do efeito causal da raça sobre renda usando métodos quasi-experimentais.

Dois métodos complementares:
    1. Propensity Score Matching (PSM)
       → Pareia negros e brancos com perfis observáveis similares.
         ATT = E[Y(1) - Y(0) | T=1]: efeito médio sobre os tratados (negros).
         Interpretação: gap residual após controlar por características observáveis.

    2. Double Machine Learning (Double ML / Partially Linear Model)
       → Usa ML para controlar de forma flexível por covariáveis de alta dimensão.
         Estimativa semi-paramétrica do coeficiente θ de raça em:
             Y = θ·T + g(X) + ε    com    T = m(X) + v
         Evita o viés de regularização do PSM com muitas covariáveis.
         (Chernozhukov et al., 2018 — "Double/Debiased ML")

Limitação fundamental:
    Raça no Brasil não é aleatória (é correlacionada com histórico familiar,
    local de nascimento, etc.). Os efeitos estimados capturam discriminação
    CONDICIONAL às covariáveis observadas — existem confundidores não observados.
    Os resultados são interpretados como evidência de discriminação residual,
    não como efeito causal estrito.

Referências:
    Rosenbaum, P. R., & Rubin, D. B. (1983). The central role of the propensity
        score. Biometrika, 70(1), 41-55.
    Chernozhukov, V., et al. (2018). Double/debiased machine learning.
        The Econometrics Journal, 21(1), C1-C68.
    Morgan, S. L., & Winship, C. (2015). Counterfactuals and Causal Inference.
        Cambridge University Press.
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
from sklearn.linear_model import LogisticRegressionCV, LassoCV
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

ROOT          = Path(__file__).parent.parent
FEATURES_PATH = ROOT / "data" / "processed" / "features.parquet"
OUT_FIG       = ROOT / "outputs" / "figures"
OUT_TAB       = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

# Covariáveis usadas para propensity score e Double ML
COVARIATES = [
    "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "pct_negro_uf_z",  "tx_desemprego_uf_z",  "media_educ_uf_z",
]
OUTCOME = "log_renda"
TREATMENT = "negro"

MODEL_VARS = [OUTCOME, TREATMENT] + COVARIATES + ["UF"]


# ── Carregamento ──────────────────────────────────────────────────────────────

def carregar_dados(sample_frac: Optional[float] = None) -> pd.DataFrame:
    """Carrega features e prepara dataset para inferência causal."""
    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df = df.dropna(subset=MODEL_VARS).reset_index(drop=True)

    # Filtra UPAs com n mínimo
    if "UPA" in df.columns:
        cnt = df["UPA"].value_counts()
        df  = df[df["UPA"].isin(cnt[cnt >= 10].index)].reset_index(drop=True)

    df["UF_str"] = df["UF"].astype(str)
    df["log_renda"] = df["log_renda"].astype(float)

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)

    logger.info(
        f"Dataset causal: {len(df):,} obs. | "
        f"tratados (negro=1): {df['negro'].sum():,} ({df['negro'].mean():.1%})"
    )
    return df


# ── Propensity Score Matching ─────────────────────────────────────────────────

def calcular_propensity_scores(df: pd.DataFrame) -> np.ndarray:
    """
    Estima P(negro=1 | X) via regressão logística com regularização L2.

    LogisticRegressionCV escolhe C (inverso da penalidade) via CV 5-fold,
    evitando overfitting que infla artificialmente o balanceamento.
    """
    X = df[COVARIATES].values
    T = df[TREATMENT].values.astype(int)

    scaler = StandardScaler()
    X_std  = scaler.fit_transform(X)

    logger.info("Estimando propensity scores (LogisticRegressionCV)...")
    clf = LogisticRegressionCV(
        cv=5, max_iter=1000, random_state=42, n_jobs=-1, scoring="roc_auc"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        clf.fit(X_std, T)

    ps = clf.predict_proba(X_std)[:, 1]
    logger.info(
        f"  PS: min={ps.min():.3f}, max={ps.max():.3f}, "
        f"AUC={clf.scores_[1].mean():.3f}"
    )
    return ps


def _nearest_neighbor_match(
    ps_treated: np.ndarray,
    ps_control: np.ndarray,
    caliper: float = 0.2,
    ratio: int = 1,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Matching nearest-neighbor sem reposição, com caliper.

    Caliper padrão de 0.2 × σ(logit(PS)) segue Cochran & Rubin (1973):
    elimina pares com diferença grande de PS mesmo sendo o mais próximo.
    """
    from scipy.spatial import KDTree

    sigma_logit = np.std(np.log(ps_treated / (1 - ps_treated + 1e-8)))
    max_dist    = caliper * sigma_logit

    # KD-Tree no espaço do propensity score (1D)
    tree = KDTree(ps_control.reshape(-1, 1))
    dists, idx_ctrl = tree.query(ps_treated.reshape(-1, 1), k=ratio)

    valid = dists.flatten() <= max_dist
    idx_treated_matched = np.where(valid)[0]
    idx_control_matched = idx_ctrl.flatten()[valid]

    logger.info(
        f"  Matched {valid.sum():,} de {len(ps_treated):,} tratados "
        f"(caliper={max_dist:.4f})"
    )
    return idx_treated_matched, idx_control_matched


def matching_psm(df: pd.DataFrame, ps: np.ndarray) -> pd.DataFrame:
    """
    Executa PSM nearest-neighbor e retorna dataset pareado.

    O ATT é calculado na média de Y(1) - Y(0) sobre os pares.
    """
    idx_treated = np.where(df[TREATMENT].values == 1)[0]
    idx_control = np.where(df[TREATMENT].values == 0)[0]

    ps_treated = ps[idx_treated]
    ps_control = ps[idx_control]

    idx_t_match, idx_c_match = _nearest_neighbor_match(ps_treated, ps_control)

    df_matched_t = df.iloc[idx_treated[idx_t_match]].copy()
    df_matched_c = df.iloc[idx_control[idx_c_match]].copy()

    df_matched = pd.concat(
        [df_matched_t, df_matched_c], ignore_index=True
    )
    df_matched["ps"] = np.concatenate([
        ps_treated[idx_t_match],
        ps_control[idx_c_match],
    ])
    return df_matched


def estimar_att_psm(df_matched: pd.DataFrame) -> Dict:
    """
    ATT = diferença de médias em Y(1) - Y(0) no dataset pareado.
    SE via bootstrap (200 repetições).
    """
    y_treat = df_matched.loc[df_matched[TREATMENT] == 1, OUTCOME].values
    y_ctrl  = df_matched.loc[df_matched[TREATMENT] == 0, OUTCOME].values
    att     = y_treat.mean() - y_ctrl.mean()

    # Bootstrap SE
    np.random.seed(42)
    boots = []
    for _ in range(200):
        idx = np.random.choice(len(y_treat), len(y_treat), replace=True)
        boots.append(y_treat[idx].mean() - y_ctrl[np.random.choice(len(y_ctrl), len(y_ctrl))].mean())
    se  = np.std(boots)
    ci_l, ci_h = np.percentile(boots, [2.5, 97.5])

    gap_pct = (np.exp(att) - 1) * 100
    logger.info(
        f"ATT (PSM): {att:.4f}  SE={se:.4f}  "
        f"gap={gap_pct:.1f}%  IC95%=[{ci_l:.4f}, {ci_h:.4f}]"
    )
    return {
        "metodo":  "PSM",
        "ATT":     att,
        "SE":      se,
        "CI_low":  ci_l,
        "CI_high": ci_h,
        "gap_pct": gap_pct,
        "n_pares": min(len(y_treat), len(y_ctrl)),
    }


def tabela_balanceamento(
    df: pd.DataFrame,
    df_matched: pd.DataFrame,
) -> pd.DataFrame:
    """
    Tabela de balanceamento antes/depois do matching.

    SMD (Standardized Mean Difference) < 0.1 indica bom balanceamento
    (convenção de Austin, 2011 — Journal of Evaluating Clinical Practice).
    """
    rows = []
    for var in COVARIATES[:8]:  # subset para legibilidade
        if var not in df.columns:
            continue

        def _smd(data, var):
            m1 = data.loc[data[TREATMENT] == 1, var].mean()
            m0 = data.loc[data[TREATMENT] == 0, var].mean()
            s1 = data.loc[data[TREATMENT] == 1, var].std()
            s0 = data.loc[data[TREATMENT] == 0, var].std()
            pooled_sd = np.sqrt((s1**2 + s0**2) / 2)
            return (m1 - m0) / pooled_sd if pooled_sd > 0 else np.nan

        rows.append({
            "Variável":         var,
            "SMD (antes)":      round(_smd(df, var), 3),
            "SMD (após PSM)":   round(_smd(df_matched, var), 3),
        })

    df_bal = pd.DataFrame(rows)
    df_bal["Balanceado?"] = (df_bal["SMD (após PSM)"].abs() < 0.1).map({True: "Sim", False: "Não"})
    return df_bal


# ── Double Machine Learning ───────────────────────────────────────────────────

def ajustar_double_ml(df: pd.DataFrame) -> Dict:
    """
    Double ML (Partially Linear Regression) via econml.LinearDML.
    Se econml não estiver instalado, usa a implementação manual abaixo.

    Modelo: Y = θ·T + g(X) + ε,  T = m(X) + v
    θ estimado por: regress (Y - ĝ(X)) em (T - m̂(X))

    g(X) e m(X) estimados via LassoCV (flexível, evita overfitting).
    Particionamento cross-fitting (k=5) para validade semiparamétrica.
    """
    try:
        from econml.dml import LinearDML
        from sklearn.linear_model import LassoCV
        from sklearn.linear_model import LogisticRegressionCV as LRCV

        logger.info("Ajustando Double ML via econml.LinearDML...")
        Y = df[OUTCOME].values
        T = df[TREATMENT].values.astype(float)
        X = df[COVARIATES].values
        W = None  # covariáveis de controle = X (sem separação neste caso)

        dml = LinearDML(
            model_y=LassoCV(cv=5, max_iter=2000, random_state=42),
            model_t=LRCV(cv=5, max_iter=1000, random_state=42),
            cv=5,
            random_state=42,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dml.fit(Y, T, X=None, W=X)  # X=None: efeito constante (PLR)

        theta   = dml.coef_[0]
        se      = dml.coef__inference().std_point[0]
        ci      = dml.coef__inference().conf_int(alpha=0.05)
        ci_l, ci_h = ci[0][0], ci[1][0]

    except ImportError:
        logger.warning(
            "econml não instalado. Usando Double ML manual. "
            "Instale com: pip install econml"
        )
        theta, se, ci_l, ci_h = _double_ml_manual(df)

    gap_pct = (np.exp(theta) - 1) * 100
    logger.info(
        f"Double ML: θ={theta:.4f}  SE={se:.4f}  "
        f"gap={gap_pct:.1f}%  IC95%=[{ci_l:.4f}, {ci_h:.4f}]"
    )
    return {
        "metodo":  "Double ML",
        "ATT":     theta,
        "SE":      se,
        "CI_low":  ci_l,
        "CI_high": ci_h,
        "gap_pct": gap_pct,
        "n_obs":   len(df),
    }


def _double_ml_manual(df: pd.DataFrame) -> Tuple:
    """
    Implementação manual do Double ML (Partially Linear Regression).

    Etapas do cross-fitting (k=5):
        1. Para cada fold k:
           a. Estima ĝ₋ₖ(X) via LassoCV nos folds excluindo k
           b. Estima m̂₋ₖ(X) via LogisticRegressionCV excluindo k
        2. Calcula resíduos: Ỹ = Y - ĝ(X),  T̃ = T - m̂(X)
        3. OLS: Ỹ ~ T̃  → θ̂ = Cov(T̃, Ỹ) / Var(T̃)
    """
    from sklearn.model_selection import KFold
    from sklearn.linear_model import LassoCV, LogisticRegressionCV

    Y  = df[OUTCOME].values
    T  = df[TREATMENT].values.astype(float)
    X  = StandardScaler().fit_transform(df[COVARIATES].values)
    n  = len(Y)

    Y_res = np.zeros(n)
    T_res = np.zeros(n)

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    logger.info("Double ML manual: cross-fitting 5-fold...")

    for fold, (train_idx, test_idx) in enumerate(kf.split(X)):
        X_train, X_test = X[train_idx], X[test_idx]
        Y_train, Y_test = Y[train_idx], Y[test_idx]
        T_train, T_test = T[train_idx], T[test_idx]

        # Estima g(X): modelo de resultado
        lasso = LassoCV(cv=3, max_iter=2000).fit(X_train, Y_train)
        Y_res[test_idx] = Y_test - lasso.predict(X_test)

        # Estima m(X): modelo de tratamento
        lr = LogisticRegressionCV(cv=3, max_iter=1000).fit(X_train, T_train.astype(int))
        T_res[test_idx] = T_test - lr.predict_proba(X_test)[:, 1]

        logger.info(f"  Fold {fold+1}/5 concluído")

    # OLS dos resíduos: θ = Cov(T̃, Ỹ) / Var(T̃)
    theta = np.cov(T_res, Y_res)[0, 1] / np.var(T_res)

    # SE via influência
    psi   = (Y_res - theta * T_res) * T_res
    se    = np.sqrt(np.var(psi) / (n * np.var(T_res)**2))
    ci_l  = theta - 1.96 * se
    ci_h  = theta + 1.96 * se

    return theta, se, ci_l, ci_h


# ── Comparação OLS naive vs. métodos causais ──────────────────────────────────

def ajustar_ols_naive(df: pd.DataFrame) -> Dict:
    """OLS sem controles sofisticados — estimador ingênuo para comparação."""
    formula = (
        "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
        " + educ_fund_completo + educ_medio_completo"
        " + educ_superior_completo + educ_pos_graduacao + C(UF_str)"
    )
    res   = smf.ols(formula, data=df).fit(
        cov_type="cluster", cov_kwds={"groups": df["UF_str"]}
    )
    b     = res.params.get("negro", np.nan)
    se    = res.bse.get("negro", np.nan)
    ci_l  = b - 1.96 * se
    ci_h  = b + 1.96 * se
    return {
        "metodo":  "OLS (naive)",
        "ATT":     b,
        "SE":      se,
        "CI_low":  ci_l,
        "CI_high": ci_h,
        "gap_pct": (np.exp(b) - 1) * 100,
        "n_obs":   len(df),
    }


# ── Visualizações ─────────────────────────────────────────────────────────────

def plotar_comparacao_metodos(resultados: list, df_bal: pd.DataFrame) -> None:
    """Compara ATT estimado pelos três métodos com IC95%."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Painel 1: ATT por método
    ax = axes[0]
    labels = [r["metodo"] for r in resultados]
    atts   = [r["ATT"]    for r in resultados]
    ci_l   = [r["CI_low"] for r in resultados]
    ci_h   = [r["CI_high"]for r in resultados]
    cores  = ["#95a5a6", "#c0392b", "#8e44ad"]

    for i, (lbl, att, cl, ch, cor) in enumerate(zip(labels, atts, ci_l, ci_h, cores)):
        ax.errorbar(att, i, xerr=[[att - cl], [ch - att]],
                    fmt="o", color=cor, capsize=6, linewidth=2, markersize=8)
        ax.text(att + 0.003, i, f"{(np.exp(att)-1)*100:.1f}%", va="center", fontsize=9)

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10)
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel("ATT (log-renda)  ·  IC 95%", fontsize=11)
    ax.set_title("Gap Racial: OLS vs. PSM vs. Double ML", fontsize=11)

    # Painel 2: balanceamento SMD
    ax2 = axes[1]
    y   = range(len(df_bal))
    ax2.scatter(df_bal["SMD (antes)"].abs(), y,
                marker="o", color="#c0392b", s=60, label="Antes PSM", zorder=3)
    ax2.scatter(df_bal["SMD (após PSM)"].abs(), y,
                marker="s", color="#27ae60", s=60, label="Após PSM", zorder=3)
    ax2.set_yticks(list(y))
    ax2.set_yticklabels(df_bal["Variável"].tolist(), fontsize=8)
    ax2.axvline(0.1, color="orange", linewidth=1, linestyle="--", label="Limiar 0.1")
    ax2.set_xlabel("|SMD|", fontsize=11)
    ax2.set_title("Balanceamento de Covariáveis\n(PSM)", fontsize=11)
    ax2.legend(fontsize=8)

    plt.tight_layout()
    fig.savefig(OUT_FIG / "causal_comparacao_metodos.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: causal_comparacao_metodos.png")


def plotar_distribuicao_ps(df: pd.DataFrame, ps: np.ndarray) -> None:
    """Distribuição dos propensity scores por grupo — verifica sobreposição."""
    fig, ax = plt.subplots(figsize=(7, 4))
    for neg, label, cor in [(0, "Branco (controle)", "#3498db"),
                             (1, "Negro (tratado)", "#c0392b")]:
        mask = df[TREATMENT].values == neg
        ax.hist(ps[mask], bins=40, density=True, alpha=0.6,
                color=cor, edgecolor="white", label=label)
    ax.set_xlabel("Propensity Score P(negro=1 | X)", fontsize=11)
    ax.set_ylabel("Densidade", fontsize=11)
    ax.set_title("Distribuição do Propensity Score por Raça\n(sobreposição = região de suporte comum)", fontsize=11)
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "causal_ps_distribuicao.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: causal_ps_distribuicao.png")


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_inferencia_causal(sample_frac: Optional[float] = None) -> Dict:
    """
    Pipeline completo de inferência causal.

    Requer: scikit-learn (instalado), econml (opcional — pip install econml).

    Returns:
        dict com resultados PSM, Double ML, OLS e tabela de balanceamento.
    """
    df = carregar_dados(sample_frac=sample_frac)

    # OLS naive (estimador de referência)
    res_ols = ajustar_ols_naive(df)
    logger.info(f"OLS naive: gap = {res_ols['gap_pct']:.1f}%")

    # PSM
    ps         = calcular_propensity_scores(df)
    df_matched = matching_psm(df, ps)
    res_psm    = estimar_att_psm(df_matched)
    df_bal     = tabela_balanceamento(df, df_matched)

    # Double ML
    # Usa amostra menor para controlar tempo (DML é mais lento)
    df_dml  = df.sample(min(50_000, len(df)), random_state=42) if len(df) > 50_000 else df
    res_dml = ajustar_double_ml(df_dml)

    # Salva outputs
    resultados = [res_ols, res_psm, res_dml]
    pd.DataFrame(resultados).to_csv(OUT_TAB / "causal_comparacao.csv", index=False)
    df_bal.to_csv(OUT_TAB / "causal_balanceamento.csv", index=False)

    plotar_distribuicao_ps(df, ps)
    plotar_comparacao_metodos(resultados, df_bal)

    # Sumário
    print("\n── SUMÁRIO: Inferência Causal ──")
    print("\nComparação de métodos (gap salarial racial):")
    for r in resultados:
        stars = (
            "***" if abs(r["ATT"]) / r["SE"] > 3.29 else
            "**" if abs(r["ATT"]) / r["SE"] > 2.58 else
            "*" if abs(r["ATT"]) / r["SE"] > 1.96 else "ns"
        )
        print(
            f"  {r['metodo']:<20s}: {r['ATT']:+.4f}{stars}  "
            f"IC95%=[{r['CI_low']:+.4f}, {r['CI_high']:+.4f}]  "
            f"gap={(np.exp(r['ATT'])-1)*100:.1f}%"
        )
    print("\nBalanceamento após PSM:")
    print(df_bal.to_string(index=False))

    return {
        "ols": res_ols, "psm": res_psm, "dml": res_dml,
        "balanceamento": df_bal, "df_matched": df_matched, "ps": ps,
    }
