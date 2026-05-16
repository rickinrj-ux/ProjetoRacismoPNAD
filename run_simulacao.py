"""
run_simulacao.py
================
Microsimulação do impacto da Lei de Igualdade Salarial e das Cotas.
Outputs: outputs/figures/simulacao_*.png | outputs/tables/simulacao_*.csv

Uso:
    python run_simulacao.py --sample 0.20
    python run_simulacao.py --intensidade_salarial 0.75 --aumento_cotas 0.15
    python run_simulacao.py

Parâmetros:
    --intensidade_salarial: grau de convergência da Lei de Igualdade (0.0-1.0)
    --aumento_cotas: fração de negros sem superior promovidos (0.0-1.0)
    --n_bootstrap: replicações para IC95% (default: 100 — use 500 para publicação)
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
        logging.FileHandler("logs/simulacao.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from simulacao_politicas import run_simulacao

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Microsimulação de políticas públicas")
    parser.add_argument("--sample", type=float, default=None)
    parser.add_argument("--intensidade_salarial", type=float, default=0.50,
                        help="Grau de convergência da Lei de Igualdade Salarial (0-1). Default: 0.50")
    parser.add_argument("--aumento_cotas", type=float, default=0.10,
                        help="Fração de negros promovidos a superior. Default: 0.10")
    parser.add_argument("--n_bootstrap", type=int, default=100,
                        help="Replicações bootstrap para IC95%. Default: 100")
    args = parser.parse_args()

    resultado = run_simulacao(
        sample_frac=args.sample,
        intensidade_salarial=args.intensidade_salarial,
        aumento_cotas=args.aumento_cotas,
        n_bootstrap=args.n_bootstrap,
    )

    print("\n=== CONCLUÍDO ===")
    print(resultado["resultados"][["Cenário", "gap_pct", "redução_%_gap"]].to_string(index=False))
    print("Outputs salvos em: outputs/figures/ e outputs/tables/")
