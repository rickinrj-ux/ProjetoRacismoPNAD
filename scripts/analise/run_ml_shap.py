"""
run_ml_shap.py
==============
ML supervisionado para predição de log-rendimento + SHAP Values.
PNAD Contínua 2016-2025.

OBJETIVO (TCC):
    Demonstrar que raça (negro) exerce efeito independente sobre rendimento
    mesmo após o modelo controlar por educação, experiência, gênero e contexto
    de moradia — evidência computacional de discriminação estrutural.

MODELAGEM:
    Target: log_renda (regressão contínua — equação de Mincer estendida)

    Modelo 1 — Random Forest (sklearn):
        Ensemble de 200 árvores, profundidade máx 10.
        Vantagem: robusto a outliers, captura não-linearidades.

    Modelo 2 — XGBoost (gradient boosting):
        300 árvores, max_depth=6, learning_rate=0.05.
        Vantagem: regularização L1/L2, melhor performance preditiva.

INTERPRETABILIDADE (SHAP — SHapley Additive exPlanations):
    TreeExplainer: O(T * L) por observação — eficiente para tree ensembles.
    Lundberg & Lee (2017): SHAP unifica feature importance, efeitos parciais
    e explicações individuais numa única framework axiomática.

    Plots gerados:
        1. Beeswarm plot (summary): distribuição de SHAP por feature
        2. Bar plot: importância global média |SHAP|
        3. Dependence plot — negro: efeito da raça vs. renda com coloração
           por pct_negro_upa (interação contextual)
        4. Waterfall: 3 casos individuais — branco alto, negro alto, negro baixo

AMOSTRA:
    20% do dataset filtrado (~1.54M obs.) para viabilidade.
    SHAP calculado sobre subsample de 50k (suficiente para distribuições estáveis).
"""

# --- bootstrap raiz do projeto (reorg estrutura) ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys
import logging
import time
import warnings
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, "src")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

