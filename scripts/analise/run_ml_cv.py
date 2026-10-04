"""
run_ml_cv.py
============
Validação cruzada e escolha de hiperparâmetros do XGBoost (TODO_revisao, bloco 8;
apostila Alencar, ML-02/ML-06), na POPULAÇÃO COMPLETA — sem amostragem.

Desenho (sem tocar no conjunto de teste, para não contaminar as métricas do relatório):
  1. Mesmo split 80/20 de run_ml_shap.py (train_test_split, seed 42).
  2. Busca de hiperparâmetros numa partição de validação DENTRO do treino (75/25):
     grade pequena e deliberada em max_depth / learning_rate / n_estimators, começando
     pela configuração atual do TCC. Não é grid completo: é a comparação que responde
     "a configuração usada é defensável?".
  3. Validação cruzada k-fold (k=5) do modelo escolhido, no treino inteiro, reportando
     média +- desvio-padrão de R2, MAE e RMSE entre folds (a variabilidade entre folds é
     o que a apostila pede reportar).
  4. Métricas na unidade original (ML-04): o modelo prevê log-renda; converte-se o erro
     para reais com a correção de Duan (smearing), reportando MAE e erro mediano em R$.

Saídas: outputs/tables/ml_cv_hiperparametros.csv, ml_cv_folds.csv, ml_cv_resumo.csv
Uso: python scripts/analise/run_ml_cv.py
"""

