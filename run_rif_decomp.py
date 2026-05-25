"""
run_rif_decomp.py
=================
Decomposição RIF-OB (Firpo, Fortin & Lemieux, 2018) do gap salarial racial
por quantil incondicional.

Outputs:
    outputs/figures/rif_ob_decomposicao.png
    outputs/figures/rif_ob_retornos_quantis.png
    outputs/tables/rif_ob_decomposicao.{csv,tex}

Uso:
    python run_rif_decomp.py               # 10% da amostra (padrão)
    python run_rif_decomp.py --sample 0.20
    python run_rif_decomp.py --sample None  # população completa (~40 min)
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
        logging.FileHandler("logs/rif_decomp.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from rif_decomp import run_rif_decomp

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=float, default=0.10,
                        help="Fração da amostra. Default: 10%% (recomendado para velocidade).")
    args = parser.parse_args()
    sample = None if args.sample == 0 else args.sample
    run_rif_decomp(sample_frac=sample)
    print("\n=== CONCLUÍDO: outputs/tables/rif_ob_decomposicao.* ===")