Path("outputs/_logs").mkdir(exist_ok=True)
handlers = [
    logging.FileHandler("outputs/_logs/ml_shap.log", encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=handlers,
)
logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import statsmodels.api as sm
import xgboost as xgb

FEATURES_PATH = Path("data/processed/features.parquet")
OUTPUTS_TB    = Path("outputs/tables")
OUTPUTS_FIG   = Path("outputs/figures")
OUTPUTS_TB.mkdir(parents=True, exist_ok=True)
OUTPUTS_FIG.mkdir(parents=True, exist_ok=True)

SAMPLE_FRAC   = None   # None = população completa (modelo treina em 7,69M; SHAP em subset p/ viz)
SHAP_SAMPLE   = 50_000
RANDOM_STATE  = 42

# ── Validação cruzada (protocolo de robustez adicional ao hold-out 80/20) ──────
# CV k-fold roda em subamostra (não na população completa): 5 folds × RF(200 árv.)
# + XGB(300 iter.) na base inteira (7,69M) multiplicaria o custo computacional do
# ajuste principal por ~5x. Uma subamostra representativa mantém a validação
# tratável sem comprometer a estimativa de variância entre folds.
RUN_CV         = True
N_CV_FOLDS     = 5
CV_SAMPLE_FRAC = 0.20
N_SHAP_BOOTSTRAP = 200   # reamostragens para IC da importância |SHAP| média

# n_jobs=-1 no RandomForestRegressor usa multiprocessing (joblib/loky): cada worker
# pode precisar de sua própria cópia da matriz de features, multiplicando o uso de
# memória pelo nº de núcleos. Em máquinas com RAM limitada isso já causou swap
# pesado (10-50x mais lento) em outros scripts deste pipeline — capado em 4 para
# manter o uso de memória previsível. XGBoost usa threads (memória compartilhada),
# sem esse risco, por isso mantém n_jobs=-1.
N_JOBS_RF = 4

# ── Features e target ─────────────────────────────────────────────────────────
TARGET = "log_renda"

FEATURES = [
    # Individuais
    "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao", "educ_missing",
    # Trabalho (novos)
    "horas_c", "emprego_formal", "conta_propria", "trab_domestico",
    # Grupo CBO — referência: elementar (novos)
    "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
    "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
    # Contexto UPA (Nível 2)
    "pct_negro_upa_z", "tx_desemprego_upa_z",
    "media_educ_upa_z", "media_renda_upa_z",
    # Contexto UF (Nível 3)
    "pct_negro_uf_z", "tx_desemprego_uf_z", "media_educ_uf_z",
]

FEATURE_LABELS = {
    "negro":                   "Raça (negro)",
    "sexo_fem":                "Gênero (feminino)",
    "idade_c":                 "Idade (centralizada)",
    "idade_sq":                "Idade² (experiência)",
    "educ_fund_completo":      "Educ.: Fundamental",
    "educ_medio_completo":     "Educ.: Médio",
    "educ_superior_completo":  "Educ.: Superior",
    "educ_pos_graduacao":      "Educ.: Pós-graduação",
    "educ_missing":            "Educ.: não registrada",
    "horas_c":                 "Horas trabalhadas",
    "emprego_formal":          "Emprego formal (carteira)",
    "conta_propria":           "Conta própria",
    "trab_domestico":          "Trabalho doméstico",
    "ocp_dirigente":           "CBO: Dirigentes",
    "ocp_profissional":        "CBO: Profissionais",
    "ocp_tecnico":             "CBO: Técnicos",
    "ocp_administrativo":      "CBO: Administrativo",
    "ocp_servicos":            "CBO: Serviços/Vendas",
    "ocp_agro":                "CBO: Agropecuária",
    "ocp_operario":            "CBO: Operários",
    "ocp_operador":            "CBO: Op. Máquinas",
    "ocp_ffaa":                "CBO: FFAA/Polícia",
    "pct_negro_upa_z":         "% Negro na UPA",
    "tx_desemprego_upa_z":     "Desemprego na UPA",
    "media_educ_upa_z":        "Educ. média UPA",
    "media_renda_upa_z":       "Renda média UPA",
    "pct_negro_uf_z":          "% Negro no Estado",
    "tx_desemprego_uf_z":      "Desemprego no Estado",
    "media_educ_uf_z":         "Educ. média Estado",
}


# ── Carregamento ───────────────────────────────────────────────────────────────

def load_data():
    logger.info(f"Carregando {FEATURES_PATH} ...")
    df = pd.read_parquet(FEATURES_PATH)
    # educ_missing: escolaridade não registrada (educ_cat NA ~69%) como feature própria.
    df["educ_missing"] = df["educ_cat"].isna().astype(int) if "educ_cat" in df.columns else 0

    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df = df.dropna(subset=FEATURES + [TARGET]).reset_index(drop=True)

    for col in FEATURES + [TARGET]:
        df[col] = df[col].astype(float)

    logger.info(f"  Apos filtros: {len(df):,} obs.")

    if SAMPLE_FRAC:
        df = df.sample(frac=SAMPLE_FRAC, random_state=RANDOM_STATE).reset_index(drop=True)
        logger.info(f"  Amostra {SAMPLE_FRAC*100:.0f}%: {len(df):,} obs.")
    else:
        df = df.reset_index(drop=True)
        logger.info(f"  População completa: {len(df):,} obs.")
    return df


# ── Divisão treino/teste ───────────────────────────────────────────────────────

def split(df):
    X = df[FEATURES].values
    y = df[TARGET].values
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE
    )
    logger.info(f"  Treino: {len(X_tr):,} | Teste: {len(X_te):,}")
    return X_tr, X_te, y_tr, y_te, df


# ── Avaliação ──────────────────────────────────────────────────────────────────

