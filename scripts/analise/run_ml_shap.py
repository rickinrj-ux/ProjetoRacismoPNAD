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
        300 árvores, max_depth=10 (validação cruzada), learning_rate=0.05.
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
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import xgboost as xgb

FEATURES_PATH = Path("data/processed/features.parquet")
OUTPUTS_TB    = Path("outputs/tables")
OUTPUTS_FIG   = Path("outputs/figures")
OUTPUTS_TB.mkdir(parents=True, exist_ok=True)
OUTPUTS_FIG.mkdir(parents=True, exist_ok=True)

SAMPLE_FRAC   = None   # None = população completa (modelo treina em 7,69M; SHAP em subset p/ viz)
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
    "media_educ_upa_z", "media_renda_upa_loo_z",
    # Contexto UF (Nível 3)
    "pct_negro_uf_z", "tx_desemprego_uf_z", "media_educ_uf_z",
]

FEATURE_LABELS = {
    "negro":                   "Raça (negro)",
    "sexo_fem":                "Gênero (feminino)",
    "idade_c":                 "Idade (centrada)",
    "idade_sq":                "Idade² (experiência)",
    "educ_fund_completo":      "Educ.: fundamental completo",
    "educ_medio_completo":     "Educ.: médio completo",
    "educ_superior_completo":  "Educ.: superior completo",
    "educ_pos_graduacao":      "Educ.: pós-graduação",
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
    "media_renda_upa_loo_z":   "Renda média UPA (exceto o próprio)",
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

    # Renda média da UPA LEAVE-ONE-OUT (problema do reflexo, Manski 1993): a variável
    # original media_renda_upa_z é a média de log_renda da UPA INCLUINDO o próprio
    # indivíduo — regredir y_i em ȳ_j é mecanicamente informativo e não mede efeito de
    # vizinhança. Aqui: (soma_j − y_i)/(n_j − 1), padronizada. UPAs com n = 1 saem.
    _sum = df.groupby("UPA")["log_renda"].transform("sum")
    _n   = df.groupby("UPA")["log_renda"].transform("size")
    _loo = (_sum - df["log_renda"]) / (_n - 1)
    df["media_renda_upa_loo_z"] = (_loo - _loo.mean()) / _loo.std()
    df = df[_n > 1].copy()
    logger.info(f"  renda média da UPA leave-one-out criada (UPAs com n=1 removidas: {int((_n <= 1).sum()):,})")

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
    # o índice viaja junto no split: sem ele não há como voltar de uma linha da
    # matriz de treino para a linha correspondente do dataframe (o embaralhamento
    # do train_test_split desfaz qualquer correspondência posicional)
    pos = np.arange(len(df))
    X_tr, X_te, y_tr, y_te, pos_tr, pos_te = train_test_split(
        X, y, pos, test_size=0.20, random_state=RANDOM_STATE
    )
    logger.info(f"  Treino: {len(X_tr):,} | Teste: {len(X_te):,}")
    return X_tr, X_te, y_tr, y_te, df, pos_tr


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
    logger.info("Ajustando XGBoost (n=300, depth=10 [CV], lr=0.05) ...")
    t0 = time.time()
    # max_depth=10 escolhido por validação cruzada 5-fold na população (run_ml_cv.py):
    # R² 0,628 ± 0,001 contra 0,614 ± 0,001 de max_depth=6, sem sinal de sobreajuste
    # (gap treino–validação de 0,011). Demais hiperparâmetros inalterados.
    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=10,
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

def compute_shap(model, X_tr, df, model_name, pos_tr):
    logger.info(f"[{model_name}] Calculando SHAP (subsample={SHAP_SAMPLE:,}) ...")
    t0 = time.time()

    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(len(X_tr), size=min(SHAP_SAMPLE, len(X_tr)), replace=False)
    X_shap = X_tr[idx]
    # pos_tr[idx] é a linha do dataframe que gerou X_shap[i]; usar df.iloc[idx]
    # direto emparelharia cada valor SHAP com a pessoa errada
    df_shap = df.iloc[pos_tr[idx]].reset_index(drop=True)

    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_shap)

    logger.info(f"  [{model_name}] SHAP calculado em {time.time()-t0:.0f}s")
    return shap_values, X_shap, df_shap, explainer


