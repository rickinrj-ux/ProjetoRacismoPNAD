"""
run_ml_cv_fullpop.py
=====================
Reexecuta apenas a validação cruzada k-fold (RF/XGBoost) de run_ml_shap.py em
POPULAÇÃO COMPLETA (7,69M obs.), substituindo a versão em subamostra de 20%
(CV_SAMPLE_FRAC) documentada como limitação computacional.

Reaproveita load_data()/split()/cross_validate_models() de run_ml_shap.py sem
refazer o fit principal, SHAP ou bootstrap (já corretos e mais caros de
recomputar sem necessidade) — sobrescreve outputs/tables/ml_performance_cv.csv.
"""

import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
_sys.path.insert(0, "scripts/analise")

import time
import run_ml_shap as mlshap

def main():
    t0 = time.time()
    mlshap.logger.info("=" * 70)
    mlshap.logger.info("CV K-FOLD EM POPULAÇÃO COMPLETA (reexecução de run_ml_shap.py)")
    mlshap.logger.info("=" * 70)

    df = mlshap.load_data()
    _, _, _, _, df_full = mlshap.split(df)

    mlshap.cross_validate_models(df_full, k=mlshap.N_CV_FOLDS, sample_frac=1.0)

    elapsed = (time.time() - t0) / 60
    mlshap.logger.info(f"CV FULL-POP CONCLUÍDO em {elapsed:.1f} min")
    print(f"\n=== CV FULL-POP CONCLUÍDO em {elapsed:.1f} min ===")


if __name__ == "__main__":
    main()