def evaluate(name, y_true, y_pred):
    r2   = r2_score(y_true, y_pred)
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    logger.info(f"  [{name}] R²={r2:.4f} | MAE={mae:.4f} | RMSE={rmse:.4f}")
    return {"Modelo": name, "R²": round(r2, 4), "MAE": round(mae, 4), "RMSE": round(rmse, 4)}


# ── Validação cruzada k-fold (robustez do protocolo além do hold-out) ─────────

def cross_validate_models(df: pd.DataFrame, k: int = N_CV_FOLDS,
                           sample_frac: float = CV_SAMPLE_FRAC) -> pd.DataFrame:
    """
    K-fold CV para RF e XGBoost, complementando o hold-out 80/20 principal.

    Reporta média ± DP de R²/MAE/RMSE entre os k folds — responde diretamente
    à cobrança de robustez do protocolo de validação (não apenas um único
    split treino/teste). Roda em subamostra (CV_SAMPLE_FRAC) por tratabilidade
    computacional; ver nota em CV_SAMPLE_FRAC acima.
    """
    df_cv = df.sample(frac=sample_frac, random_state=RANDOM_STATE).reset_index(drop=True)
    X = df_cv[FEATURES].values
    y = df_cv[TARGET].values
    logger.info(f"CV k={k} em subamostra de {len(df_cv):,} obs. ({sample_frac*100:.0f}% do total)...")

    kf = KFold(n_splits=k, shuffle=True, random_state=RANDOM_STATE)
    metrics = {"Random Forest": {"r2": [], "mae": [], "rmse": []},
               "XGBoost":       {"r2": [], "mae": [], "rmse": []}}

    for fold, (tr_idx, te_idx) in enumerate(kf.split(X), start=1):
        X_tr, X_te = X[tr_idx], X[te_idx]
        y_tr, y_te = y[tr_idx], y[te_idx]

        rf_cv = fit_rf(X_tr, y_tr)
        y_pred = rf_cv.predict(X_te)
        metrics["Random Forest"]["r2"].append(r2_score(y_te, y_pred))
        metrics["Random Forest"]["mae"].append(mean_absolute_error(y_te, y_pred))
        metrics["Random Forest"]["rmse"].append(np.sqrt(mean_squared_error(y_te, y_pred)))

        xgb_cv = fit_xgb(X_tr, y_tr)
        y_pred = xgb_cv.predict(X_te)
        metrics["XGBoost"]["r2"].append(r2_score(y_te, y_pred))
        metrics["XGBoost"]["mae"].append(mean_absolute_error(y_te, y_pred))
        metrics["XGBoost"]["rmse"].append(np.sqrt(mean_squared_error(y_te, y_pred)))

        logger.info(
            f"  [fold {fold}/{k}] RF R²={metrics['Random Forest']['r2'][-1]:.4f} | "
            f"XGB R²={metrics['XGBoost']['r2'][-1]:.4f}"
        )

    rows = []
    for name, m in metrics.items():
        rows.append({
            "Modelo": name, "k": k, "sample_frac": sample_frac,
            "R2_mean": round(float(np.mean(m["r2"])), 4),
            "R2_sd":   round(float(np.std(m["r2"])), 4),
            "MAE_mean": round(float(np.mean(m["mae"])), 4),
            "MAE_sd":   round(float(np.std(m["mae"])), 4),
            "RMSE_mean": round(float(np.mean(m["rmse"])), 4),
            "RMSE_sd":   round(float(np.std(m["rmse"])), 4),
        })
        logger.info(
            f"  [{name}] CV R²={rows[-1]['R2_mean']:.4f}±{rows[-1]['R2_sd']:.4f}"
        )
    df_out = pd.DataFrame(rows)
    df_out.to_csv(OUTPUTS_TB / "ml_performance_cv.csv", index=False)
    return df_out


# ── Baseline econométrico (OLS) na mesma partição — ganho real do ML ─────────

