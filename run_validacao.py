"""
run_validacao.py
================
Validação cruzada dos resultados: temporal, geográfica (LOSO + k-fold) e RAIS.
Outputs: outputs/figures/validacao_*.png | outputs/tables/validacao_*.csv

Uso:
    python run_validacao.py --sample 0.15
    python run_validacao.py --rais_path data/external/rais_processada.parquet
    python run_validacao.py
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
        logging.FileHandler("logs/validacao.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from validacao_cruzada import run_validacao

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validação cruzada dos modelos")
    parser.add_argument("--sample", type=float, default=None)
    parser.add_argument("--rais_path", type=str, default=None,
                        help="Path para parquet da RAIS (opcional).")
    parser.add_argument("--kfold", type=int, default=5,
                        help="Número de folds geográficos. Default: 5")
    args = parser.parse_args()

    resultado = run_validacao(
        sample_frac=args.sample,
        rais_path=args.rais_path,
        n_kfold=args.kfold,
    )

    print("\n=== CONCLUÍDO ===")
    if not resultado["temporal"].empty:
        anos_sig = (resultado["temporal"]["pval"] < 0.05).sum()
        print(f"Temporal: β_negro significativo em {anos_sig}/{len(resultado['temporal'])} anos")
    print("Outputs salvos em: outputs/figures/ e outputs/tables/")
