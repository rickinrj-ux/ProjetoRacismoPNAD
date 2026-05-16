"""
run_interseccionalidade.py
==========================
Análise interseccional: raça × gênero × escolaridade.
Outputs: outputs/figures/interseccional_*.png | outputs/tables/interseccional_*.csv/.tex

Uso:
    python run_interseccionalidade.py --sample 0.15
    python run_interseccionalidade.py
"""
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
        logging.FileHandler("logs/interseccionalidade.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from interseccionalidade import run_interseccionalidade

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Análise interseccional raça×gênero×escolaridade")
    parser.add_argument("--sample", type=float, default=None,
                        help="Fração da amostra. Default: dados completos.")
    args = parser.parse_args()

    resultado = run_interseccionalidade(sample_frac=args.sample)

    print("\n=== CONCLUÍDO ===")
    print("Grupos com EME estimado:", len(resultado["eme"]))
    print("Outputs salvos em: outputs/figures/ e outputs/tables/")