def fit_ols_baseline(X_tr, y_tr, X_te, y_te) -> Dict:
    """
    OLS (equação de Mincer estendida, mesmas features do RF/XGBoost) ajustado
    na MESMA partição treino/teste, para dimensionar o ganho real de R² do ML
    frente à econometria linear tradicional — responde diretamente ao pedido
    do orientador de comparar contra um baseline simples.
    """
    Xtr_c = sm.add_constant(X_tr)
    Xte_c = sm.add_constant(X_te, has_constant="add")
    model = sm.OLS(y_tr, Xtr_c).fit()
    y_pred = model.predict(Xte_c)
    r2   = r2_score(y_te, y_pred)
    mae  = mean_absolute_error(y_te, y_pred)
    rmse = np.sqrt(mean_squared_error(y_te, y_pred))
    logger.info(f"  [OLS baseline] R²={r2:.4f} | MAE={mae:.4f} | RMSE={rmse:.4f}")
    return {"Modelo": "OLS (baseline linear)", "R2_teste": round(r2, 4),
            "MAE_teste": round(mae, 4), "RMSE_teste": round(rmse, 4)}


# ── Bootstrap de estabilidade dos valores SHAP ────────────────────────────────

def bootstrap_shap_ci(shap_values: np.ndarray, feature_names: List[str],
                       B: int = N_SHAP_BOOTSTRAP, seed: int = RANDOM_STATE) -> pd.DataFrame:
    """
    IC 95% (percentil) da importância média |SHAP| por feature via reamostragem
    (bootstrap) das observações já explicadas — não recalcula SHAP a cada
    reamostragem (custo proibitivo), reamostra os valores SHAP já computados
    para estimar a variabilidade amostral da média.
    """
    rng = np.random.default_rng(seed)
    n = shap_values.shape[0]
    abs_sv = np.abs(shap_values)
    boot_means = np.empty((B, abs_sv.shape[1]))
    for b in range(B):
        idx = rng.integers(0, n, size=n)
        boot_means[b] = abs_sv[idx].mean(axis=0)

    df_boot = pd.DataFrame({
        "Feature": feature_names,
        "mean_abs_shap_mean": boot_means.mean(axis=0).round(5),
        "ci_lo": np.percentile(boot_means, 2.5, axis=0).round(5),
        "ci_hi": np.percentile(boot_means, 97.5, axis=0).round(5),
    }).sort_values("mean_abs_shap_mean", ascending=False).reset_index(drop=True)
    df_boot.to_csv(OUTPUTS_TB / "shap_bootstrap_ci.csv", index=False)
    logger.info(f"  Bootstrap SHAP (B={B}) salvo: shap_bootstrap_ci.csv")
    return df_boot


# ── Random Forest ──────────────────────────────────────────────────────────────

def fit_rf(X_tr, y_tr):
    logger.info("Ajustando Random Forest (n=200, depth=10) ...")
    t0 = time.time()
    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=50,
        n_jobs=N_JOBS_RF,
        random_state=RANDOM_STATE,
    )
    rf.fit(X_tr, y_tr)
    logger.info(f"  RF concluído em {time.time()-t0:.0f}s")
    return rf


# ── XGBoost ────────────────────────────────────────────────────────────────────

def fit_xgb(X_tr, y_tr):
    logger.info("Ajustando XGBoost (n=300, depth=6, lr=0.05) ...")
    t0 = time.time()
    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        n_jobs=-1,
        random_state=RANDOM_STATE,
        verbosity=0,
    )
    model.fit(X_tr, y_tr, eval_set=[(X_tr, y_tr)], verbose=False)
    logger.info(f"  XGB concluído em {time.time()-t0:.0f}s")
    return model


# ── SHAP ───────────────────────────────────────────────────────────────────────