# ── Plots SHAP ────────────────────────────────────────────────────────────────

from src.figuras_ptbr import virgula_decimal as _virgula_decimal  # noqa: E402


def plot_shap_beeswarm(shap_values, X_shap, model_name):
    """Beeswarm (summary): distribuição de SHAP por feature."""
    feat_names = [FEATURE_LABELS.get(f, f) for f in FEATURES]
    plt.figure(figsize=(9, 7))
    shap.summary_plot(
        shap_values, X_shap,
        feature_names=feat_names,
        show=False, plot_size=None,
        color_bar_label="Valor da variável (alto → vermelho)",
    )
    plt.title(
        f"Contribuição de cada variável ao log-rendimento previsto — {model_name}\n"
        f"PNAD Contínua 2016–2025 | valores SHAP em {SHAP_SAMPLE // 1000} mil casos do treino",
        fontsize=11, pad=10,
    )
    plt.gcf().axes[0].set_xlabel("Valor SHAP (efeito sobre o log-rendimento previsto)")
    _virgula_decimal()
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
    colors = ["#DD8452" if lbl == FEATURE_LABELS["negro"]
              else "#4C72B0" for lbl in importance.index]
    bars = ax.barh(importance.index, importance.values, color=colors)
    ax.set_xlabel("Importância SHAP média (|SHAP|)")
    ax.set_title(
        f"Importância global das variáveis — {model_name}\n"
        "Laranja = raça | azul = demais variáveis",
        fontsize=11,
    )
    # Anotar valores
    for bar, val in zip(bars, importance.values):
        ax.text(val + 0.001, bar.get_y() + bar.get_height()/2,
                f"{val:.4f}".replace(".", ","), va="center", fontsize=8)
    _virgula_decimal(fig)
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
    cbar.set_label("% de negros na UPA (escore z) — verde = menor, vermelho = maior", fontsize=8)
    ax.set_xlabel("Raça")
    ax.set_ylabel("Valor SHAP da raça")
    ax.set_title(
        f"Efeito da raça na previsão de rendimento — {model_name}\n"
        "A penalidade varia com a composição racial do bairro?\n"
        "SHAP < 0: ser negro reduz a previsão de renda",
        fontsize=11,
    )
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Branco", "Negro"])
    _virgula_decimal(fig)
    plt.tight_layout()
    path = OUTPUTS_FIG / f"shap_dependence_negro_{model_name.lower()}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Dependence plot salvo: {path}")


def _explanation_preservando_raca(sv_caso, feat_names, n_top=11):
    """Reduz o caso às maiores contribuições, sem deixar a raça cair no agregado.

    `shap.plots.waterfall` ordena por |contribuição| e junta o excedente numa
    linha "N other features". Com 29 preditores, a raça --- pequena num caso
    individual diante da jornada e da ocupação --- nunca chegava a aparecer, e
    a legenda da figura afirmava o contrário. Aqui ela é mantida à força; o
    resto continua agregado, como o próprio shap faria.
    """
    j = FEATURES.index("negro")
    vals  = np.asarray(sv_caso.values, dtype=float)
    dados = np.asarray(sv_caso.data, dtype=float)
    ordem = np.argsort(-np.abs(vals))
    top   = [i for i in ordem if i != j][:n_top]
    mantidas = top + [j]
    resto    = [i for i in range(len(vals)) if i not in mantidas]
    return shap.Explanation(
        values=np.append(vals[mantidas], vals[resto].sum()),
        base_values=sv_caso.base_values,
        data=np.append(dados[mantidas], np.nan),
        feature_names=[feat_names[i] for i in mantidas]
                      + [f"outras {len(resto)} variáveis"],
    )


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

            expl = _explanation_preservando_raca(sv[0], feat_names)
            fig, ax = plt.subplots(figsize=(9, 5))
            shap.plots.waterfall(expl, max_display=len(expl.feature_names),
                                 show=False)
            # a linha agregada não tem valor de feature; o shap imprimiria "nan ="
            ax_atual = plt.gca()
            ax_atual.set_yticklabels(
                [t.get_text().replace("nan = ", "") for t in ax_atual.get_yticklabels()]
            )
            renda_real = df_shap.loc[idx, "log_renda"]
            negro_val  = int(df_shap.loc[idx, "negro"])
            rotulo = {"A_branco_alta_renda": "Trabalhador branco, percentil 75 da renda dos brancos",
                      "B_negro_alta_renda": "Trabalhador negro, percentil 75 da renda dos negros",
                      "C_negro_baixa_renda": "Trabalhador negro, percentil 25 da renda dos negros"}[case_name]
            reais = f"{np.exp(renda_real):,.0f}".replace(",", ".")
            plt.title(
                f"{rotulo}\n"
                + f"log-rendimento observado = {renda_real:.3f}".replace(".", ",")
                + f" (R$ {reais}/mês, reais do 2º tri/2026)",
                fontsize=10,
            )
            _virgula_decimal()
            plt.tight_layout()
            path = OUTPUTS_FIG / f"shap_waterfall_{case_name}_{model_name.lower()}.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            plt.close()
            logger.info(f"  Waterfall {case_name} salvo: {path}")

    except Exception as e:
        logger.warning(f"  Waterfall falhou: {e}")


