"""
run_ingestion_enem.py
=====================
Consulta o ENEM no basedosdados e computa o gap racial de desempenho
por UF e ano para uso como preditor contextual de Nível 3 no HLM.

Pré-requisito:
    gcloud auth application-default login

Uso:
    python run_ingestion_enem.py --project tcc-racismo-pnad
    python run_ingestion_enem.py --project tcc-racismo-pnad --ano_ini 2019 --ano_fim 2023
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
        logging.FileHandler("logs/ingestion_enem.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from ingestion_enem import run_ingestion_enem

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestão ENEM — gap racial por UF")
    parser.add_argument("--project",  required=True, help="ID do projeto GCP")
    parser.add_argument("--ano_ini",  type=int, default=2016)
    parser.add_argument("--ano_fim",  type=int, default=2023)
    parser.add_argument("--output",   default="data/external/enem_gap_uf.parquet")
    args = parser.parse_args()

    df = run_ingestion_enem(
        project_id=args.project,
        ano_ini=args.ano_ini,
        ano_fim=args.ano_fim,
        output_path=args.output,
    )
    print(f"\n=== CONCLUÍDO ===")
    print(f"Registros: {len(df):,} | Anos: {sorted(df['ano'].unique().tolist())}")
    print(f"Gap médio: {df['gap_enem'].mean():.1f} pontos")
    print(f"Output: {args.output}")