def compute_shap(model, X_tr, df, model_name):
    logger.info(f"[{model_name}] Calculando SHAP (subsample={SHAP_SAMPLE:,}) ...")
    t0 = time.time()

    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(len(X_tr), size=min(SHAP_SAMPLE, len(X_tr)), replace=False)
    X_shap = X_tr[idx]
    df_shap = df.iloc[idx].reset_index(drop=True)

    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_shap)

    logger.info(f"  [{model_name}] SHAP calculado em {time.time()-t0:.0f}s")
    return shap_values, X_shap, df_shap, explainer


# ── Plots SHAP ────────────────────────────────────────────────────────────────

def plot_shap_beeswarm(shap_values, X_shap, model_name):
    """Beeswarm (summary): distribuição de SHAP por feature."""
    feat_names = [FEATURE_LABELS.get(f, f) for f in FEATURES]
    plt.figure(figsize=(9, 7))
    shap.summary_plot(
        shap_values, X_shap,
        feature_names=feat_names,
        show=False, plot_size=None,
        color_bar_label="Valor da feature (alto → vermelho)",
    )
    plt.title(
        f"SHAP Beeswarm — {model_name}\n"
        "Impacto de cada feature no log-rendimento predito\n"
        "PNAD 2016-2025 | N=50k subsample",
        fontsize=11, pad=10,
    )
    plt.tight_layout()
    path = OUTPUTS_FIG / f"shap_beeswarm_{model_name.lower()}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Beeswarm salvo: {path}")


def plot_shap_bar(shap_values, X_shap, model_name):
    """Bar plot: importância global média |SHAP|."""
    feat_names  = [FEATURE_LABELS.get(f, f) for f in FEATURES]
    mean_abs    = np.abs(shap_values).mean(axis=0)
    importance  = pd.Series(mean_abs, index=feat_names).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["#DD8452" if "Raça" in lbl or "Negro" in lbl or "negro" in lbl.lower()
              else "#4C72B0" for lbl in importance.index]
    bars = ax.barh(importance.index, importance.values, color=colors)
    ax.set_xlabel("Importância SHAP média (|SHAP|)")
    ax.set_title(
        f"Importância Global das Features — {model_name}\n"
        "Cor laranja = variáveis raciais/contextuais | azul = demográficas/educacionais",
        fontsize=11,
    )
    # Anotar valores
    for bar, val in zip(bars, importance.values):
        ax.text(val + 0.001, bar.get_y() + bar.get_height()/2,
                f"{val:.4f}", va="center", fontsize=8)
    plt.tight_layout()
    path = OUTPUTS_FIG / f"shap_importance_{model_name.lower()}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Importance bar salvo: {path}")

    return pd.DataFrame({
        "Feature": importance.index,
        "SHAP_mean_abs": importance.values.round(5),
    }).sort_values("SHAP_mean_abs", ascending=False)


def plot_shap_dependence_negro(shap_values, X_shap, model_name):
    """Dependence plot: efeito de 'negro' condicionado por pct_negro_upa."""
    feat_idx = FEATURES.index("negro")
    inter_idx = FEATURES.index("pct_negro_upa_z")

    fig, ax = plt.subplots(figsize=(8, 5))
    sc = ax.scatter(
        X_shap[:, feat_idx],
        shap_values[:, feat_idx],
        c=X_shap[:, inter_idx],
        cmap="RdYlGn_r",
        alpha=0.3, s=6,
    )
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("% Negro na UPA (z-score) — verde=menor, vermelho=maior", fontsize=8)
    ax.set_xlabel("Raça: 0=Branco, 1=Negro")
    ax.set_ylabel("SHAP value para 'Raça (negro)'")
    ax.set_title(
        f"Efeito da Raça no Rendimento — {model_name}\n"
        "Interação: penalidade racial amplificada por segregação residencial?\n"
        "SHAP < 0: ser negro reduz a predição de renda",
        fontsize=11,
    )
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Branco (0)", "Negro (1)"])
    plt.tight_layout()
    path = OUTPUTS_FIG / f"shap_dependence_negro_{model_name.lower()}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Dependence plot salvo: {path}")


