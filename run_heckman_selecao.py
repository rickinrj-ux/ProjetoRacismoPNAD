"""
run_heckman_selecao.py
======================
Correção de seleção amostral pelo método Heckman Two-Step (1979).

Estágio 1: Probit de seleção (empregado com renda > 0 | PEA + racial).
Estágio 2: OLS com Razão de Mills Inversa (IMR) — compara β_negro com e sem correção.
Variável de exclusão: media_renda_upa_z (não incluída na equação de renda M1–M3).

Uso:
    python run_heckman_selecao.py                  # 20% para o probit (recomendado)
    python run_heckman_selecao.py --sample 0.05    # 5% para teste rápido (~5 min)
    python run_heckman_selecao.py --sample 0.50    # 50% para maior precisão

Tempo estimado: ~10-25 min com 20% (depende de RAM disponível).
"""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import logging
import argparse
from pathlib import Path

sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/heckman_selecao.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from heckman_selecao import run_heckman_selecao

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Heckman Two-Step — gap racial PNAD")
    parser.add_argument(
        "--sample", type=float, default=0.20,
        help="Fração da PEA para o probit de Estágio 1 (default: 0.20 = 20%%).",
    )
    args = parser.parse_args()

    resultados = run_heckman_selecao(sample_frac_probit=args.sample)
    print("\n=== CONCLUÍDO ===")
    print("Outputs:")
    print("  outputs/tables/heckman_comparacao.csv/.tex")
    print("  outputs/tables/heckman_probit_coef.csv")
    print("  outputs/figures/heckman_selecao.png")
