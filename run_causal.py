"""
run_causal.py
=============
Inferência causal do efeito da raça sobre renda (PSM + Double ML).
Outputs: outputs/figures/causal_*.png | outputs/tables/causal_*.csv

Requer:
    scikit-learn (já instalado)
    econml (opcional — pip install econml)
    Se econml não estiver disponível: usa implementação manual do Double ML.

Uso:
    python run_causal.py --sample 0.10
    python run_causal.py
"""
import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/inferencia_causal.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from inferencia_causal import run_inferencia_causal

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inferência causal — PSM + Double ML")
    parser.add_argument("--sample", type=float, default=0.20,
                        help="Fração da amostra. Default: 20%% (DML é computacionalmente intenso).")
    args = parser.parse_args()

    resultado = run_inferencia_causal(sample_frac=args.sample)

    print("\n=== CONCLUÍDO ===")
    print(f"Pares matched (PSM): {resultado['psm']['n_pares']:,}")
    print(f"ATT (PSM):      {resultado['psm']['ATT']:+.4f}  →  gap {resultado['psm']['gap_pct']:.1f}%")
    print(f"ATT (Double ML): {resultado['dml']['ATT']:+.4f}  →  gap {resultado['dml']['gap_pct']:.1f}%")
    print("Outputs salvos em: outputs/figures/ e outputs/tables/")
