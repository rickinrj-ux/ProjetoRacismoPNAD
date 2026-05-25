"""
run_oster_bounds.py
===================
Sensibilidade de Oster (2019): robustez do gap salarial racial a variáveis omitidas.
Outputs: outputs/figures/oster_bounds.png | outputs/tables/oster_bounds.{csv,tex}

Uso:
    python run_oster_bounds.py             # população completa
    python run_oster_bounds.py --sample 0.1
"""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import argparse
import logging
from pathlib import Path

sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/oster_bounds.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from oster_bounds import run_oster_bounds

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=float, default=None)
    args = parser.parse_args()
    run_oster_bounds(sample_frac=args.sample)
    print("\n=== CONCLUÍDO: outputs/tables/oster_bounds.* ===")
