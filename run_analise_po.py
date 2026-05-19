"""
run_analise_po.py
=================
Runner para os modelos de Pesquisa Operacional (src/analise_po.py).

Uso:
    python run_analise_po.py

Pré-requisito: todos os modelos econométricos já rodados
    (run_analise_hlm.py, run_analise_retornos_raciais.py,
     run_analise_regional.py, e análise SNA já completada).
"""
import sys
import logging
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/analise_po.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from analise_po import run_analise_po

if __name__ == "__main__":
    resultados = run_analise_po()
    print("\n=== CONCLUÍDO ===")