# --- bootstrap raiz do projeto ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys, time, logging, warnings
from pathlib import Path
sys.path.insert(0, "src")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
Path("outputs/_logs").mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%H:%M:%S",
                    handlers=[logging.FileHandler("outputs/_logs/ml_cv.log", encoding="utf-8"),
                              logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

TABLES = Path("outputs/tables")
SEED = 42
K = 5

# grade deliberada: a 1ª linha é a configuração atual do TCC
GRADE = [
    dict(max_depth=6, learning_rate=0.05, n_estimators=300),   # atual
    dict(max_depth=6, learning_rate=0.10, n_estimators=300),
    dict(max_depth=8, learning_rate=0.05, n_estimators=300),
    dict(max_depth=8, learning_rate=0.05, n_estimators=600),
    dict(max_depth=10, learning_rate=0.05, n_estimators=300),
    dict(max_depth=4, learning_rate=0.05, n_estimators=300),
]
FIXOS = dict(subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0,
             n_jobs=-1, random_state=SEED, verbosity=0)


def carregar():
    """Mesmas features/filtros de run_ml_shap.py (inclui a renda do bairro leave-one-out)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("mlshap", "scripts/analise/run_ml_shap.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["mlshap"] = m
    spec.loader.exec_module(m)          # só o topo: constantes e load_data (main() fica no guard)
    df = m.load_data()
    X = df[m.FEATURES].values
    y = df[m.TARGET].values
    return X, y, m.FEATURES


def metricas(y, p, prefixo=""):
    return {f"{prefixo}r2": r2_score(y, p), f"{prefixo}mae": mean_absolute_error(y, p),
            f"{prefixo}rmse": float(np.sqrt(mean_squared_error(y, p)))}


def main():
    t0 = time.time()
    X, y, feats = carregar()
    logger.info(f"N = {len(y):,} | {len(feats)} features")
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.20, random_state=SEED)
    # partição de validação DENTRO do treino (o teste permanece intocado)
    X_fit, X_val, y_fit, y_val = train_test_split(X_tr, y_tr, test_size=0.25, random_state=SEED)
    logger.info(f"treino={len(y_tr):,} (ajuste={len(y_fit):,} / validação={len(y_val):,}) | teste={len(y_te):,}")

    # ── 1. Busca de hiperparâmetros na validação ─────────────────────────────
    linhas = []
    for i, g in enumerate(GRADE, 1):
        t = time.time()
        mdl = xgb.XGBRegressor(**g, **FIXOS).fit(X_fit, y_fit)
        m_val = metricas(y_val, mdl.predict(X_val))
        m_fit = metricas(y_fit, mdl.predict(X_fit), "treino_")
        linhas.append({"config": i, **g, **m_val, **m_fit,
                       "gap_overfit": m_fit["treino_r2"] - m_val["r2"],
                       "minutos": round((time.time() - t) / 60, 2)})
        logger.info(f"  [{i}/{len(GRADE)}] depth={g['max_depth']} lr={g['learning_rate']} "
                    f"n={g['n_estimators']}: R²val={m_val['r2']:.4f} MAE={m_val['mae']:.4f} "
                    f"gap={linhas[-1]['gap_overfit']:.4f} ({linhas[-1]['minutos']:.1f} min)")
        del mdl
    hp = pd.DataFrame(linhas).sort_values("r2", ascending=False)
    hp.to_csv(TABLES / "ml_cv_hiperparametros.csv", index=False, encoding="utf-8")
    best = hp.iloc[0]
    escolhido = {k: (int(best[k]) if k != "learning_rate" else float(best[k]))
                 for k in ("max_depth", "learning_rate", "n_estimators")}
    atual = GRADE[0]
    logger.info(f"melhor na validação: {escolhido} (R²={best['r2']:.4f}); "
                f"atual do TCC: {atual} (R²={hp[hp['config'] == 1]['r2'].iloc[0]:.4f})")

    # ── 2. k-fold no treino, com a configuração escolhida e a atual ──────────
    folds = []
    for nome, cfg in (("escolhida", escolhido), ("atual_tcc", atual)):
        if nome == "atual_tcc" and cfg == escolhido:
            continue
        kf = KFold(n_splits=K, shuffle=True, random_state=SEED)
        for f, (i_tr, i_va) in enumerate(kf.split(X_tr), 1):
            t = time.time()
            mdl = xgb.XGBRegressor(**cfg, **FIXOS).fit(X_tr[i_tr], y_tr[i_tr])
            m = metricas(y_tr[i_va], mdl.predict(X_tr[i_va]))
            folds.append({"config": nome, **cfg, "fold": f, **m,
                          "minutos": round((time.time() - t) / 60, 2)})
            logger.info(f"  [{nome}] fold {f}/{K}: R²={m['r2']:.4f} MAE={m['mae']:.4f} "
                        f"({folds[-1]['minutos']:.1f} min)")
            del mdl
    fd = pd.DataFrame(folds)
    fd.to_csv(TABLES / "ml_cv_folds.csv", index=False, encoding="utf-8")

    # ── 3. Modelo final no treino inteiro + teste (métricas do relatório) ────
    mdl = xgb.XGBRegressor(**escolhido, **FIXOS).fit(X_tr, y_tr)
    p_te = mdl.predict(X_te)
    m_te = metricas(y_te, p_te)
    # unidade original (ML-04): log -> R$ com correção de Duan (smearing)
    resid = y_tr - mdl.predict(X_tr)
    smear = float(np.mean(np.exp(resid)))
    reais_obs = np.exp(y_te)
    reais_pred = np.exp(p_te) * smear
    err = np.abs(reais_obs - reais_pred)
    resumo = {
        "k": K, "n_treino": len(y_tr), "n_teste": len(y_te),
        **{f"cv_{c}_media": fd[fd["config"] == "escolhida"][c].mean() for c in ("r2", "mae", "rmse")},
        **{f"cv_{c}_dp": fd[fd["config"] == "escolhida"][c].std(ddof=1) for c in ("r2", "mae", "rmse")},
        **{f"teste_{k.split('_')[-1]}": v for k, v in m_te.items()},
        "smearing_duan": smear,
        "mae_reais": float(np.mean(err)), "erro_mediano_reais": float(np.median(err)),
        "erro_mediano_pct": float(np.median(err / reais_obs) * 100),
        **{f"escolhido_{k}": v for k, v in escolhido.items()},
        "config_atual_igual": escolhido == atual,
    }
    pd.DataFrame([resumo]).to_csv(TABLES / "ml_cv_resumo.csv", index=False, encoding="utf-8")
    logger.info(f"CV (k={K}): R² {resumo['cv_r2_media']:.4f} ± {resumo['cv_r2_dp']:.4f} | "
                f"teste R² {m_te['r2']:.4f} | erro mediano R$ {resumo['erro_mediano_reais']:.0f} "
                f"({resumo['erro_mediano_pct']:.0f}% do salário)")
    logger.info(f"CONCLUÍDO em {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
