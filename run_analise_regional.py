"""
run_analise_regional.py
=======================
Análise de heterogeneidade regional do gap salarial racial.
Outputs: outputs/figures/regional_*.png | outputs/tables/regional_*.csv/.tex

Uso rápido (10% da amostra para teste):
    python run_analise_regional.py --sample 0.10

Análise completa:
    python run_analise_regional.py
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
        logging.FileHandler("logs/analise_regional.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from analise_regional import run_analise_regional

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Análise regional do gap racial — PNAD Contínua")
    parser.add_argument("--sample", type=float, default=None,
                        help="Fração da amostra (ex: 0.10 para 10%%). Default: dados completos.")
    args = parser.parse_args()

    resultados = run_analise_regional(sample_frac=args.sample)

    print("\n=== CONCLUÍDO ===")
    print(f"HLM por região: {len(resultados['hlm'])} regiões estimadas")
    print(f"Regressão quantílica: {len(resultados['qr'])} registros")
    print("Outputs salvos em: outputs/figures/ e outputs/tables/")
