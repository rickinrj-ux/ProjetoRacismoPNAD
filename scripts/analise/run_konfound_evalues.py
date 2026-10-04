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

# --- bootstrap raiz do projeto (reorg estrutura) ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys; sys.stdout.reconfigure(encoding="utf-8")
import logging
from pathlib import Path

sys.path.insert(0, "src")
Path("outputs/_logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("outputs/_logs/konfound_evalues.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from konfound_evalues import run_konfound_evalues

if __name__ == "__main__":
    # LEGADO (02/10/2026): src/konfound_evalues.py tem os β do HLM de uma especificação
    # antiga digitados no código e lê o logit-FE, não o GLMM. No TCC, o Konfound vem de
    # hlm_stepup_konfound.csv (run_hlm_stepup.py) e o E-value de gerar_tabela_glmm.py —
    # rodar isto só regravaria evalues_glmm.csv com números velhos. Mantido sob --legado.
    if "--legado" not in sys.argv:
        print("run_konfound_evalues: legado, nada a fazer (ver comentário; use --legado).")
        sys.exit(0)
    run_konfound_evalues()
    print("\n=== CONCLUÍDO ===")