# ── Tabela de Importância Comparada ───────────────────────────────────────────

def salvar_shap_negro_por_grupo(shap_rf, X_shap_rf, shap_xgb, X_shap_xgb):
    """Média SHAP da variável racial, com sinal, separada por grupo.

    A média em valor absoluto responde "quanto a raça pesou"; esta responde
    "para que lado". É a segunda que sustenta a leitura de penalidade, e a
    conversão para percentual segue a mesma regra semilog do resto do
    trabalho: (e^x - 1) x 100, e não x vezes 100.

    O grupo sai da própria matriz de features, não do dataframe: é o valor que
    o modelo viu ao produzir aquele SHAP, e dispensa qualquer realinhamento.
    """
    j = FEATURES.index("negro")
    linhas = []
    for nome, sv, Xs in (("Random Forest", shap_rf, X_shap_rf),
                         ("XGBoost", shap_xgb, X_shap_xgb)):
        neg = Xs[:, j].astype(bool)
        for grupo, mask in (("negros", neg), ("brancos", ~neg)):
            if not mask.any():
                continue
            m = float(np.asarray(sv)[mask, j].mean())
            linhas.append({
                "modelo": nome,
                "grupo": grupo,
                "n": int(mask.sum()),
                "shap_medio_negro": round(m, 6),
                "equivalente_pct": round((np.exp(m) - 1) * 100, 4),
            })
    out = pd.DataFrame(linhas)
    out.to_csv(OUTPUTS_TB / "shap_negro_por_grupo.csv", index=False)
    for r in linhas:
        logger.info(f"  [SHAP raça, {r['modelo']}] {r['grupo']}: "
                    f"media com sinal = {r['shap_medio_negro']:+.4f} "
                    f"({r['equivalente_pct']:+.2f}% no rendimento predito, n={r['n']:,})")
    return out


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
       -> equivale a {(np.exp(mean_shap_negro)-1)*100:.1f}% abaixo da previsao media da base
          APOS controlar por educacao, experiencia, genero e contexto de moradia.
    SHAP medio para brancos: {mean_shap_branco:+.4f}
       -> contraste entre os grupos: {mean_shap_negro-mean_shap_branco:+.4f} log-pontos
          ({(np.exp(mean_shap_negro-mean_shap_branco)-1)*100:+.1f}%), que e o analogo
          do coeficiente racial dos modelos parametricos.
    (Decomposicao da predicao do modelo, nao efeito causal: SHAP explica o que o
     modelo faz com os dados, e o desenho e observacional.)

