"""
run_ingestion_rais.py
=====================
Ingestao RAIS via basedosdados (BigQuery) — periodo 2016-2023.
Output: data/external/rais_processada.parquet

PRE-REQUISITOS (uma vez so)
---------------------------
1. Crie um projeto gratuito no Google Cloud:
   https://console.cloud.google.com/
   (clique em "Criar projeto", anote o ID — ex: "meu-projeto-tcc-123")

2. Habilite a BigQuery API no projeto:
   https://console.cloud.google.com/apis/library/bigquery.googleapis.com

3. Instale o gcloud SDK e autentique:
   https://cloud.google.com/sdk/docs/install-sdk
   Depois, no terminal:
   ! gcloud auth application-default login

4. Execute este script:
   python run_ingestion_rais.py --project meu-projeto-tcc-123

COTA GRATUITA
-------------
BigQuery oferece 1 TB/mes de consultas gratuitas.
Esta ingestao le aproximadamente:
   - Todos os anos (2016-2023), Brasil completo: ~300-400 GB
   - Por ano: ~40-60 GB
   - Com --sample 10: ~4-6 GB por ano (recomendado para testes)
Use --sample para testes antes de rodar o dataset completo.

USO
---
    # Teste rapido (10% dos dados)
    python run_ingestion_rais.py --project meu-projeto-tcc-123 --sample 10

    # Ano especifico, UFs especificas
    python run_ingestion_rais.py --project meu-projeto-tcc-123 --anos 2022 2023 --ufs SP RJ MG

    # Completo (todos os anos, Brasil)
    python run_ingestion_rais.py --project meu-projeto-tcc-123

    # Apos concluir, rodar a validacao cruzada:
    python run_validacao.py --rais_path data/external/rais_processada.parquet
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
        logging.FileHandler("logs/ingestion_rais.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from ingestion_rais import run_ingestion_rais, ANOS_DISPONIVEIS

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingestion RAIS via basedosdados (BigQuery)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--project", type=str, required=True,
        help="ID do projeto Google Cloud para faturamento BigQuery. Ex: meu-projeto-tcc-123"
    )
    parser.add_argument(
        "--anos", type=int, nargs="+", default=None,
        help=f"Anos a processar. Default: todos disponiveis {ANOS_DISPONIVEIS}"
    )
    parser.add_argument(
        "--ufs", type=str, nargs="+", default=None,
        help="UFs a incluir (ex: SP RJ MG BA). Default: todas (Brasil)."
    )
    parser.add_argument(
        "--output", type=str, default="data/external/rais_processada.parquet",
        help="Caminho do parquet de saida. Default: data/external/rais_processada.parquet"
    )
    parser.add_argument(
        "--sample", type=float, default=None,
        help=(
            "Percentual TABLESAMPLE para testes (0-100). "
            "Ex: --sample 10 le ~10%% dos dados de cada ano. Default: dados completos."
        )
    )
    args = parser.parse_args()

    print(f"\nProjeto GCP : {args.project}")
    print(f"Anos        : {args.anos or ANOS_DISPONIVEIS}")
    print(f"UFs         : {args.ufs or 'todas (Brasil)'}")
    print(f"Amostragem  : {f'{args.sample}%' if args.sample else 'completo'}")
    print(f"Output      : {args.output}\n")

    df = run_ingestion_rais(
        project_id=args.project,
        anos=args.anos,
        output_path=args.output,
        ufs=args.ufs,
        sample_pct=args.sample,
    )

    gap = df.groupby("negro")["log_renda"].mean()
    gap_val = gap.get(1.0, float("nan")) - gap.get(0.0, float("nan"))

    print("\n=== CONCLUIDO ===")
    print(f"Registros     : {len(df):,}")
    print(f"Anos          : {sorted(df['Ano'].unique().tolist())}")
    print(f"% negro       : {df['negro'].mean():.1%}")
    print(f"Gap bruto     : {gap_val:+.4f} ({(pow(2.718281828, gap_val) - 1)*100:+.1f}%)")
    print(f"\nProximo passo:")
    print(f"  python run_validacao.py --rais_path {args.output}")