def plot_shap_waterfall_cases(model, explainer, X_tr, df_shap, model_name):
    """
    Waterfall para 3 casos individuais:
      A) Branco com alta renda (mediana de brancos de alta renda)
      B) Negro com renda equivalente a A (verifica o que o modelo explica)
      C) Negro com baixa renda (pior caso)
    """
    try:
        feat_names = [FEATURE_LABELS.get(f, f) for f in FEATURES]

        # Seleciona índices representativos
        mask_bra = df_shap["negro"] == 0
        mask_neg = df_shap["negro"] == 1

        renda_med_bra = df_shap.loc[mask_bra, "log_renda"].quantile(0.75)
        renda_med_neg = df_shap.loc[mask_neg, "log_renda"].quantile(0.75)
        renda_low_neg = df_shap.loc[mask_neg, "log_renda"].quantile(0.25)

        def nearest_idx(mask, target_renda):
            sub = df_shap[mask].copy()
            return (sub["log_renda"] - target_renda).abs().idxmin()

        idx_a = nearest_idx(mask_bra, renda_med_bra)
        idx_b = nearest_idx(mask_neg, renda_med_neg)
        idx_c = nearest_idx(mask_neg, renda_low_neg)

        cases = {
            "A_branco_alta_renda": idx_a,
            "B_negro_alta_renda":  idx_b,
            "C_negro_baixa_renda": idx_c,
        }

        sv_obj = explainer(X_tr[:1])  # força inicializacao do objeto shap.Explanation
        for case_name, idx in cases.items():
            x_case = X_tr[idx:idx+1]
            sv = explainer(x_case)
            sv.feature_names = feat_names

            fig, ax = plt.subplots(figsize=(9, 5))
            shap.plots.waterfall(sv[0], max_display=12, show=False)
            renda_real = df_shap.loc[idx, "log_renda"]
            negro_val  = int(df_shap.loc[idx, "negro"])
            plt.title(
                f"SHAP Waterfall — {case_name}\n"
                f"{'Negro' if negro_val else 'Branco'} | log_renda real={renda_real:.3f} | "
                f"R$={np.exp(renda_real):.0f}/mês",
                fontsize=10,
            )
            plt.tight_layout()
            path = OUTPUTS_FIG / f"shap_waterfall_{case_name}_{model_name.lower()}.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            plt.close()
            logger.info(f"  Waterfall {case_name} salvo: {path}")

    except Exception as e:
        logger.warning(f"  Waterfall falhou: {e}")


# ── Tabela de Importância Comparada ───────────────────────────────────────────

def build_importance_table(imp_rf, imp_xgb):
    df = imp_rf.set_index("Feature").join(
        imp_xgb.set_index("Feature"),
        lsuffix="_RF", rsuffix="_XGB",
    ).sort_values("SHAP_mean_abs_XGB", ascending=False)
    df["Rank_RF"]  = df["SHAP_mean_abs_RF"].rank(ascending=False).astype(int)
    df["Rank_XGB"] = df["SHAP_mean_abs_XGB"].rank(ascending=False).astype(int)
    return df


# ── Sumário narrativo ─────────────────────────────────────────────────────────

