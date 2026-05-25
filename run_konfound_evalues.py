"""
run_konfound_evalues.py
=======================
Sensibilidade a variáveis omitidas — métodos corretos por tipo de modelo:
  - Konfound (Frank et al., 2013)  para HLM M1–M4
  - E-values (VanderWeele & Ding, 2017) para GLMM
  - Oster bounds (Oster, 2019) reposicionado como check auxiliar de OLS

Não re-estima modelos: usa β e SE dos outputs existentes em outputs/tables/.

Outputs:
    outputs/tables/konfound_hlm_vs_ols.{csv,tex}
    outputs/tables/evalues_glmm.{csv,tex}
    outputs/tables/sensibilidade_comparativa.csv
    outputs/figures/sensibilidade_konfound_evalues.png
"""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import logging
from pathlib import Path

sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/konfound_evalues.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from konfound_evalues import run_konfound_evalues

if __name__ == "__main__":
    run_konfound_evalues()
    print("\n=== CONCLUÍDO ===")
