# -*- coding: utf-8 -*-
"""
regerar_waterfalls_shap.py
==========================
Regera apenas as figuras de *waterfall* do XGBoost, sem repetir o pipeline
inteiro de `run_ml_shap.py`.

Por que existe: os valores SHAP não são gravados em disco, então mudar o
desenho da figura exige recalculá-los. O caro é o Random Forest (~43 min de
ajuste e ~54 min de SHAP), que não entra em nenhuma das três figuras. Aqui só
o XGBoost é reajustado, com as mesmas funções, os mesmos hiperparâmetros e a
mesma semente de `run_ml_shap.py` --- este arquivo não redefine nada, importa.

Reprodutibilidade: como a semente e a ordem das operações são as do pipeline,
o subsample e os casos A, B e C são os mesmos da última execução completa;
muda só o que a figura mostra.

Uso: python scripts/analise/regerar_waterfalls_shap.py
"""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "run_ml_shap", ROOT / "scripts" / "analise" / "run_ml_shap.py"
)
ml = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ml)          # o módulo não roda main() ao ser importado


def main() -> int:
    t0 = time.time()
    ml.logger.info("=" * 70)
    ml.logger.info("REGERANDO SÓ OS WATERFALLS (XGBoost)")
    ml.logger.info("=" * 70)

    df = ml.load_data()
    X_tr, X_te, y_tr, y_te, df_full, pos_tr = ml.split(df)

    xgb_model = ml.fit_xgb(X_tr, y_tr)
    shap_xgb, X_shap, df_shap, exp_xgb = ml.compute_shap(
        xgb_model, X_tr, df_full, "XGB", pos_tr
    )
    ml.plot_shap_waterfall_cases(xgb_model, exp_xgb, X_shap, df_shap, "XGB")

    ml.logger.info(f"CONCLUIDO em {(time.time() - t0) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