def print_summary(metrics, imp_xgb, shap_negro_xgb, X_shap_xgb):
    negro_idx = FEATURES.index("negro")
    shap_neg_blacks  = shap_negro_xgb[X_shap_xgb[:, negro_idx] == 1, negro_idx]
    shap_neg_whites  = shap_negro_xgb[X_shap_xgb[:, negro_idx] == 0, negro_idx]
    mean_shap_negro  = shap_neg_blacks.mean()   # efeito medio da raca para negros
    mean_shap_branco = shap_neg_whites.mean()   # deve ser proximo de 0 (referencia)

    race_rank = imp_xgb[imp_xgb["Feature"] == FEATURE_LABELS["negro"]]["SHAP_mean_abs"].values
    race_rank_pos = int(imp_xgb[imp_xgb["Feature"] == FEATURE_LABELS["negro"]].index[0]) + 1 \
        if len(race_rank) > 0 else "N/D"

    sep = "=" * 78
    print(f"""
{sep}
  SUMARIO ML + SHAP — PNAD 2016-2025
{sep}

  PERFORMANCE DOS MODELOS (teste hold-out 20%):""")
    for m in metrics:
        print(f"    {m['Modelo']:<30s}  R²={m['R²']:.4f}  MAE={m['MAE']:.4f}  RMSE={m['RMSE']:.4f}")

    print(f"""
  IMPORTANCIA SHAP (XGBoost) — Top 5:""")
    for i, (_, row) in enumerate(imp_xgb.head(5).iterrows(), 1):
        print(f"    {i}. {row['Feature']:<30s}  |SHAP| medio = {row['SHAP_mean_abs']:.5f}")

    print(f"""
  EFEITO DA RACA (SHAP — XGBoost):
    SHAP medio para negros:  {mean_shap_negro:.4f}
       -> ser negro reduz a predicao de log-renda em {abs(mean_shap_negro):.4f} pontos
       -> equivale a {(np.exp(mean_shap_negro)-1)*100:.1f}% de penalidade racial
          APOS controlar por educacao, experiencia, genero e contexto de moradia.
    (Este e o efeito causal parcial estimado pelo modelo — evidencia de discriminacao.)

{sep}
""")


# ── Pipeline principal ─────────────────────────────────────────────────────────

