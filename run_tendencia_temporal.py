"""
run_tendencia_temporal.py
=========================
Testa formalmente se β_negro está convergindo ou estável ao longo de 2016–2025.

Métodos: WLS ponderado × Chow × Mann-Kendall × AR(1).
Opera sobre outputs/tables/validacao_temporal.csv — sem re-estimar HLMs.

Uso:
    python run_tendencia_temporal.py
"""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import logging
from pathlib import Path

sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/tendencia_temporal.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from tendencia_temporal import run_tendencia_temporal

if __name__ == "__main__":
    resultados = run_tendencia_temporal()
    print("\n=== CONCLUÍDO ===")
    print("Outputs:")
    print("  outputs/tables/tendencia_temporal_testes.csv/.tex")
    print("  outputs/tables/tendencia_temporal_serie.csv/.tex")
    print("  outputs/figures/tendencia_temporal.png")
