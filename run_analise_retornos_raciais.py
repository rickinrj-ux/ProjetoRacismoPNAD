"""
run_analise_retornos_raciais.py
================================
Oaxaca-Blinder twofold decomposition e análise de interação
negro × escolaridade (incluindo efeito quantílico / glass ceiling).

Uso rápido (10% da amostra):
    python run_analise_retornos_raciais.py --sample 0.10

Análise completa:
    python run_analise_retornos_raciais.py

Com menos replicações bootstrap (mais rápido):
    python run_analise_retornos_raciais.py --n_bootstrap 100
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
        logging.FileHandler("logs/analise_retornos_raciais.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from analise_retornos_raciais import run_analise_retornos_raciais

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Oaxaca-Blinder + interação negro×escolaridade"
    )
    parser.add_argument(
        "--sample",
        type=float,
        default=None,
        help="Fração da amostra para teste rápido (ex: 0.10 = 10%%)",
    )
    parser.add_argument(
        "--n_bootstrap",
        type=int,
        default=200,
        help="Número de replicações bootstrap para SE do OB (default: 200)",
    )
    args = parser.parse_args()

    resultados = run_analise_retornos_raciais(
        sample_frac=args.sample,
        n_bootstrap=args.n_bootstrap,
    )

    print("\n=== CONCLUÍDO ===")
    print("Outputs:")
    print("  outputs/tables/ob_decomposicao.csv|.tex")
    print("  outputs/tables/ob_retornos_educacao.csv|.tex")
    print("  outputs/tables/interacao_negro_escolaridade.csv|.tex")
    print("  outputs/tables/interacao_quantilica.csv|.tex")
    print("  outputs/figures/ob_decomposicao.png")
    print("  outputs/figures/ob_retornos_educacao.png")
    print("  outputs/figures/interacao_negro_escolaridade.png")
    print("  outputs/figures/interacao_quantilica.png")
