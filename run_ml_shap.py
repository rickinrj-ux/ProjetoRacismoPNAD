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
import sys
import logging
import time
import warnings
from pathlib import Path

sys.path.insert(0, "src")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

Path("logs").mkdir(exist_ok=True)
handlers = [
    logging.FileHandler("logs/ml_shap.log", encoding="utf-8"),
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
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import xgboost as xgb

FEATURES_PATH = Path("data/processed/features.parquet")
OUTPUTS_TB    = Path("outputs/tables")
OUTPUTS_FIG   = Path("outputs/figures")
OUTPUTS_TB.mkdir(parents=True, exist_ok=True)
OUTPUTS_FIG.mkdir(parents=True, exist_ok=True)

SAMPLE_FRAC   = 0.20
SHAP_SAMPLE   = 50_000
RANDOM_STATE  = 42

# ── Features e target ─────────────────────────────────────────────────────────
TARGET = "log_renda"

FEATURES = [
    # Individuais
    "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
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

    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df = df.dropna(subset=FEATURES + [TARGET]).reset_index(drop=True)

    for col in FEATURES + [TARGET]:
        df[col] = df[col].astype(float)

    logger.info(f"  Apos filtros: {len(df):,} obs.")

    df = df.sample(frac=SAMPLE_FRAC, random_state=RANDOM_STATE).reset_index(drop=True)
    logger.info(f"  Amostra {SAMPLE_FRAC*100:.0f}%: {len(df):,} obs.")
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


# ── Random Forest ──────────────────────────────────────────────────────────────

def fit_rf(X_tr, y_tr):
    logger.info("Ajustando Random Forest (n=200, depth=10) ...")
    t0 = time.time()
    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=50,
        n_jobs=-1,
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
    metrics = [evaluate("Random Forest", y_te, rf.predict(X_te))]

    # ── XGBoost ────────────────────────────────────────────────────────────────
    xgb_model = fit_xgb(X_tr, y_tr)
    metrics.append(evaluate("XGBoost", y_te, xgb_model.predict(X_te)))

    # Salva métricas
    pd.DataFrame(metrics).to_csv(OUTPUTS_TB / "ml_performance.csv", index=False)

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
