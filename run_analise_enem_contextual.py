"""
run_analise_enem_contextual.py
==============================
HLM estendido com gap racial do ENEM como preditor contextual de Nível 3.

Pré-requisito:
    python run_ingestion_enem.py --project tcc-racismo-pnad

Uso rápido (10% da amostra):
    python run_analise_enem_contextual.py --sample 0.10

Análise completa:
    python run_analise_enem_contextual.py
"""
import sys, logging, argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/analise_enem_contextual.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from analise_enem_contextual import run_analise_enem_contextual

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="HLM com gap ENEM como preditor contextual de Nível 3"
    )
    parser.add_argument("--sample",    type=float, default=None)
    parser.add_argument("--enem_path", type=str,   default=None,
                        help="Path do parquet do gap ENEM. "
                             "Default: data/external/enem_gap_uf.parquet")
    args = parser.parse_args()

    resultados = run_analise_enem_contextual(
        sample_frac=args.sample,
        enem_path=Path(args.enem_path) if args.enem_path else None,
    )

    print("\n=== CONCLUÍDO ===")
    print("Outputs: outputs/tables/enem_*.csv|.tex | outputs/figures/enem_*.png")
