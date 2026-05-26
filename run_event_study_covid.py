"""
run_event_study_covid.py
========================
Event study do choque COVID-19 (2020) no gap salarial racial.

Análises:
  1. OLS poolado com interações negro × C(Ano) → δ_t relativo a 2019
  2. Teste de pré-tendência (Wald: δ_2016 = δ_2017 = δ_2018 = 0)
  3. Decomposição composicional: separação de efeito preço vs. composição
  4. DiD 2×2 (negro × {2019 vs 2020}) com SE clusterizado

Uso:
    python run_event_study_covid.py                   # amostra completa (~7.7M)
    python run_event_study_covid.py --sample 0.20     # 20% para teste rápido

Tempo estimado: ~5-15 min na amostra completa.
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
        logging.FileHandler("logs/event_study_covid.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from event_study_covid import run_event_study_covid

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Event Study COVID — gap racial PNAD")
    parser.add_argument(
        "--sample", type=float, default=None,
        help="Fração da amostra de empregados para o OLS (default: 100%%).",
    )
    args = parser.parse_args()

    resultados = run_event_study_covid(sample_frac=args.sample)
    print("\n=== CONCLUÍDO ===")
    print("Outputs:")
    print("  outputs/tables/event_study_covid_coef.csv/.tex")
    print("  outputs/tables/event_study_composicao.csv")
    print("  outputs/tables/event_study_did.csv/.tex")
    print("  outputs/figures/event_study_covid.png")