{sep}
""")


# ── Pipeline principal ─────────────────────────────────────────────────────────

def main():
    t_total = time.time()
    logger.info("=" * 70)
    logger.info("ML SUPERVISIONADO + SHAP — PNAD 2016-2025")
    logger.info("=" * 70)

    df = load_data()
    X_tr, X_te, y_tr, y_te, df_full, pos_tr = split(df)

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

    # ── Robustez ao reflexo: XGBoost SEM nenhuma renda de vizinhança ───────────
    # (a LOO já remove a inclusão mecânica do próprio indivíduo; aqui testa-se o caso
    #  extremo — nem a renda dos vizinhos entra — para ver quanto do ajuste e do
    #  ranking de importância dependia dessa variável.)
    i_loo = FEATURES.index("media_renda_upa_loo_z")
    keep = [i for i in range(len(FEATURES)) if i != i_loo]
    xgb_sr = fit_xgb(X_tr[:, keep], y_tr)
    m_sr = evaluate("XGBoost (sem renda da UPA)", y_te, xgb_sr.predict(X_te[:, keep]))
    m_sr["R2_treino"] = round(r2_score(y_tr, xgb_sr.predict(X_tr[:, keep])), 4)
    m_sr["gap_overfit"] = round(m_sr["R2_treino"] - m_sr["R²"], 4)
    metrics.append(m_sr)
    # rank da raça nesse modelo (mesmo subsample do SHAP principal)
    try:
        rng_sr = np.random.default_rng(RANDOM_STATE)
        idx_sr = rng_sr.choice(len(X_tr), size=min(SHAP_SAMPLE, len(X_tr)), replace=False)
        sv_sr = shap.TreeExplainer(xgb_sr).shap_values(X_tr[idx_sr][:, keep])
        imp_sr = pd.DataFrame({"Feature": [FEATURE_LABELS.get(FEATURES[i], FEATURES[i]) for i in keep],
                               "SHAP_mean_abs": np.abs(sv_sr).mean(0)}).sort_values("SHAP_mean_abs", ascending=False)
        imp_sr = imp_sr.reset_index(drop=True)
        imp_sr["rank"] = imp_sr.index + 1
        imp_sr.to_csv(OUTPUTS_TB / "shap_importance_sem_renda_upa.csv", index=False)
        _r = imp_sr[imp_sr["Feature"] == FEATURE_LABELS["negro"]]
        logger.info(f"  [sem renda da UPA] R²={m_sr['R²']:.4f} | raça no rank "
                    f"{int(_r['rank'].iloc[0]) if len(_r) else '?'} de {len(imp_sr)}")
        del sv_sr
    except Exception as e:  # noqa: BLE001
        logger.warning(f"  SHAP do modelo sem renda da UPA falhou: {e}")
    del xgb_sr

    # Salva métricas
    pd.DataFrame(metrics).to_csv(OUTPUTS_TB / "ml_performance.csv", index=False)

    # ── SHAP — Random Forest ───────────────────────────────────────────────────
    logger.info("--- SHAP: Random Forest ---")
    shap_rf, X_shap_rf, df_shap_rf, exp_rf = compute_shap(rf, X_tr, df_full, "RF", pos_tr)
    plot_shap_beeswarm(shap_rf, X_shap_rf, "RF")
    imp_rf = plot_shap_bar(shap_rf, X_shap_rf, "RF")
    plot_shap_dependence_negro(shap_rf, X_shap_rf, "RF")

    # ── SHAP — XGBoost ─────────────────────────────────────────────────────────
    logger.info("--- SHAP: XGBoost ---")
    shap_xgb, X_shap_xgb, df_shap_xgb, exp_xgb = compute_shap(
        xgb_model, X_tr, df_full, "XGB", pos_tr
    )
    plot_shap_beeswarm(shap_xgb, X_shap_xgb, "XGB")
    imp_xgb = plot_shap_bar(shap_xgb, X_shap_xgb, "XGB")
    plot_shap_dependence_negro(shap_xgb, X_shap_xgb, "XGB")
    plot_shap_waterfall_cases(xgb_model, exp_xgb, X_shap_xgb, df_shap_xgb, "XGB")

    # ── Média SHAP da raça com sinal, por grupo ────────────────────────────────
    # (a tabela comparada guarda só |SHAP|; a direção do efeito sai daqui)
    salvar_shap_negro_por_grupo(shap_rf, X_shap_rf, shap_xgb, X_shap_xgb)

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
