"""
run_sobrevivencia.py
====================
Análise de sobrevivência do vínculo empregatício por raça (Cox PH + KM).
Outputs: outputs/figures/sobrevivencia_*.png | outputs/tables/sobrevivencia_*.csv

Requer (opcional para duração real):
    pip install lifelines

Se lifelines não estiver instalado: usa regressão logística como proxy.
Se V4039/V4040 não estiverem em features.parquet: usa duração sintética.

Uso:
    python run_sobrevivencia.py --sample 0.20
    python run_sobrevivencia.py
"""

# --- bootstrap raiz do projeto (reorg estrutura) ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys
import logging
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/sobrevivencia.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from sobrevivencia import run_sobrevivencia

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Análise de sobrevivência — emprego por raça")
    parser.add_argument("--sample", type=float, default=None)
    args = parser.parse_args()

    resultado = run_sobrevivencia(sample_frac=args.sample)

    print("\n=== CONCLUÍDO ===")
    print(f"Dataset: {len(resultado['df']):,} trabalhadores")
    print("Outputs salvos em: outputs/figures/ e outputs/tables/")