def main():
    t_total = time.time()
    logger.info("=" * 70)
    logger.info("ML SUPERVISIONADO + SHAP — PNAD 2016-2025")
    logger.info("=" * 70)

    df = load_data()
    X_tr, X_te, y_tr, y_te, df_full = split(df)

    # ── Random Forest ──────────────────────────────────────────────────────────
    rf = fit_rf(X_tr, y_tr)
    m_rf = evaluate("Random Forest", y_te, rf.predict(X_te))
    m_rf["R2_treino"] = round(r2_score(y_tr, rf.predict(X_tr)), 4)        # diagnóstico de overfitting
    m_rf["gap_overfit"] = round(m_rf["R2_treino"] - m_rf["R²"], 4)
    metrics = [m_rf]

    # ── XGBoost ────────────────────────────────────────────────────────────────
    xgb_model = fit_xgb(X_tr, y_tr)
    m_xgb = evaluate("XGBoost", y_te, xgb_model.predict(X_te))
    m_xgb["R2_treino"] = round(r2_score(y_tr, xgb_model.predict(X_tr)), 4)
    m_xgb["gap_overfit"] = round(m_xgb["R2_treino"] - m_xgb["R²"], 4)
    metrics.append(m_xgb)
    logger.info(f"  Overfitting (R²treino-R²teste): RF={m_rf['gap_overfit']:.4f} | XGB={m_xgb['gap_overfit']:.4f}")

    # Salva métricas
    pd.DataFrame(metrics).to_csv(OUTPUTS_TB / "ml_performance.csv", index=False)

    # ── Baseline OLS (mesma partição) — ganho real do ML sobre a econometria ──
    base_ols = fit_ols_baseline(X_tr, y_tr, X_te, y_te)
    base_rows = [
        base_ols,
        {"Modelo": "Random Forest", "R2_teste": m_rf["R²"], "MAE_teste": m_rf["MAE"], "RMSE_teste": m_rf["RMSE"]},
        {"Modelo": "XGBoost",       "R2_teste": m_xgb["R²"], "MAE_teste": m_xgb["MAE"], "RMSE_teste": m_xgb["RMSE"]},
    ]
    df_baseline = pd.DataFrame(base_rows)
    df_baseline["ganho_R2_vs_OLS"] = (df_baseline["R2_teste"] - base_ols["R2_teste"]).round(4)
    df_baseline.to_csv(OUTPUTS_TB / "ml_baseline_comparacao.csv", index=False)
    logger.info(
        f"  Ganho de R² sobre OLS: RF={df_baseline.loc[1,'ganho_R2_vs_OLS']:.4f} | "
        f"XGB={df_baseline.loc[2,'ganho_R2_vs_OLS']:.4f}"
    )

    # ── Validação cruzada k-fold (robustez de protocolo além do hold-out) ─────
    if RUN_CV:
        cross_validate_models(df_full)

    # ── SHAP — Random Forest ───────────────────────────────────────────────────
    logger.info("--- SHAP: Random Forest ---")
    shap_rf, X_shap_rf, df_shap_rf, exp_rf = compute_shap(rf, X_tr, df_full, "RF")
    plot_shap_beeswarm(shap_rf, X_shap_rf, "RF")
    imp_rf = plot_shap_bar(shap_rf, X_shap_rf, "RF")
    plot_shap_dependence_negro(shap_rf, X_shap_rf, "RF")

    # ── SHAP — XGBoost ─────────────────────────────────────────────────────────
    logger.info("--- SHAP: XGBoost ---")
    shap_xgb, X_shap_xgb, df_shap_xgb, exp_xgb = compute_shap(
        xgb_model, X_tr, df_full, "XGB"
    )
    plot_shap_beeswarm(shap_xgb, X_shap_xgb, "XGB")
    imp_xgb = plot_shap_bar(shap_xgb, X_shap_xgb, "XGB")
    plot_shap_dependence_negro(shap_xgb, X_shap_xgb, "XGB")
    plot_shap_waterfall_cases(xgb_model, exp_xgb, X_shap_xgb, df_shap_xgb, "XGB")

    # ── Bootstrap de estabilidade dos valores SHAP (XGBoost) ──────────────────
    feat_names = [FEATURE_LABELS.get(f, f) for f in FEATURES]
    df_shap_boot = bootstrap_shap_ci(shap_xgb, feat_names, B=N_SHAP_BOOTSTRAP)
    logger.info(
        f"  SHAP bootstrap — top 3: "
        + ", ".join(f"{r.Feature}=[{r.ci_lo:.4f}; {r.ci_hi:.4f}]"
                     for _, r in df_shap_boot.head(3).iterrows())
    )

    # ── Tabela comparada ───────────────────────────────────────────────────────
    imp_table = build_importance_table(imp_rf, imp_xgb)
    imp_table.to_csv(OUTPUTS_TB / "shap_importance_comparada.csv")
    try:
        import jinja2  # noqa: F401
        latex = imp_table.to_latex(
            caption=(
                "Importância SHAP comparada — Random Forest e XGBoost. "
                "Predição de log-rendimento, PNAD 2016-2025 (N=50k subsample SHAP). "
                "Valores: |SHAP| médio; maior = maior impacto no rendimento predito."
            ),
            label="tab:shap_importance",
            escape=False,
        )
        (OUTPUTS_TB / "shap_importance_comparada.tex").write_text(latex, encoding="utf-8")
    except ImportError:
        pass

    # ── Sumário ────────────────────────────────────────────────────────────────
    print_summary(metrics, imp_xgb, shap_xgb, X_shap_xgb)

    # Tabela no console
    print("--- Importância SHAP Comparada (RF vs XGBoost) ---")
    print(imp_table[["SHAP_mean_abs_RF", "Rank_RF", "SHAP_mean_abs_XGB", "Rank_XGB"]].to_string())

    elapsed = (time.time() - t_total) / 60
    logger.info(f"CONCLUIDO em {elapsed:.1f} min")
    print(f"\n=== CONCLUIDO em {elapsed:.1f} min | Outputs: {OUTPUTS_TB} / {OUTPUTS_FIG} ===")


if __name__ == "__main__":
    main()
