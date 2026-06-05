"""
run_mobilidade.py
=================
Mobilidade intergeracional de renda por raça (proxy via educação do chefe).
Outputs: outputs/figures/mobilidade_*.png | outputs/tables/mobilidade_*.csv

Requer: dados brutos em data/processed/ano=*/trimestre=*/data.parquet
        com variáveis V2005 (posição no domicílio) e V1008 (número do domicílio).

Uso:
    python run_mobilidade.py --sample 0.20
    python run_mobilidade.py --anos 2019 2020 2021 2022 2023
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
Path("outputs/_logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("outputs/_logs/mobilidade.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from mobilidade_intergeracional import run_mobilidade

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mobilidade intergeracional por raça")
    parser.add_argument("--sample", type=float, default=None)
    parser.add_argument("--anos", type=int, nargs="+", default=None,
                        help="Anos a incluir (ex: 2019 2020 2021). Default: todos.")
    args = parser.parse_args()

    resultado = run_mobilidade(anos=args.anos, sample_frac=args.sample)

    print("\n=== CONCLUÍDO ===")
    print(f"Pares filho-chefe: {len(resultado['dataset']):,}")
    print("Outputs salvos em: outputs/figures/ e outputs/tables/")
