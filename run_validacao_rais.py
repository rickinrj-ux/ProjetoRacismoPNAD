"""
run_validacao_rais.py
=====================
Validação cruzada do gap salarial racial entre PNAD Contínua e RAIS.

Compara β_negro estimado em cada base com a mesma especificação HLM,
verificando consistência do achado no setor formal (RAIS) versus
toda a força de trabalho (PNAD).

Pré-requisito:
    RAIS harmonizada disponível em data/external/rais_processada.parquet
    (gere com: python run_ingestion_rais.py --project <seu-projeto-gcp>)

Uso rápido (10% da amostra para teste):
    python run_validacao_rais.py --sample 0.10

Análise completa:
    python run_validacao_rais.py

Apontando para RAIS em caminho diferente:
    python run_validacao_rais.py --rais_path data/external/rais_2019_2022.parquet

Filtrar apenas alguns anos:
    python run_validacao_rais.py --anos 2019 2020 2021 2022
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
        logging.FileHandler("logs/validacao_rais.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from validacao_rais import run_validacao_rais

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validação cruzada do gap racial — PNAD × RAIS"
    )
    parser.add_argument("--sample", type=float, default=None,
                        help="Fração da amostra (ex: 0.10 para 10%%). Default: completo.")
    parser.add_argument("--rais_path", type=str, default=None,
                        help="Path do parquet RAIS. Default: data/external/rais_processada.parquet")
    parser.add_argument("--anos", type=int, nargs="+", default=None,
                        help="Anos a incluir (ex: 2019 2020 2021). Default: todos.")
    args = parser.parse_args()

    resultados = run_validacao_rais(
        rais_path=args.rais_path,
        sample_frac=args.sample,
        anos=args.anos,
    )

    print("\n=== CONCLUÍDO ===")
    print(f"Comparações gerais:  {len(resultados['comparacao'])} subgrupos")
    print(f"Comparação temporal: {len(resultados['temporal'])} estimativas")
    print(f"Comparação por UF:   {len(resultados['por_uf'])} registros")
    print("Outputs: outputs/figures/rais_*.png | outputs/tables/rais_*.csv|.tex")
